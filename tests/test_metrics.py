"""Tests for SESR-Bench core metrics."""

import numpy as np
import sys
sys.path.insert(0, "..")

from sesr_bench import evaluate, critical_clearance, profiles


def approx(a, b, tol=1e-6):
    return abs(a - b) < tol


def test_sesr_basic():
    """SESR = error / clearance."""
    errors = np.array([0.05, 0.10, 0.15])  # meters
    clearance = profiles.uniform(3, 0.10)   # 10 cm uniform
    result = evaluate(errors, clearance, dt=1.0)

    assert approx(result.sesr_timeseries[0], 0.5)   # 5cm / 10cm
    assert approx(result.sesr_timeseries[1], 1.0)   # 10cm / 10cm
    assert approx(result.sesr_timeseries[2], 1.5)   # 15cm / 10cm
    assert approx(result.sesr_mean, 1.0)
    assert approx(result.sesr_max, 1.5)
    print("PASS: test_sesr_basic")


def test_sesr_breach():
    """Breach percentage counts SESR >= 1."""
    errors = np.array([0.05, 0.10, 0.15, 0.20])
    clearance = profiles.uniform(4, 0.10)
    result = evaluate(errors, clearance, dt=1.0)

    # 0.10, 0.15, 0.20 all >= 0.10 clearance -> 3 of 4 breach
    assert result.sesr_breach_pct == 75.0
    print("PASS: test_sesr_breach")


def test_critical_clearance():
    """c* = peak error."""
    errors = np.array([0.01, 0.05, 0.12, 0.03])
    assert critical_clearance(errors) == 0.12
    print("PASS: test_critical_clearance")


def test_cse():
    """CSE accumulates SESR exceedances above threshold."""
    errors = np.array([0.08, 0.08, 0.08])  # 8 cm constant
    clearance = profiles.uniform(3, 0.10)   # 10 cm -> SESR = 0.8
    result = evaluate(errors, clearance, dt=1.0, tau_values=(0.5,))

    # SESR = 0.8, tau = 0.5, excess = 0.3, dt = 1.0, 3 timesteps
    expected_cse = 3 * 0.3 * 1.0  # = 0.9
    assert abs(result.cse[0.5] - expected_cse) < 1e-6
    print("PASS: test_cse")


def test_uniform_profile():
    """Uniform clearance is constant."""
    c = profiles.uniform(100, 0.25)
    assert len(c) == 100
    assert np.all(c == 0.25)
    print("PASS: test_uniform_profile")


def test_sinusoidal_profile():
    """Sinusoidal clearance oscillates and stays positive."""
    ts = np.linspace(0, 20, 200)
    c = profiles.sinusoidal(ts, c_bar=0.3, amplitude=0.2, period=10.0)
    assert len(c) == 200
    assert np.all(c > 0)
    assert c.min() >= 0.01  # safety floor
    assert abs(np.mean(c) - 0.3) < 0.05  # mean near c_bar
    print("PASS: test_sinusoidal_profile")


def test_step_profile():
    """Step clearance alternates."""
    ts = np.array([0, 5, 10, 16, 20, 31])
    c = profiles.step(ts, c_wide=1.0, c_narrow=0.1, period=15.0)
    assert c[0] == 1.0   # first interval is wide
    assert c[2] == 1.0   # still in first interval
    assert c[3] == 0.1   # second interval is narrow
    print("PASS: test_step_profile")


def test_error_correlated_profile():
    """Error-correlated clearance is low where error is high."""
    errors = np.array([0.0, 0.1, 0.2, 0.3])
    c = profiles.error_correlated(errors)
    # c = max(0.05, 0.5 - 2*error)
    assert approx(c[0], 0.5)    # no error -> full clearance
    assert approx(c[1], 0.3)    # 0.5 - 0.2
    assert approx(c[2], 0.1)    # 0.5 - 0.4
    assert approx(c[3], 0.05)   # floor
    print("PASS: test_error_correlated_profile")


def test_zero_error():
    """Zero error produces zero SESR."""
    errors = np.zeros(10)
    clearance = profiles.uniform(10, 0.15)
    result = evaluate(errors, clearance)
    assert result.sesr_mean == 0.0
    assert result.sesr_max == 0.0
    assert result.sesr_breach_pct == 0.0
    print("PASS: test_zero_error")


if __name__ == "__main__":
    test_sesr_basic()
    test_sesr_breach()
    test_critical_clearance()
    test_cse()
    test_uniform_profile()
    test_sinusoidal_profile()
    test_step_profile()
    test_error_correlated_profile()
    test_zero_error()
    print("\nAll tests passed.")
