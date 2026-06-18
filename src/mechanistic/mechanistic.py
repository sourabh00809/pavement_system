"""
Module G — Mechanistic Engine
Fatigue life (Nf), Rutting life (Nr), Design Traffic (Nd) calculations.
Fatigue: Nf = K1 × (1/εt)^K2 × (1/E)^K3  (default: 3.34e18 × (1/εt)^3.58 × (1/E)^1.75)
Rutting: Nr = K4 × (1/εv)^K5  (Shell model)
Design traffic: Nd = 365 × A × D × F × ((1+r)^n - 1) / r  (IRC:37)
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from src.utils.config import load_config, get_logger

log = get_logger(__name__)
CFG = load_config()
ME = CFG["mechanistic"]


@dataclass
class PavementLifeResult:
    epsilon_t_microstrain: float    # horizontal tensile strain (µε)
    epsilon_v_microstrain: float    # vertical compressive strain (µε)
    E_MPa: float                    # dynamic modulus of AC layer
    Nf: float                       # IRC:37-2018 fatigue life (repetitions)
    Nr: float                       # Shell rutting life (repetitions)
    Nd: float                       # design traffic (repetitions)
    governing_failure: str          # 'fatigue' or 'rutting'
    fatigue_utilization: float      # Nd / Nf
    rutting_utilization: float      # Nd / Nr
    design_adequate: bool           # True if both utilizations < 1.0

    def to_dict(self) -> dict:
        return {
            "epsilon_t_µε": round(self.epsilon_t_microstrain, 2),
            "epsilon_v_µε": round(self.epsilon_v_microstrain, 2),
            "E_MPa": round(self.E_MPa, 1),
            "Nf": f"{self.Nf:.3e}",
            "Nr": f"{self.Nr:.3e}",
            "Nd": f"{self.Nd:.3e}",
            "governing_failure": self.governing_failure,
            "fatigue_utilization": round(self.fatigue_utilization, 4),
            "rutting_utilization": round(self.rutting_utilization, 4),
            "design_adequate": self.design_adequate,
        }


def _layer_thicknesses(layers: list[dict] | None) -> tuple[float, float, float]:
    """Extract wearing, binder, and granular thicknesses from dashboard layer rows."""
    if not layers:
        return 50.0, 100.0, 300.0

    wearing = 0.0
    binder = 0.0
    granular = 0.0

    for idx, layer in enumerate(layers):
        name = str(layer.get("Layer", "")).lower()
        thickness = float(layer.get("Thickness (mm)", 0.0))
        if "wear" in name or idx == 0:
            wearing += thickness
        elif "binder" in name or "bituminous" in name or idx == 1:
            binder += thickness
        else:
            granular += thickness

    return max(wearing, 20.0), max(binder, 40.0), max(granular, 100.0)


def estimate_redesigned_strains(epsilon_t_microstrain: float,
                                epsilon_v_microstrain: float,
                                wearing_mm: float,
                                binder_mm: float,
                                granular_mm: float,
                                base_wearing_mm: float,
                                base_binder_mm: float,
                                base_granular_mm: float,
                                binder_stiffness_factor: float) -> tuple[float, float]:
    """
    Lightweight response surrogate for option screening.
    More bituminous depth reduces tensile strain; more lower-layer depth reduces
    vertical subgrade strain. Binder stiffening also lowers response demand.
    """
    base_bituminous = max(base_wearing_mm + base_binder_mm, 1.0)
    new_bituminous = max(wearing_mm + binder_mm, 1.0)
    base_total = max(base_bituminous + base_granular_mm, 1.0)
    new_total = max(new_bituminous + granular_mm, 1.0)

    tensile_factor = (base_bituminous / new_bituminous) ** 1.75
    tensile_factor *= binder_stiffness_factor ** -0.45

    vertical_factor = (base_total / new_total) ** 1.60
    vertical_factor *= binder_stiffness_factor ** -0.18

    eps_t = max(1.0, epsilon_t_microstrain * tensile_factor)
    eps_v = max(1.0, epsilon_v_microstrain * vertical_factor)
    return float(eps_t), float(eps_v)


def recommend_pavement_redesign(epsilon_t_microstrain: float,
                                epsilon_v_microstrain: float,
                                E_MPa: float = 3000.0,
                                layers: list[dict] | None = None,
                                A: float = 1000.0,
                                D: float = ME["default_lane_distribution"],
                                F: float = ME["default_vdf"],
                                r: float = ME["default_growth_rate"],
                                n: int = ME["default_design_period"],
                                K1: float = ME["K1"], K2: float = ME["K2"], K3: float = ME["K3"],
                                K4: float = ME["K4"], K5: float = ME["K5"],
                                target_utilization: float = 0.90) -> dict:
    """
    Screen practical pavement redesign options and return the lightest adequate one.
    Material parameters K1-K5 are overridable for what-if scenarios.

    The search balances layer-depth increases and binder-property improvements.
    It is intentionally deterministic so the dashboard gives repeatable guidance.
    """
    base_wearing, base_binder, base_granular = _layer_thicknesses(layers)
    current = compute_pavement_life(
        epsilon_t_microstrain, epsilon_v_microstrain, E_MPa,
        A=A, D=D, F=F, r=r, n=n, K1=K1, K2=K2, K3=K3, K4=K4, K5=K5,
        log_result=False,
    )

    candidates: list[dict] = []
    wearing_increments = [0, 10, 20, 30, 40, 50, 60]
    binder_increments = [0, 20, 40, 60, 80, 100, 120, 140, 160]
    granular_increments = [0, 25, 50, 75, 100, 125, 150, 175, 200, 250, 300, 350, 400, 450, 500]
    binder_options = [
        {"name": "Existing binder", "stiffness_factor": 1.00, "fatigue_factor": 1.00, "rutting_factor": 1.00},
        {"name": "Improved VG binder", "stiffness_factor": 1.08, "fatigue_factor": 1.15, "rutting_factor": 1.10},
        {"name": "Polymer modified binder", "stiffness_factor": 1.16, "fatigue_factor": 1.35, "rutting_factor": 1.25},
        {"name": "High fatigue-resistant modified binder", "stiffness_factor": 1.22, "fatigue_factor": 1.55, "rutting_factor": 1.35},
    ]

    for w_inc in wearing_increments:
        for b_inc in binder_increments:
            for g_inc in granular_increments:
                for binder in binder_options:
                    wearing = base_wearing + w_inc
                    binder_mm = base_binder + b_inc
                    granular = base_granular + g_inc
                    improved_E = min(E_MPa * binder["stiffness_factor"], 8000.0)
                    eps_t_new, eps_v_new = estimate_redesigned_strains(
                        epsilon_t_microstrain, epsilon_v_microstrain,
                        wearing, binder_mm, granular,
                        base_wearing, base_binder, base_granular,
                        binder["stiffness_factor"],
                    )
                    redesigned = compute_pavement_life(
                        eps_t_new, eps_v_new, improved_E,
                        A=A, D=D, F=F, r=r, n=n,
                        K1=K1 * binder["fatigue_factor"], K2=K2, K3=K3,
                        K4=K4 * binder["rutting_factor"], K5=K5,
                        log_result=False,
                    )
                    governing_util = max(redesigned.fatigue_utilization, redesigned.rutting_utilization)
                    thickness_added = w_inc + b_inc + g_inc
                    binder_penalty = (binder["fatigue_factor"] - 1.0) * 55.0
                    score = thickness_added + binder_penalty + max(0.0, governing_util - target_utilization) * 1000.0
                    candidate = {
                        "wearing_course_mm": float(wearing),
                        "binder_course_mm": float(binder_mm),
                        "granular_layer_mm": float(granular),
                        "total_thickness_mm": float(wearing + binder_mm + granular),
                        "added_thickness_mm": float(thickness_added),
                        "binder_recommendation": binder["name"],
                        "binder_stiffness_factor": float(binder["stiffness_factor"]),
                        "binder_fatigue_factor": float(binder["fatigue_factor"]),
                        "improved_E_MPa": float(improved_E),
                        "predicted_epsilon_t": eps_t_new,
                        "predicted_epsilon_v": eps_v_new,
                        "Nf": redesigned.Nf,
                        "Nr": redesigned.Nr,
                        "Nd": redesigned.Nd,
                        "fatigue_utilization": redesigned.fatigue_utilization,
                        "rutting_utilization": redesigned.rutting_utilization,
                        "governing_failure": redesigned.governing_failure,
                        "design_adequate": redesigned.design_adequate and governing_util <= target_utilization,
                        "score": float(score),
                    }
                    candidates.append(candidate)

    candidates.sort(key=lambda item: (not item["design_adequate"], item["score"], item["added_thickness_mm"]))
    recommended = candidates[0] if candidates else None
    feasible = [c for c in candidates if c["design_adequate"]]

    return {
        "current": current.to_dict(),
        "target_utilization": target_utilization,
        "recommended": recommended,
        "alternatives": feasible[:5],
    }


def nf_fatigue(epsilon_t_microstrain: float,
               E_MPa: float,
               K1: float = ME["K1"],
               K2: float = ME["K2"],
               K3: float = ME["K3"]) -> float:
    """
    Fatigue life equation.
    Nf = K1 × (1/εt)^K2 × (1/E)^K3

    Default constants: K1=3.34e18, K2=3.58, K3=1.75
    → Nf = 3.34e18 × (1/εt)^3.58 × (1/E)^1.75

    Parameters
    ----------
    epsilon_t_microstrain : tensile strain at bottom of AC layer (µε)
    E_MPa                 : resilient modulus of AC mix (MPa)
    K1, K2, K3            : material calibration constants

    Returns
    -------
    Nf : number of standard axle repetitions to fatigue failure
    """
    if epsilon_t_microstrain <= 0 or E_MPa <= 0:
        raise ValueError("Strain and modulus must be positive")
    # εt is used as the raw microstrain value (e.g., 200 for 200 µε)
    Nf = K1 * (1.0 / epsilon_t_microstrain) ** K2 * (1.0 / E_MPa) ** K3
    return float(Nf)


def nr_shell(epsilon_v_microstrain: float,
             K4: float = ME["K4"],
             K5: float = ME["K5"]) -> float:
    """
    Shell rutting life equation (as adopted in IRC:37-2018).
    Nr = K4 × (1/εv)^K5

    Parameters
    ----------
    epsilon_v_microstrain : vertical compressive strain at top of subgrade (µε)
    K4, K5                : Shell rutting constants

    Returns
    -------
    Nr : number of standard axle repetitions to rutting failure
    """
    if epsilon_v_microstrain <= 0:
        raise ValueError("Vertical strain must be positive")
    epsilon_v = epsilon_v_microstrain * 1e-6
    Nr = K4 * (1.0 / epsilon_v) ** K5
    return float(Nr)


def nd_irc(A: float, D: float = ME["default_lane_distribution"],
           F: float = ME["default_vdf"],
           r: float = ME["default_growth_rate"],
           n: int = ME["default_design_period"]) -> float:
    """
    IRC design traffic calculation.
    Nd = 365 × A × D × F × ((1+r)^n - 1) / r

    Parameters
    ----------
    A : initial daily traffic (CVPD — commercial vehicles per day)
    D : lane distribution factor (0–1)
    F : vehicle damage factor (VDF)
    r : annual traffic growth rate (fraction, e.g. 0.05 = 5%)
    n : design period (years)

    Returns
    -------
    Nd : cumulative number of standard axles over design life
    """
    if r <= 0:
        growth_factor = n  # linear if no growth
    else:
        growth_factor = ((1 + r) ** n - 1) / r
    Nd = 365 * A * D * F * growth_factor
    return float(Nd)


def compute_pavement_life(epsilon_t_microstrain: float,
                          epsilon_v_microstrain: float,
                          E_MPa: float = 3000.0,
                          A: float = 1000.0,
                          D: float = ME["default_lane_distribution"],
                          F: float = ME["default_vdf"],
                          r: float = ME["default_growth_rate"],
                          n: int = ME["default_design_period"],
                          K1: float = ME["K1"], K2: float = ME["K2"], K3: float = ME["K3"],
                          K4: float = ME["K4"], K5: float = ME["K5"],
                          log_result: bool = True) -> PavementLifeResult:
    """
    Full pavement life computation (fatigue + rutting + design traffic).
    Computes Nf, Nr, Nd and determines governing failure mode.
    Material parameters K1-K5 are overridable for site-specific calibration.
    """
    Nf = nf_fatigue(epsilon_t_microstrain, E_MPa, K1, K2, K3)
    Nr = nr_shell(epsilon_v_microstrain, K4, K5)
    Nd = nd_irc(A, D, F, r, n)

    fatigue_util = Nd / Nf
    rutting_util = Nd / Nr
    governing = "fatigue" if Nf < Nr else "rutting"
    adequate = (fatigue_util < 1.0) and (rutting_util < 1.0)

    result = PavementLifeResult(
        epsilon_t_microstrain=epsilon_t_microstrain,
        epsilon_v_microstrain=epsilon_v_microstrain,
        E_MPa=E_MPa,
        Nf=Nf,
        Nr=Nr,
        Nd=Nd,
        governing_failure=governing,
        fatigue_utilization=fatigue_util,
        rutting_utilization=rutting_util,
        design_adequate=adequate,
    )

    if log_result:
        log.info(
            f"Pavement Life: Nf={Nf:.3e}, Nr={Nr:.3e}, Nd={Nd:.3e} | "
            f"Governing: {governing} | Adequate: {adequate}"
        )
    return result


def compute_life_with_uncertainty(epsilon_t_microstrain: float,
                                  epsilon_v_microstrain: float,
                                  epsilon_t_std: float,
                                  epsilon_v_std: float,
                                  E_MPa: float = 3000.0,
                                  n_samples: int = 1000,
                                  **kwargs) -> dict:
    """
    Monte Carlo uncertainty propagation for Nf/Nr.
    Samples strain distributions → computes Nf/Nr distributions → returns stats.
    """
    eps_t_samples = np.random.normal(epsilon_t_microstrain, epsilon_t_std, n_samples)
    eps_v_samples = np.random.normal(epsilon_v_microstrain, epsilon_v_std, n_samples)
    eps_t_samples = np.clip(eps_t_samples, 1.0, None)
    eps_v_samples = np.clip(eps_v_samples, 1.0, None)

    Nf_samples = np.array([nf_fatigue(e, E_MPa, **{k: v for k, v in kwargs.items() if k in ["K1","K2","K3"]})
                            for e in eps_t_samples])
    Nr_samples = np.array([nr_shell(e, **{k: v for k, v in kwargs.items() if k in ["K4","K5"]})
                            for e in eps_v_samples])

    return {
        "Nf_mean": float(np.mean(Nf_samples)),
        "Nf_std": float(np.std(Nf_samples)),
        "Nf_p5": float(np.percentile(Nf_samples, 5)),
        "Nf_p95": float(np.percentile(Nf_samples, 95)),
        "Nr_mean": float(np.mean(Nr_samples)),
        "Nr_std": float(np.std(Nr_samples)),
        "Nr_p5": float(np.percentile(Nr_samples, 5)),
        "Nr_p95": float(np.percentile(Nr_samples, 95)),
    }
