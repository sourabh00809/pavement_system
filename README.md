# Pavement AI System

### BTP Phase II — IIT Tirupati (CEE)
**Advisor:** Prof. B. Krishna Prapoorna
**Site:** NH-71 Instrumented Pavement | GEOTRAN DAQ (30 gauges | 500,000 samples/file | 500 Hz)

---

## Overview

End-to-end AI/ML pipeline for **pavement response analysis and fatigue/rutting life prediction** using real-time strain gauge data. Implements IRC:37-2018 mechanistic-empirical design equations with physics-constrained ML.

## Architecture

```
React SPA (Vercel)
  ↓ API calls
FastAPI Backend (Render)
  ↓
Core Python Modules (unchanged):
  A: Ingestion      → GEOTRAN .xls parser
  B: Preprocessing  → 0.5–30 Hz bandpass filter
  C: Sensor Health  → Dead/saturated gauge detection + autoencoder
  D: Event Detection → Adaptive peak detection, vehicle grouping
  E: Synchronization → Cross-correlation, DTW, DBSCAN
  F: Features       → Waveform features, collective strain fusion
  G: Mechanistic    → IRC:37-2018 Nf/Nr/Nd + redesign
  ML: XGBoost classifier + LSTM strain predictor
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start API server
python run_pipeline.py --api

# Or run full pipeline with demo data
python run_pipeline.py --demo

# Frontend (dev mode - separate terminal)
cd frontend && npm install && npm run dev
```

## IRC:37-2018 Equations

**Fatigue Life:** `Nf = K1 × (1/εt)^K2 × (1/E)^K3`
- K1=0.005837, K2=3.89, K3=0.854 (B-80 bituminous mix)

**Rutting Life:** `Nr = K4 × (1/εv)^K5`
- K4=6.15×10⁻⁷, K5=4.0 (Shell model)

**Design Traffic:** `Nd = 365 × A × D × F × ((1+r)^n − 1) / r`

## Deployment

- **Backend:** Render.com (free tier) — `render.yaml`
- **Frontend:** Vercel (free tier) — `frontend/vercel.json`
- **Docker:** `Dockerfile` included for containerized deployment
