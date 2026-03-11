"""
SESR-Bench clearance profiles.

Four synthetic clearance functions for benchmark evaluation.
"""

import numpy as np


def uniform(n: int, c0: float) -> np.ndarray:
    """
    Uniform clearance: c(t) = c0 for all t.

    Parameters
    ----------
    n : int
        Number of timesteps.
    c0 : float
        Constant clearance in meters.
    """
    assert c0 > 0, "clearance must be positive"
    return np.full(n, c0)


def sinusoidal(
    timestamps: np.ndarray,
    c_bar: float = 0.3,
    amplitude: float = 0.2,
    period: float = 10.0,
) -> np.ndarray:
    """
    Sinusoidal clearance: c(t) = c_bar + A * sin(2*pi*t/P).

    Simulates alternating open and narrow regions.

    Parameters
    ----------
    timestamps : np.ndarray, shape (N,)
        Time values in seconds (relative to trajectory start).
    c_bar : float
        Mean clearance in meters.
    amplitude : float
        Oscillation amplitude in meters. Must be < c_bar.
    period : float
        Oscillation period in seconds.
    """
    assert amplitude < c_bar, "amplitude must be less than c_bar to keep clearance positive"
    c = c_bar + amplitude * np.sin(2 * np.pi * timestamps / period)
    return np.maximum(c, 0.01)  # safety floor


def step(
    timestamps: np.ndarray,
    c_wide: float = 1.0,
    c_narrow: float = 0.10,
    period: float = 15.0,
) -> np.ndarray:
    """
    Step clearance: alternates between c_wide and c_narrow.

    Simulates entering and exiting confined spaces.

    Parameters
    ----------
    timestamps : np.ndarray, shape (N,)
        Time values in seconds.
    c_wide : float
        Clearance during wide intervals (meters).
    c_narrow : float
        Clearance during narrow intervals (meters).
    period : float
        Duration of each interval (seconds).
    """
    phase = (timestamps // period).astype(int) % 2
    return np.where(phase == 0, c_wide, c_narrow)


def error_correlated(
    errors: np.ndarray,
    floor: float = 0.05,
    scale: float = 0.5,
    slope: float = 2.0,
) -> np.ndarray:
    """
    Error-correlated clearance: low clearance where error is high.

    c(t) = max(floor, scale - slope * ||e(t)||)

    Models the real-world correlation where visually challenging areas
    (featureless corridors) coincide with geometric constraints.

    Parameters
    ----------
    errors : np.ndarray, shape (N,)
        Position error magnitude in meters.
    floor : float
        Minimum clearance (meters). Prevents division by near-zero.
    scale : float
        Base clearance (meters).
    slope : float
        How aggressively clearance drops with error.
    """
    c = scale - slope * errors
    return np.maximum(c, floor)


# Convenience: standard SESR-Bench protocol profiles
PROTOCOL_UNIFORM_CLEARANCES = [0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.00]


def full_protocol(
    errors: np.ndarray,
    timestamps: np.ndarray,
) -> dict:
    """
    Generate all four clearance profiles for the full SESR-Bench protocol.

    Returns a dict mapping profile name to clearance array.
    """
    n = len(errors)
    profiles = {}

    # Uniform sweep
    for c0 in PROTOCOL_UNIFORM_CLEARANCES:
        profiles[f"uniform_{c0:.2f}"] = uniform(n, c0)

    # Sinusoidal
    profiles["sinusoidal"] = sinusoidal(timestamps)

    # Step
    profiles["step"] = step(timestamps)

    # Error-correlated
    profiles["error_correlated"] = error_correlated(errors)

    return profiles
