"""
SESR-Bench integration with the evo trajectory evaluation library.

Provides one-call evaluation from ground truth + estimate files.
"""

import numpy as np
from typing import Optional
from . import metrics, profiles


def evaluate_trajectory(
    gt_file: str,
    est_file: str,
    format: str = "euroc",
    clearance_profile: str = "uniform",
    c0: float = 0.15,
    **profile_kwargs,
) -> metrics.SESRResult:
    """
    Full SESR evaluation from trajectory files.

    Parameters
    ----------
    gt_file : str
        Path to ground truth trajectory file.
    est_file : str
        Path to estimated trajectory file.
    format : str
        Trajectory format: "euroc", "tum", "kitti".
    clearance_profile : str
        Profile name: "uniform", "sinusoidal", "step", "error_correlated".
    c0 : float
        Clearance value (for uniform profile) in meters.
    **profile_kwargs
        Additional arguments passed to the clearance profile function.

    Returns
    -------
    SESRResult
    """
    try:
        from evo.tools import file_interface
        from evo.core import sync, trajectory
    except ImportError:
        raise ImportError(
            "evo is required for trajectory file loading. "
            "Install it with: pip install evo"
        )

    # Load trajectories based on format
    if format == "euroc":
        traj_ref = file_interface.read_euroc_csv_trajectory(gt_file)
        traj_est = file_interface.read_tum_trajectory_file(est_file)
    elif format == "tum":
        traj_ref = file_interface.read_tum_trajectory_file(gt_file)
        traj_est = file_interface.read_tum_trajectory_file(est_file)
    elif format == "kitti":
        traj_ref = file_interface.read_kitti_poses_file(gt_file)
        traj_est = file_interface.read_kitti_poses_file(est_file)
    else:
        raise ValueError(f"Unknown format: {format}. Use 'euroc', 'tum', or 'kitti'.")

    # Associate timestamps
    traj_ref, traj_est = sync.associate_trajectories(traj_ref, traj_est)

    # Align (Umeyama SE3)
    traj_est_aligned = trajectory.align_trajectory(
        traj_est, traj_ref, correct_scale=False
    )

    # Compute per-timestep position errors
    errors = np.linalg.norm(
        traj_est_aligned.positions_xyz - traj_ref.positions_xyz, axis=1
    )

    # Compute timestamps relative to start
    timestamps = traj_ref.timestamps - traj_ref.timestamps[0]

    # Compute dt (average timestep)
    dt = float(np.mean(np.diff(timestamps))) if len(timestamps) > 1 else 0.05

    # Generate clearance
    n = len(errors)
    if clearance_profile == "uniform":
        clearance = profiles.uniform(n, c0)
    elif clearance_profile == "sinusoidal":
        clearance = profiles.sinusoidal(timestamps, **profile_kwargs)
    elif clearance_profile == "step":
        clearance = profiles.step(timestamps, **profile_kwargs)
    elif clearance_profile == "error_correlated":
        clearance = profiles.error_correlated(errors, **profile_kwargs)
    else:
        raise ValueError(
            f"Unknown profile: {clearance_profile}. "
            "Use 'uniform', 'sinusoidal', 'step', or 'error_correlated'."
        )

    # Evaluate
    return metrics.evaluate(errors, clearance, dt=dt)


def full_evaluation(
    gt_file: str,
    est_file: str,
    format: str = "euroc",
    output: str = "dict",
) -> dict:
    """
    Run the complete SESR-Bench protocol on a trajectory pair.

    Evaluates all clearance profiles and returns comprehensive results.

    Parameters
    ----------
    gt_file, est_file, format : see evaluate_trajectory
    output : str
        Output format: "dict", "csv", "latex", "json".

    Returns
    -------
    dict mapping profile name to SESRResult
    """
    try:
        from evo.tools import file_interface
        from evo.core import sync, trajectory
    except ImportError:
        raise ImportError("evo is required. Install with: pip install evo")

    # Load and align
    if format == "euroc":
        traj_ref = file_interface.read_euroc_csv_trajectory(gt_file)
        traj_est = file_interface.read_tum_trajectory_file(est_file)
    elif format == "tum":
        traj_ref = file_interface.read_tum_trajectory_file(gt_file)
        traj_est = file_interface.read_tum_trajectory_file(est_file)
    else:
        raise ValueError(f"Unknown format: {format}")

    traj_ref, traj_est = sync.associate_trajectories(traj_ref, traj_est)
    traj_est_aligned = trajectory.align_trajectory(
        traj_est, traj_ref, correct_scale=False
    )

    errors = np.linalg.norm(
        traj_est_aligned.positions_xyz - traj_ref.positions_xyz, axis=1
    )
    timestamps = traj_ref.timestamps - traj_ref.timestamps[0]
    dt = float(np.mean(np.diff(timestamps))) if len(timestamps) > 1 else 0.05

    # Run all profiles
    all_profiles = profiles.full_protocol(errors, timestamps)
    results = {}
    for name, clearance in all_profiles.items():
        results[name] = metrics.evaluate(errors, clearance, dt=dt)

    if output == "dict":
        return results
    elif output == "json":
        import json
        return json.dumps(
            {k: v.to_dict() for k, v in results.items()},
            indent=2,
        )
    elif output == "latex":
        return _format_latex(results)
    elif output == "csv":
        return _format_csv(results)
    else:
        return results


def _format_latex(results: dict) -> str:
    """Format results as a LaTeX table row."""
    lines = []
    lines.append("% SESR-Bench results (auto-generated)")
    lines.append("% Profile & ATE(cm) & c*(cm) & SESR_mean & SESR_max & breach(%) & CSE(0.5)")
    for name, r in results.items():
        lines.append(
            f"{name} & {r.ate_rmse*100:.1f} & {r.c_star*100:.1f} & "
            f"{r.sesr_mean:.3f} & {r.sesr_max:.3f} & "
            f"{r.sesr_breach_pct:.1f} & {r.cse.get(0.5, 0):.2f} \\\\"
        )
    return "\n".join(lines)


def _format_csv(results: dict) -> str:
    """Format results as CSV."""
    lines = ["profile,ate_cm,c_star_cm,sesr_mean,sesr_max,breach_pct,cse_0.5"]
    for name, r in results.items():
        lines.append(
            f"{name},{r.ate_rmse*100:.2f},{r.c_star*100:.2f},"
            f"{r.sesr_mean:.4f},{r.sesr_max:.4f},"
            f"{r.sesr_breach_pct:.2f},{r.cse.get(0.5, 0):.3f}"
        )
    return "\n".join(lines)
