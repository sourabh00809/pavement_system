"""
ML Models — Module 4.1 to 4.4
1. Vehicle Type Classifier (XGBoost)
2. Strain Response Predictor (LSTM)
3. MC Dropout uncertainty quantification
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
import torch
import torch.nn as nn
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
from src.utils.config import load_config, get_logger

log = get_logger(__name__)
CFG = load_config()
ML = CFG["ml"]


# ─── Model 1: Vehicle Type Classifier ────────────────────────────────────────

FEATURE_COLS = [
    "axle_count", "duration_s", "mean_axle_spacing_s", "std_axle_spacing_s",
    "max_axle_peak", "mean_axle_peak", "peak_strain_ratio",
    "max_strain", "mean_strain", "area_under_curve", "peak_to_peak",
    "rise_time_s", "zero_crossing_rate",
]


def train_vehicle_classifier(features_df: pd.DataFrame,
                              label_col: str = "axle_count",
                              model_dir: str = "src/models/trained") -> object:
    """
    Train XGBoost vehicle classifier on extracted features.
    Falls back to RandomForest if xgboost not available.
    """
    try:
        from xgboost import XGBClassifier
        model = XGBClassifier(
            n_estimators=ML["xgboost_n_estimators"],
            max_depth=ML["xgboost_max_depth"],
            use_label_encoder=False,
            eval_metric="mlogloss",
            random_state=42,
        )
    except ImportError:
        log.warning("XGBoost not found; using RandomForest fallback")
        model = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42)

    X = features_df[FEATURE_COLS].fillna(0).values
    y = features_df[label_col].values

    # 5-fold stratified CV
    skf = StratifiedKFold(n_splits=ML["cv_folds"], shuffle=True, random_state=42)
    cv_scores = []
    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        model.fit(X[train_idx], y[train_idx])
        preds = model.predict(X[val_idx])
        acc = accuracy_score(y[val_idx], preds)
        cv_scores.append(acc)
        log.info(f"  Fold {fold+1}: accuracy={acc:.3f}")

    log.info(f"CV Accuracy: {np.mean(cv_scores):.3f} ± {np.std(cv_scores):.3f}")

    # Final fit on all data
    model.fit(X, y)
    out_path = Path(model_dir) / "vehicle_classifier.joblib"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_path)
    log.info(f"Vehicle classifier saved → {out_path}")
    return model


def predict_vehicle_type(model, features_df: pd.DataFrame) -> np.ndarray:
    X = features_df[FEATURE_COLS].fillna(0).values
    return model.predict(X)


def load_vehicle_classifier(model_dir: str = "src/models/trained") -> object:
    path = Path(model_dir) / "vehicle_classifier.joblib"
    return joblib.load(path)


# ─── Model 2: LSTM Strain Response Predictor ─────────────────────────────────

class StrainLSTM(nn.Module):
    """
    LSTM that predicts (εt, εv) from a synchronized multi-gauge event window.
    Input: (batch, seq_len, n_features)
    Output: (batch, 2) — [epsilon_t, epsilon_v]
    """
    def __init__(self, n_features: int, hidden: int = 128, dropout: float = 0.2):
        super().__init__()
        self.lstm = nn.LSTM(n_features, hidden, batch_first=True, dropout=dropout)
        self.dropout = nn.Dropout(dropout)
        self.fc1 = nn.Linear(hidden, 64)
        self.fc2 = nn.Linear(64, 2)
        self.relu = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, (h_n, _) = self.lstm(x)
        h = self.dropout(h_n[-1])
        out = self.relu(self.fc1(h))
        return torch.abs(self.fc2(out))  # Physics: strains must be positive

    def predict_with_uncertainty(self, x: torch.Tensor,
                                  n_passes: int = 100) -> tuple[torch.Tensor, torch.Tensor]:
        """MC Dropout: run n_passes forward passes with dropout active."""
        self.train()  # enable dropout
        preds = torch.stack([self(x) for _ in range(n_passes)])
        self.eval()
        mean = preds.mean(dim=0)
        std = preds.std(dim=0)
        return mean, std


def train_strain_lstm(X_train: np.ndarray, y_train: np.ndarray,
                      model_dir: str = "src/models/trained",
                      epochs: int = 50, batch_size: int = 32, lr: float = 1e-3) -> StrainLSTM:
    """
    Train LSTM on synchronized event feature sequences.
    X_train: (N, seq_len, n_features)
    y_train: (N, 2) — [epsilon_t, epsilon_v]
    """
    n_features = X_train.shape[2]
    model = StrainLSTM(n_features, hidden=ML["lstm_hidden"], dropout=ML["lstm_dropout"])
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    X = torch.tensor(X_train, dtype=torch.float32)
    y = torch.tensor(y_train, dtype=torch.float32)
    dataset = torch.utils.data.TensorDataset(X, y)
    loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model.train()
    for epoch in range(epochs):
        total_loss = 0.0
        for X_b, y_b in loader:
            optimizer.zero_grad()
            pred = model(X_b)
            loss = criterion(pred, y_b)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        if (epoch + 1) % 10 == 0:
            log.info(f"  LSTM Epoch {epoch+1}/{epochs}  loss={total_loss/len(loader):.6f}")

    out_path = Path(model_dir) / "strain_lstm.pt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), out_path)
    log.info(f"LSTM saved → {out_path}")
    return model


def load_strain_lstm(n_features: int, model_dir: str = "src/models/trained") -> StrainLSTM:
    model = StrainLSTM(n_features, hidden=ML["lstm_hidden"], dropout=ML["lstm_dropout"])
    path = Path(model_dir) / "strain_lstm.pt"
    model.load_state_dict(torch.load(path, weights_only=True))
    model.eval()
    return model
