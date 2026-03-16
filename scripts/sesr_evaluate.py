#!/usr/bin/env python3
"""
SESR Evaluation Pipeline for Paper B1 (SESR-Bench)
Fixed for evo v1.34, handles all 7 algorithm output formats.

Usage:
    cd ~/sesr
    python3 scripts/sesr_evaluate.py
"""

import os
import sys
import json
import numpy as np
from pathlib import Path
from collections import defaultdict

try:
    from evo.core import trajectory, sync, geometry
    from evo.tools import file_interface
except ImportError:
    print("Run: pip3 install evo numpy matplotlib seaborn")
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError:
    print("Run: pip3 install matplotlib seaborn")
    sys.exit(1)


# ================================================================
# CONFIGURATION
# ================================================================

REPO_DIR = Path.home() / "sesr"
TRAJ_DIR = REPO_DIR / "data" / "trajectories"
GT_DIR = REPO_DIR / "data" / "groundtruth"
RESULTS_DIR = REPO_DIR / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
TABLES_DIR = RESULTS_DIR / "tables"

for d in [RESULTS_DIR, FIGURES_DIR, TABLES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

SEQ_MAP = {
    "MH01": "MH01_gt.csv",
    "MH02": "MH02_gt.csv",
    "MH03": "MH03_gt.csv",
    "MH05": "MH05_gt.csv",
    "V101": "V101_gt.csv",
    "V202": "V202_gt.csv",
}

# BASALT uses different naming: MH1 instead of MH01
BASALT_SEQ_MAP = {
    "MH01": "MH1", "MH02": "MH2", "MH03": "MH3",
    "MH05": "MH5", "V101": "V11", "V202": "V22",
}

ALGORITHMS = ["orbslam3", "basalt", "openvins", "vins_fusion", "rovio", "svo2", "kimera"]

ALGO_DISPLAY = {
    "orbslam3": "ORB-SLAM3",
    "basalt": "BASALT",
    "openvins": "OpenVINS",
    "vins_fusion": "VINS-Fusion",
    "rovio": "ROVIO",
    "svo2": "SVO2",
    "kimera": "Kimera-VIO",
}

UNIFORM_CLEARANCES = [0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.00]


# ================================================================
# LOADERS - handle every format
# ================================================================

def load_euroc_gt(seq_short):
    """Load EuRoC ground truth CSV."""
    gt_file = GT_DIR / SEQ_MAP[seq_short]
    if not gt_file.exists():
        return None
    return file_interface.read_euroc_csv_trajectory(str(gt_file))


def parse_tum_manual(filepath):
    """
    Manually parse TUM-like files, handling:
    - Nanosecond timestamps (divide by 1e9 if > 1e15)
    - Header lines starting with #
    - Scientific notation
    Returns PoseTrajectory3D or None.
    """
    timestamps = []
    xyz = []
    quat_wxyz = []

    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 8:
                continue
            try:
                t = float(parts[0])
                # Convert nanoseconds to seconds if needed
                if t > 1e15:
                    t = t / 1e9
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                qx, qy, qz, qw = float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])
                timestamps.append(t)
                xyz.append([x, y, z])
                quat_wxyz.append([qw, qx, qy, qz])
            except (ValueError, IndexError):
                continue

    if len(timestamps) < 10:
        return None

    return trajectory.PoseTrajectory3D(
        positions_xyz=np.array(xyz),
        orientations_quat_wxyz=np.array(quat_wxyz),
        timestamps=np.array(timestamps),
    )


def parse_vins_csv(filepath):
    """
    Parse VINS-Fusion CSV output.
    Format: timestamp,x,y,z,qw,qx,qy,qz,vx,vy,vz, (trailing comma)
    Note: VINS uses qw FIRST in the csv, but the output we captured
    from stereoVIOEuroc.bash prints: time, t: x y z q: qx qy qz qw
    Actually let's check: the CSV has comma-separated values.
    """
    timestamps = []
    xyz = []
    quat_wxyz = []

    with open(filepath) as f:
        for line in f:
            line = line.strip().rstrip(",")
            if not line or line.startswith("#") or line.startswith("time"):
                continue
            parts = line.split(",")
            if len(parts) < 8:
                continue
            try:
                t = float(parts[0])
                if t > 1e15:
                    t = t / 1e9
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                # VINS CSV format from our run script captured raw output
                # Check: is it qx,qy,qz,qw or qw,qx,qy,qz?
                # From the sample: -0.04276,0.84177,0.04577,0.53618
                # Compare with GT:  0.534108,-0.153029,-0.827383,-0.082152 (qw,qx,qy,qz)
                # The VINS output looks like qx,qy,qz,qw based on magnitude
                qx, qy, qz, qw = float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])
                timestamps.append(t)
                xyz.append([x, y, z])
                quat_wxyz.append([qw, qx, qy, qz])
            except (ValueError, IndexError):
                continue

    if len(timestamps) < 10:
        return None

    return trajectory.PoseTrajectory3D(
        positions_xyz=np.array(xyz),
        orientations_quat_wxyz=np.array(quat_wxyz),
        timestamps=np.array(timestamps),
    )


def parse_openvins(filepath):
    """
    Parse OpenVINS console output converted to TUM.
    Format: fake_timestamp x y z qx qy qz qw
    Timestamps are fake (0.0, 0.05, 0.1, ...) so we need to
    reconstruct real timestamps from the GT trajectory rate.
    We'll assign EuRoC timestamps based on 20Hz rate.
    """
    timestamps = []
    xyz = []
    quat_wxyz = []

    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 8:
                continue
            try:
                t = float(parts[0])
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                qx, qy, qz, qw = float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])
                timestamps.append(t)
                xyz.append([x, y, z])
                quat_wxyz.append([qw, qx, qy, qz])
            except (ValueError, IndexError):
                continue

    if len(timestamps) < 10:
        return None

    # OpenVINS timestamps are fake (0, 0.05, 0.1...)
    # We can't align with GT by timestamp.
    # Instead we'll align by position using Umeyama only.
    return trajectory.PoseTrajectory3D(
        positions_xyz=np.array(xyz),
        orientations_quat_wxyz=np.array(quat_wxyz),
        timestamps=np.array(timestamps),
    )


def parse_kimera_csv(filepath):
    """
    Parse Kimera CSV: #timestamp,x,y,z,qw,qx,qy,qz,...
    Timestamps in nanoseconds. Quaternion order: qw,qx,qy,qz.
    """
    timestamps = []
    xyz = []
    quat_wxyz = []

    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            parts = line.split(",")
            if len(parts) < 8:
                continue
            try:
                t = float(parts[0]) / 1e9
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                qw, qx, qy, qz = float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])
                timestamps.append(t)
                xyz.append([x, y, z])
                quat_wxyz.append([qw, qx, qy, qz])
            except (ValueError, IndexError):
                continue

    if len(timestamps) < 10:
        return None

    return trajectory.PoseTrajectory3D(
        positions_xyz=np.array(xyz),
        orientations_quat_wxyz=np.array(quat_wxyz),
        timestamps=np.array(timestamps),
    )


def load_trajectories_for_algo(algo, seq_short):
    """Load all runs for an algorithm/sequence pair."""
    algo_dir = TRAJ_DIR / algo
    if not algo_dir.is_dir():
        return []

    # Determine file pattern based on algorithm
    if algo == "basalt":
        short = BASALT_SEQ_MAP.get(seq_short, seq_short)
        pattern = f"{short}_run*.txt"
    elif algo == "kimera":
        pattern = f"{seq_short}_run*.csv"
    else:
        pattern = f"{seq_short}_run*.txt"

    results = []
    for f in sorted(algo_dir.glob(pattern)):
        try:
            if algo == "kimera":
                traj = parse_kimera_csv(f)
            elif algo == "vins_fusion":
                traj = parse_vins_csv(f)
            elif False:  # openvins now has real timestamps
                traj = parse_openvins(f)
            else:
                traj = parse_tum_manual(f)

            if traj is not None:
                results.append((f.stem, traj))
        except Exception as e:
            print(f"    WARN: Could not load {f.name}: {e}")

    return results


# ================================================================
# ALIGNMENT AND ERROR COMPUTATION (evo v1.34 API)
# ================================================================

def align_and_compute_errors(traj_ref, traj_est, algo):
    """
    Align estimated trajectory to reference and compute position errors.
    Handles timestamp-based association for most algorithms,
    and index-based for OpenVINS (which has fake timestamps).
    """
    if False:  # openvins now has real timestamps
        # OpenVINS has fake timestamps. We can't use timestamp association.
        # Subsample the longer trajectory to match lengths, then align by position.
        n_ref = len(traj_ref.timestamps)
        n_est = len(traj_est.timestamps)

        if n_est > n_ref:
            # Subsample estimated to match GT length
            indices = np.linspace(0, n_est - 1, n_ref, dtype=int)
            pos_est = traj_est.positions_xyz[indices]
            quat_est = traj_est.orientations_quat_wxyz[indices]
            traj_est_sub = trajectory.PoseTrajectory3D(
                positions_xyz=pos_est,
                orientations_quat_wxyz=quat_est,
                timestamps=traj_ref.timestamps.copy(),
            )
        elif n_ref > n_est:
            indices = np.linspace(0, n_ref - 1, n_est, dtype=int)
            pos_ref = traj_ref.positions_xyz[indices]
            quat_ref = traj_ref.orientations_quat_wxyz[indices]
            traj_ref_sub = trajectory.PoseTrajectory3D(
                positions_xyz=pos_ref,
                orientations_quat_wxyz=quat_ref,
                timestamps=traj_est.timestamps.copy(),
            )
            traj_ref = traj_ref_sub
            traj_est_sub = traj_est
        else:
            traj_est_sub = traj_est

        # Umeyama alignment
        r, t, s = geometry.umeyama_alignment(
            traj_est_sub.positions_xyz.T, traj_ref.positions_xyz.T, with_scale=False
        )
        aligned_pos = (r @ traj_est_sub.positions_xyz.T + t[:, np.newaxis]).T
        errors = np.linalg.norm(aligned_pos - traj_ref.positions_xyz, axis=1)
        timestamps = np.arange(len(errors)) * 0.05  # fake but consistent
        ate = float(np.sqrt(np.mean(errors ** 2)))
        return errors, timestamps, ate

    else:
        # Normal timestamp-based association
        traj_ref_s, traj_est_s = sync.associate_trajectories(
            traj_ref, traj_est, max_diff=0.05
        )

        if len(traj_ref_s.timestamps) < 10:
            raise ValueError(f"Only {len(traj_ref_s.timestamps)} matched timestamps")

        # Umeyama alignment (SE3, no scale)
        r, t, s = geometry.umeyama_alignment(
            traj_est_s.positions_xyz.T, traj_ref_s.positions_xyz.T, with_scale=False
        )
        aligned_pos = (r @ traj_est_s.positions_xyz.T + t[:, np.newaxis]).T

        errors = np.linalg.norm(aligned_pos - traj_ref_s.positions_xyz, axis=1)
        timestamps = traj_ref_s.timestamps - traj_ref_s.timestamps[0]
        ate = float(np.sqrt(np.mean(errors ** 2)))
        return errors, timestamps, ate


# ================================================================
# SESR METRICS
# ================================================================

def compute_sesr(errors, clearance, dt=0.05, tau_values=(0.3, 0.5, 0.7)):
    sesr = errors / clearance
    result = {
        "sesr_mean": float(np.mean(sesr)),
        "sesr_max": float(np.max(sesr)),
        "sesr_breach_pct": float(100.0 * np.mean(sesr >= 1.0)),
        "c_star_cm": float(np.max(errors) * 100),
        "sesr_timeseries": sesr,
    }
    for tau in tau_values:
        result[f"cse_{tau}"] = float(np.sum(np.maximum(0, sesr - tau)) * dt)
    return result

def uniform_clearance(n, c0):
    return np.full(n, c0)

def sinusoidal_clearance(ts, c_bar=0.3, amp=0.2, period=10.0):
    return np.maximum(0.01, c_bar + amp * np.sin(2 * np.pi * ts / period))

def step_clearance(ts, c_wide=1.0, c_narrow=0.10, period=15.0):
    phase = (ts // period).astype(int) % 2
    return np.where(phase == 0, c_wide, c_narrow)

def error_correlated_clearance(errors, floor=0.05):
    return np.maximum(floor, 0.5 - 2.0 * errors)


# ================================================================
# STEP 1: Compute position errors
# ================================================================

print("=" * 60)
print("STEP 1: Computing position errors")
print("=" * 60)

all_data = {}
seq_list = list(SEQ_MAP.keys())

for seq_short in seq_list:
    gt = load_euroc_gt(seq_short)
    if gt is None:
        print(f"  SKIP {seq_short}: no ground truth")
        continue

    for algo in ALGORITHMS:
        runs = load_trajectories_for_algo(algo, seq_short)
        if not runs:
            print(f"  MISS {algo:12s} / {seq_short}")
            continue

        run_results = []
        for name, traj_est in runs:
            try:
                errors, timestamps, ate = align_and_compute_errors(gt, traj_est, algo)
                run_results.append((name, errors, timestamps, ate))
            except Exception as e:
                print(f"    WARN: {algo}/{seq_short}/{name}: {e}")

        if not run_results:
            print(f"  FAIL {algo:12s} / {seq_short}: all runs failed")
            continue

        # Select median ATE run
        run_results.sort(key=lambda x: x[3])
        median = run_results[len(run_results) // 2]
        name, errors, timestamps, ate = median

        all_data[(algo, seq_short)] = {
            "errors": errors,
            "timestamps": timestamps,
            "ate": ate,
            "num_runs": len(run_results),
            "all_ates": [r[3] for r in run_results],
        }

        print(f"  OK {algo:12s} / {seq_short} | ATE = {ate*100:6.2f} cm | "
              f"peak = {np.max(errors)*100:6.2f} cm | {len(run_results)} runs")

print(f"\nTotal pairs: {len(all_data)}")

if len(all_data) == 0:
    print("\nFATAL: No data loaded. Check file formats and paths.")
    sys.exit(1)


# ================================================================
# STEP 2: Compute SESR under all clearance profiles
# ================================================================

print("\n" + "=" * 60)
print("STEP 2: Computing SESR metrics")
print("=" * 60)

sesr_results = {}

for (algo, seq), data in all_data.items():
    errors = data["errors"]
    ts = data["timestamps"]
    dt = float(np.mean(np.diff(ts))) if len(ts) > 1 else 0.05

    sesr_results[(algo, seq)] = {}

    for c0 in UNIFORM_CLEARANCES:
        key = f"uniform_{c0:.2f}"
        c = uniform_clearance(len(errors), c0)
        sesr_results[(algo, seq)][key] = compute_sesr(errors, c, dt)

    c = sinusoidal_clearance(ts)
    sesr_results[(algo, seq)]["sinusoidal"] = compute_sesr(errors, c, dt)

    c = step_clearance(ts)
    sesr_results[(algo, seq)]["step"] = compute_sesr(errors, c, dt)

    c = error_correlated_clearance(errors)
    sesr_results[(algo, seq)]["error_correlated"] = compute_sesr(errors, c, dt)

print(f"Computed SESR for {len(sesr_results)} pairs x {len(UNIFORM_CLEARANCES) + 3} profiles")


# ================================================================
# STEP 3: Generate figures
# ================================================================

print("\n" + "=" * 60)
print("STEP 3: Generating figures")
print("=" * 60)


def plot_three_panel(algo, seq, clearance_func, clearance_name, filename):
    if (algo, seq) not in all_data:
        return

    errors = all_data[(algo, seq)]["errors"]
    ts = all_data[(algo, seq)]["timestamps"]
    c = clearance_func(ts)
    sesr = errors / c

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 7), sharex=True)

    ax1.plot(ts, errors * 100, "k-", linewidth=0.6)
    ax1.set_ylabel("Position Error (cm)")
    ax1.grid(True, alpha=0.3)

    ax2.plot(ts, c, "b-", linewidth=0.8)
    ax2.set_ylabel("Clearance (m)")
    ax2.grid(True, alpha=0.3)

    ax3.plot(ts, sesr, "r-", linewidth=0.6)
    ax3.axhline(y=1.0, color="k", linestyle="--", linewidth=0.8, alpha=0.7)
    ax3.set_ylabel("SESR")
    ax3.set_xlabel("Time (s)")
    ax3.grid(True, alpha=0.3)

    title = f"{ALGO_DISPLAY.get(algo, algo)} on {seq} ({clearance_name} clearance)"
    fig.suptitle(title, fontsize=12)
    plt.tight_layout()

    outpath = FIGURES_DIR / filename
    plt.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {outpath}")


# Main figures: pick best available algorithm on MH03
for main_seq in ["MH03", "MH05", "MH01"]:
    for candidate in ALGORITHMS:
        if (candidate, main_seq) in all_data:
            plot_three_panel(candidate, main_seq, step_clearance, "step",
                             f"fig1_step_{candidate}_{main_seq}.pdf")
            plot_three_panel(candidate, main_seq, sinusoidal_clearance, "sinusoidal",
                             f"fig2_sinusoidal_{candidate}_{main_seq}.pdf")
            break
    else:
        continue
    break

# All algorithms on all sequences with step clearance
for algo in ALGORITHMS:
    for seq in seq_list:
        if (algo, seq) in all_data:
            plot_three_panel(algo, seq, step_clearance, "step",
                             f"fig_step_{algo}_{seq}.pdf")


# Breach heatmaps
def plot_breach_heatmap(c0, filename):
    profile_key = f"uniform_{c0:.2f}"
    active_algos = [a for a in ALGORITHMS if any((a, s) in sesr_results for s in seq_list)]
    active_seqs = [s for s in seq_list if any((a, s) in sesr_results for a in ALGORITHMS)]

    if not active_algos or not active_seqs:
        return

    matrix = np.full((len(active_algos), len(active_seqs)), np.nan)
    for i, algo in enumerate(active_algos):
        for j, seq in enumerate(active_seqs):
            if (algo, seq) in sesr_results and profile_key in sesr_results[(algo, seq)]:
                matrix[i, j] = sesr_results[(algo, seq)][profile_key]["sesr_breach_pct"]

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.heatmap(
        matrix, annot=True, fmt=".1f",
        xticklabels=active_seqs,
        yticklabels=[ALGO_DISPLAY.get(a, a) for a in active_algos],
        cmap="YlOrRd", vmin=0, vmax=50, ax=ax, linewidths=0.5,
    )
    ax.set_title(f"SESR Breach Rate (%) at c = {c0} m")
    plt.tight_layout()
    outpath = FIGURES_DIR / filename
    plt.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {outpath}")

for c0 in [0.10, 0.15, 0.20, 0.30]:
    plot_breach_heatmap(c0, f"fig_heatmap_c{int(c0*100):02d}.pdf")


# Critical clearance bar chart
def plot_cstar_bars(filename):
    algo_cstars = defaultdict(list)
    for (algo, seq), data in all_data.items():
        algo_cstars[algo].append(np.max(data["errors"]) * 100)

    if not algo_cstars:
        return

    algos = sorted(algo_cstars.keys(), key=lambda a: np.mean(algo_cstars[a]))
    means = [np.mean(algo_cstars[a]) for a in algos]
    stds = [np.std(algo_cstars[a]) for a in algos]
    labels = [ALGO_DISPLAY.get(a, a) for a in algos]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(labels, means, xerr=stds, color="steelblue", alpha=0.8, capsize=4)
    ax.set_xlabel("Mean Critical Clearance c* (cm)")
    ax.set_title("Minimum Safe Deployment Clearance (EuRoC)")
    ax.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()
    outpath = FIGURES_DIR / filename
    plt.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {outpath}")

plot_cstar_bars("fig_cstar_bars.pdf")


# ATE vs SESR scatter
def plot_ate_vs_sesr(c0, filename):
    profile_key = f"uniform_{c0:.2f}"
    fig, ax = plt.subplots(figsize=(8, 6))

    for algo in ALGORITHMS:
        ates = []
        sesrs = []
        for seq in seq_list:
            if (algo, seq) in all_data and (algo, seq) in sesr_results:
                if profile_key in sesr_results[(algo, seq)]:
                    ates.append(all_data[(algo, seq)]["ate"] * 100)
                    sesrs.append(sesr_results[(algo, seq)][profile_key]["sesr_breach_pct"])
        if ates:
            ax.scatter(ates, sesrs, label=ALGO_DISPLAY.get(algo, algo), s=60, alpha=0.8)

    ax.set_xlabel("ATE RMSE (cm)")
    ax.set_ylabel(f"SESR Breach Rate (%) at c = {c0} m")
    ax.set_title("ATE vs SESR: Ranking Inversions")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    outpath = FIGURES_DIR / filename
    plt.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {outpath}")

plot_ate_vs_sesr(0.15, "fig_ate_vs_sesr_c15.pdf")
plot_ate_vs_sesr(0.10, "fig_ate_vs_sesr_c10.pdf")


# ================================================================
# STEP 4: Generate LaTeX tables
# ================================================================

print("\n" + "=" * 60)
print("STEP 4: Generating LaTeX tables")
print("=" * 60)

def generate_leaderboard_latex(filename="table1_leaderboard.tex"):
    lines = ["% Auto-generated by sesr_evaluate.py", ""]
    for seq in seq_list:
        lines.append(f"\\midrule")
        lines.append(f"\\multicolumn{{7}}{{c}}{{\\textbf{{{seq}}}}} \\\\")
        lines.append(f"\\midrule")
        for algo in ALGORITHMS:
            if (algo, seq) not in all_data:
                continue
            ate_cm = all_data[(algo, seq)]["ate"] * 100
            c_star = np.max(all_data[(algo, seq)]["errors"]) * 100
            parts = [ALGO_DISPLAY.get(algo, algo), f"{ate_cm:.1f}", f"{c_star:.1f}"]
            for c0 in [0.15, 0.10]:
                key = f"uniform_{c0:.2f}"
                if (algo, seq) in sesr_results and key in sesr_results[(algo, seq)]:
                    r = sesr_results[(algo, seq)][key]
                    parts.extend([f"{r['sesr_mean']:.3f}", f"{r['sesr_breach_pct']:.1f}"])
                else:
                    parts.extend(["--", "--"])
            lines.append(" & ".join(parts) + " \\\\")
    outpath = TABLES_DIR / filename
    with open(outpath, "w") as f:
        f.write("\n".join(lines))
    print(f"  Saved: {outpath}")

generate_leaderboard_latex()

def generate_cstar_latex(filename="table2_cstar.tex"):
    lines = ["% Auto-generated critical clearance table (cm)"]
    for algo in ALGORITHMS:
        values = []
        for seq in seq_list:
            if (algo, seq) in all_data:
                values.append(f"{np.max(all_data[(algo, seq)]['errors']) * 100:.1f}")
            else:
                values.append("--")
        mean_vals = [np.max(all_data[(algo, s)]["errors"]) * 100 for s in seq_list if (algo, s) in all_data]
        mean_str = f"{np.mean(mean_vals):.1f}" if mean_vals else "--"
        lines.append(f"{ALGO_DISPLAY.get(algo, algo)} & " + " & ".join(values) + f" & {mean_str} \\\\")
    outpath = TABLES_DIR / filename
    with open(outpath, "w") as f:
        f.write("\n".join(lines))
    print(f"  Saved: {outpath}")

generate_cstar_latex()

def generate_ate_table(filename="table3_ate.tex"):
    lines = ["% Auto-generated ATE table (cm)"]
    for algo in ALGORITHMS:
        values = []
        for seq in seq_list:
            if (algo, seq) in all_data:
                values.append(f"{all_data[(algo, seq)]['ate'] * 100:.1f}")
            else:
                values.append("--")
        mean_vals = [all_data[(algo, s)]["ate"] * 100 for s in seq_list if (algo, s) in all_data]
        mean_str = f"{np.mean(mean_vals):.1f}" if mean_vals else "--"
        lines.append(f"{ALGO_DISPLAY.get(algo, algo)} & " + " & ".join(values) + f" & {mean_str} \\\\")
    outpath = TABLES_DIR / filename
    with open(outpath, "w") as f:
        f.write("\n".join(lines))
    print(f"  Saved: {outpath}")

generate_ate_table()


# ================================================================
# STEP 5: Save JSON
# ================================================================

print("\n" + "=" * 60)
print("STEP 5: Saving results")
print("=" * 60)

export = {}
for (algo, seq), data in all_data.items():
    key = f"{algo}__{seq}"
    export[key] = {
        "algorithm": algo,
        "sequence": seq,
        "ate_cm": round(data["ate"] * 100, 2),
        "c_star_cm": round(float(np.max(data["errors"])) * 100, 2),
        "num_points": len(data["errors"]),
        "duration_s": round(float(data["timestamps"][-1]), 1),
        "num_runs": data["num_runs"],
        "all_ates_cm": [round(a * 100, 2) for a in data["all_ates"]],
    }
    for c0 in [0.05, 0.10, 0.15, 0.20, 0.30]:
        pkey = f"uniform_{c0:.2f}"
        if (algo, seq) in sesr_results and pkey in sesr_results[(algo, seq)]:
            r = sesr_results[(algo, seq)][pkey]
            export[key][f"sesr_mean_c{int(c0*100):02d}"] = round(r["sesr_mean"], 4)
            export[key][f"breach_pct_c{int(c0*100):02d}"] = round(r["sesr_breach_pct"], 2)
            export[key][f"cse_0.5_c{int(c0*100):02d}"] = round(r["cse_0.5"], 4)

json_path = RESULTS_DIR / "sesr_bench_results.json"
with open(json_path, "w") as f:
    json.dump(export, f, indent=2)
print(f"  Saved: {json_path}")


# ================================================================
# SUMMARY
# ================================================================

print("\n" + "=" * 60)
print("PIPELINE COMPLETE")
print("=" * 60)

n_algos = len(set(a for a, s in all_data))
n_seqs = len(set(s for a, s in all_data))
print(f"""
  {len(all_data)} algorithm-sequence pairs ({n_algos} algorithms x {n_seqs} sequences)
  {len(sesr_results)} SESR evaluations x {len(UNIFORM_CLEARANCES) + 3} profiles

  Results: {RESULTS_DIR}/
    figures/   <- PDF figures
    tables/    <- LaTeX tables
    sesr_bench_results.json
""")
