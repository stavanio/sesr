"""
SESR-Bench: Clearance-Aware Evaluation for Visual-Inertial Odometry.

Core metrics: SESR, CSE, critical clearance.
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class SESRResult:
    """Result container for SESR evaluation."""

    ate_rmse: float           # meters
    sesr_mean: float
    sesr_max: float
    sesr_breach_pct: float    # percentage of timesteps with SESR >= 1
    cse: Dict[float, float]   # threshold -> CSE value in seconds
    c_star: float             # critical clearance in meters
    sesr_timeseries: np.ndarray

    def __repr__(self):
        return (
            f"SESRResult(\n"
            f"  ATE_RMSE    = {self.ate_rmse * 100:.2f} cm\n"
            f"  SESR_mean   = {self.sesr_mean:.3f}\n"
            f"  SESR_max    = {self.sesr_max:.3f}\n"
            f"  breach      = {self.sesr_breach_pct:.1f}%\n"
            f"  CSE(0.5)    = {self.cse.get(0.5, 0.0):.2f} s\n"
            f"  c*          = {self.c_star * 100:.1f} cm\n"
            f")"
        )

    def to_dict(self) -> dict:
        return {
            "ate_rmse_cm": round(self.ate_rmse * 100, 2),
            "sesr_mean": round(self.sesr_mean, 4),
            "sesr_max": round(self.sesr_max, 4),
            "sesr_breach_pct": round(self.sesr_breach_pct, 2),
            "cse_0.3": round(self.cse.get(0.3, 0.0), 3),
            "cse_0.5": round(self.cse.get(0.5, 0.0), 3),
            "cse_0.7": round(self.cse.get(0.7, 0.0), 3),
            "c_star_cm": round(self.c_star * 100, 2),
        }


def evaluate(
    errors: np.ndarray,
    clearance: np.ndarray,
    dt: float = 0.05,
    tau_values: tuple = (0.3, 0.5, 0.7),
) -> SESRResult:
    """
    Compute SESR-Bench metrics.

    Parameters
    ----------
    errors : np.ndarray, shape (N,)
        Position error magnitude at each timestep, in meters.
    clearance : np.ndarray, shape (N,)
        Clearance (min distance to obstacle) at each timestep, in meters.
        Must be > 0 everywhere.
    dt : float
        Time between samples in seconds. Default 0.05 (20 Hz).
    tau_values : tuple of float
        CSE thresholds to compute.

    Returns
    -------
    SESRResult
    """
    assert len(errors) == len(clearance), "errors and clearance must have same length"
    assert np.all(clearance > 0), "clearance must be positive everywhere"

    # SESR: one division per timestep
    sesr = errors / clearance

    # Summary statistics
    sesr_mean = float(np.mean(sesr))
    sesr_max = float(np.max(sesr))
    sesr_breach_pct = float(100.0 * np.mean(sesr >= 1.0))

    # CSE at each threshold
    cse = {}
    for tau in tau_values:
        cse[tau] = float(np.sum(np.maximum(0, sesr - tau)) * dt)

    # Critical clearance = peak error
    c_star = float(np.max(errors))

    # ATE RMSE
    ate_rmse = float(np.sqrt(np.mean(errors ** 2)))

    return SESRResult(
        ate_rmse=ate_rmse,
        sesr_mean=sesr_mean,
        sesr_max=sesr_max,
        sesr_breach_pct=sesr_breach_pct,
        cse=cse,
        c_star=c_star,
        sesr_timeseries=sesr,
    )


def critical_clearance(errors: np.ndarray) -> float:
    """
    Compute critical clearance: the minimum uniform clearance
    at which SESR never exceeds 1.

    This is simply the peak position error.

    Parameters
    ----------
    errors : np.ndarray, shape (N,)
        Position error magnitude at each timestep, in meters.

    Returns
    -------
    float : critical clearance in meters.
    """
    return float(np.max(errors))
