"""
SESR-Bench: Clearance-Aware Evaluation for Visual-Inertial Odometry.

Usage:
    from sesr_bench import evaluate, profiles

    errors = ...  # shape (N,), meters
    clearance = profiles.uniform(n=len(errors), c0=0.15)
    result = evaluate(errors, clearance)
    print(result)
"""

from .metrics import evaluate, critical_clearance, SESRResult
from . import profiles
from . import evo_integration

__version__ = "0.1.0"
__all__ = ["evaluate", "critical_clearance", "profiles", "evo_integration", "SESRResult"]
