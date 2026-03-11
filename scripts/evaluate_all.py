#!/usr/bin/env python3
"""
SESR-Bench: Complete local evaluation pipeline.

Run this on your Mac after downloading trajectory files from the cloud.

Usage:
    pip install evo numpy matplotlib seaborn
    python3 sesr_local_pipeline.py

Input:  ~/sesr-metrics/trajectories/  (from cloud tarball)
Output: ~/sesr-metrics/results/       (tables, figures, LaTeX)
"""

import os
import sys
import json
import numpy as np
from pathlib import Path
from collections import defaultdict

# ----------------------------------------------------------------
# Check dependencies
# ----------------------------------------------------------------
try:
    from evo.core import trajectory, sync
    from evo.tools import file_interface
except ImportError:
    print("Missing dependency. Run:")
    print("  pip install evo numpy matplotlib seaborn")
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend for Mac
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError:
    print("Missing plotting dependencies. Run:")
    print("  pip install matplotlib seaborn")
    sys.exit(1)


# ================================================================
# CONFIGURATION
# ================================================================

BASE = Path.home() / "sesr-metrics"
TRAJ_DIR = BASE / "trajectories"
EUROC_DIR = BASE / "euroc"  # or wherever you put the EuRoC data
RESULTS_DIR = BASE / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
TABLES_DIR = RESULTS_DIR / "tables"

for d in [RESULTS_DIR, FIGURES_DIR, TABLES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

EUROC_SEQUENCES = [
    "MH_01_easy", "MH_02_easy", "MH_03_medium",
    "MH_05_difficult", "V1_01_easy", "V2_02_medium",
]

ALGORITHMS = [
    "vins_mono", "orbslam3", "openvins",
    "basalt", "rovio", "svo2", "kimera",
]

ALGO_DISPLAY = {
    "vins_mono": "VINS-Mono",
    "orbslam3": "ORB-SLAM3",
    "openvins": "OpenVINS",
    "basalt": "BASALT",
    "rovio": "ROVIO",
    "svo2": "SVO2",
    "kimera": "Kimera",
}

UNIFORM_CLEARANCES = [0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.00]

# ================================================================
# STEP 3: Compute position errors
# ================================================================

def load_euroc_gt(seq):
    """Load EuRoC ground truth. Try multiple possible paths."""
    possible = [
        EUROC_DIR / seq / "mav0" / "state_groundtruth_estimate0" / "data.csv",
        BASE / "data" / "euroc" / seq / "mav0" / "state_groundtruth_estimate0" / "data.csv",
    ]
    for p in possible:
        if p.exists():
            return file_interface.read_euroc_csv_trajectory(str(p))
    return None


def load_estimated(algo, seq):
    """Load estimated trajectory files. Returns list of (name, traj)."""
    results = []

    # Directory with multiple runs
    run_dir = TRAJ_DIR / algo / seq
    if run_dir.is_dir():
        for f in sorted(run_dir.glob("*.txt")):
            try:
                traj = file_interface.read_tum_trajectory_file(str(f))
                results.append((f.stem, traj))
            except:
                pass

    # Single file
    flat = TRAJ_DIR / algo / f"{seq}.txt"
    if flat.exists() and not results:
        try:
            traj = file_interface.read_tum_trajectory_file(str(flat))
            results.append((flat.stem, traj))
        except:
            pass

    return results


def compute_errors(traj_ref, traj_est):
    """Align and compute per-timestep position errors."""
    traj_ref_s, traj_est_s = sync.associate_trajectories(traj_ref, traj_est)
    traj_est_aligned = trajectory.align_trajectory(
        traj_est_s, traj_ref_s, correct_scale=False
    )
    errors = np.linalg.norm(
        traj_est_aligned.positions_xyz - traj_ref_s.positions_xyz, axis=1
    )
    timestamps = traj_ref_s.timestamps - traj_ref_s.timestamps[0]
    ate = float(np.sqrt(np.mean(errors**2)))
    return errors, timestamps, ate


print("=" * 60)
print("STEP 3: Computing position errors")
print("=" * 60)

# Store all results: {(algo, seq): {"errors": ..., "timestamps": ..., "ate": ...}}
all_data = {}

for seq in EUROC_SEQUENCES:
    gt = load_euroc_gt(seq)
    if gt is None:
        print(f"  SKIP {seq}: no ground truth found")
        continue

    for algo in ALGORITHMS:
        runs = load_estimated(algo, seq)
        if not runs:
            continue

        # Compute errors for each run, pick median ATE
        run_results = []
        for name, traj_est in runs:
            try:
                errors, timestamps, ate = compute_errors(gt, traj_est)
                run_results.append((name, errors, timestamps, ate))
            except Exception as e:
                print(f"    WARN: {algo}/{seq}/{name}: {e}")

        if not run_results:
            continue

        # Select median ATE run
        run_results.sort(key=lambda x: x[3])
        median = run_results[len(run_results) // 2]
        name, errors, timestamps, ate = median

        all_data[(algo, seq)] = {
            "errors": errors,
            "timestamps": timestamps,
            "ate": ate,
            "num_runs": len(run_results),
        }

        print(f"  OK {algo:12s} / {seq:18s} | ATE = {ate*100:6.2f} cm | "
              f"peak = {np.max(errors)*100:6.2f} cm | {len(run_results)} runs")

print(f"\nTotal pairs: {len(all_data)}")


# ================================================================
# STEP 4: Compute SESR / CSE / critical clearance
# ================================================================

print("\n" + "=" * 60)
print("STEP 4: Computing SESR metrics")
print("=" * 60)


def compute_sesr(errors, clearance, dt=0.05, tau_values=(0.3, 0.5, 0.7)):
    """Compute all SESR-Bench metrics."""
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


# Compute SESR for all pairs under all clearance profiles
sesr_results = {}

for (algo, seq), data in all_data.items():
    errors = data["errors"]
    ts = data["timestamps"]
    dt = float(np.mean(np.diff(ts))) if len(ts) > 1 else 0.05

    sesr_results[(algo, seq)] = {}

    # Uniform sweep
    for c0 in UNIFORM_CLEARANCES:
        key = f"uniform_{c0:.2f}"
        c = uniform_clearance(len(errors), c0)
        sesr_results[(algo, seq)][key] = compute_sesr(errors, c, dt)

    # Sinusoidal
    c = sinusoidal_clearance(ts)
    sesr_results[(algo, seq)]["sinusoidal"] = compute_sesr(errors, c, dt)

    # Step
    c = step_clearance(ts)
    sesr_results[(algo, seq)]["step"] = compute_sesr(errors, c, dt)

    # Error-correlated
    c = error_correlated_clearance(errors)
    sesr_results[(algo, seq)]["error_correlated"] = compute_sesr(errors, c, dt)

print(f"Computed SESR for {len(sesr_results)} pairs x {len(UNIFORM_CLEARANCES) + 3} profiles")


# ================================================================
# STEP 5: Generate figures
# ================================================================

print("\n" + "=" * 60)
print("STEP 5: Generating figures")
print("=" * 60)


# --- Figure 1: Three-panel time series (step clearance) ---

def plot_three_panel(algo, seq, clearance_func, clearance_name, filename):
    """The money figure: error, clearance, SESR stacked."""
    if (algo, seq) not in all_data:
        print(f"  SKIP {filename}: no data for {algo}/{seq}")
        return

    errors = all_data[(algo, seq)]["errors"]
    ts = all_data[(algo, seq)]["timestamps"]
    c = clearance_func(ts) if "ts" in clearance_func.__code__.co_varnames else clearance_func(len(errors))
    sesr = errors / c

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 7), sharex=True)

    # Top: position error
    ax1.plot(ts, errors * 100, "k-", linewidth=0.6)
    ax1.set_ylabel("Position Error (cm)")
    ax1.grid(True, alpha=0.3)

    # Middle: clearance
    ax2.plot(ts, c, "b-", linewidth=0.8)
    ax2.set_ylabel("Clearance (m)")
    ax2.grid(True, alpha=0.3)

    # Bottom: SESR
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


# Use the best-data algorithm on MH_03 for the main figures
# Try VINS-Mono first, fall back to whatever is available
main_algo = None
main_seq = "MH_03_medium"
for candidate in ["vins_mono", "orbslam3", "basalt", "openvins"]:
    if (candidate, main_seq) in all_data:
        main_algo = candidate
        break

if main_algo:
    plot_three_panel(
        main_algo, main_seq,
        lambda ts: step_clearance(ts),
        "step",
        "fig1_step_clearance.pdf"
    )
    plot_three_panel(
        main_algo, main_seq,
        lambda ts: sinusoidal_clearance(ts),
        "sinusoidal",
        "fig2_sinusoidal_clearance.pdf"
    )
else:
    print("  WARNING: No data for MH_03_medium. Skipping main figures.")


# --- Figure 3: SESR breach heatmap ---

def plot_breach_heatmap(c0, filename):
    """Heatmap: algorithms x sequences, color = breach %."""
    profile_key = f"uniform_{c0:.2f}"

    # Build matrix
    active_algos = [a for a in ALGORITHMS if any((a, s) in sesr_results for s in EUROC_SEQUENCES)]
    active_seqs = [s for s in EUROC_SEQUENCES if any((a, s) in sesr_results for a in ALGORITHMS)]

    if not active_algos or not active_seqs:
        print(f"  SKIP {filename}: no data")
        return

    matrix = np.full((len(active_algos), len(active_seqs)), np.nan)

    for i, algo in enumerate(active_algos):
        for j, seq in enumerate(active_seqs):
            if (algo, seq) in sesr_results and profile_key in sesr_results[(algo, seq)]:
                matrix[i, j] = sesr_results[(algo, seq)][profile_key]["sesr_breach_pct"]

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.heatmap(
        matrix,
        annot=True, fmt=".1f",
        xticklabels=[s.replace("_", " ") for s in active_seqs],
        yticklabels=[ALGO_DISPLAY.get(a, a) for a in active_algos],
        cmap="YlOrRd",
        vmin=0, vmax=30,
        ax=ax,
        linewidths=0.5,
    )
    ax.set_title(f"SESR Breach Rate (%) at $c_0$ = {c0} m")
    plt.tight_layout()

    outpath = FIGURES_DIR / filename
    plt.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {outpath}")


plot_breach_heatmap(0.10, "fig3_heatmap_c010.pdf")
plot_breach_heatmap(0.15, "fig4_heatmap_c015.pdf")


# --- Figure 4: Critical clearance bar chart ---

def plot_cstar_bars(filename):
    """Bar chart: mean critical clearance per algorithm."""
    algo_cstars = defaultdict(list)

    for (algo, seq), data in all_data.items():
        if seq in EUROC_SEQUENCES:
            algo_cstars[algo].append(np.max(data["errors"]) * 100)  # cm

    if not algo_cstars:
        print(f"  SKIP {filename}: no data")
        return

    algos = sorted(algo_cstars.keys(), key=lambda a: np.mean(algo_cstars[a]))
    means = [np.mean(algo_cstars[a]) for a in algos]
    stds = [np.std(algo_cstars[a]) for a in algos]
    labels = [ALGO_DISPLAY.get(a, a) for a in algos]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(labels, means, xerr=stds, color="steelblue", alpha=0.8, capsize=4)
    ax.set_xlabel("Mean Critical Clearance $c^*$ (cm)")
    ax.set_title("Minimum Safe Deployment Clearance (EuRoC)")
    ax.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()

    outpath = FIGURES_DIR / filename
    plt.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {outpath}")


plot_cstar_bars("fig5_cstar_bars.pdf")


# ================================================================
# STEP 6: Generate LaTeX tables
# ================================================================

print("\n" + "=" * 60)
print("STEP 6: Generating LaTeX tables")
print("=" * 60)


# --- Table 1: Main leaderboard ---

def generate_leaderboard_latex(sequences, c0_values=[0.15, 0.10], filename="table1_leaderboard.tex"):
    """Generate the main SESR-Bench leaderboard table."""
    lines = []
    lines.append("% Auto-generated by sesr_local_pipeline.py")
    lines.append("% Replace the placeholder table in the paper with this content")
    lines.append("")

    for seq in sequences:
        lines.append(f"% --- {seq} ---")
        for algo in ALGORITHMS:
            if (algo, seq) not in all_data:
                continue

            ate_cm = all_data[(algo, seq)]["ate"] * 100
            c_star = np.max(all_data[(algo, seq)]["errors"]) * 100

            parts = [ALGO_DISPLAY.get(algo, algo), f"{ate_cm:.1f}", f"{c_star:.1f}"]

            for c0 in c0_values:
                key = f"uniform_{c0:.2f}"
                if (algo, seq) in sesr_results and key in sesr_results[(algo, seq)]:
                    r = sesr_results[(algo, seq)][key]
                    parts.extend([
                        f"{r['sesr_mean']:.2f}",
                        f"{r['sesr_max']:.2f}",
                        f"{r['sesr_breach_pct']:.1f}",
                    ])
                else:
                    parts.extend(["--", "--", "--"])

            lines.append(" & ".join(parts) + " \\\\")
        lines.append("\\midrule")

    outpath = TABLES_DIR / filename
    with open(outpath, "w") as f:
        f.write("\n".join(lines))
    print(f"  Saved: {outpath}")


generate_leaderboard_latex(EUROC_SEQUENCES)


# --- Table 2: Critical clearance ---

def generate_cstar_latex(filename="table2_cstar.tex"):
    """Generate critical clearance table."""
    lines = ["% Auto-generated critical clearance table"]

    for algo in ALGORITHMS:
        values = []
        for seq in EUROC_SEQUENCES:
            if (algo, seq) in all_data:
                c_star = np.max(all_data[(algo, seq)]["errors"]) * 100
                values.append(f"{c_star:.1f}")
            else:
                values.append("--")

        mean_vals = [
            np.max(all_data[(algo, s)]["errors"]) * 100
            for s in EUROC_SEQUENCES
            if (algo, s) in all_data
        ]
        mean_str = f"{np.mean(mean_vals):.1f}" if mean_vals else "--"

        line = f"{ALGO_DISPLAY.get(algo, algo)} & " + " & ".join(values) + f" & {mean_str} \\\\"
        lines.append(line)

    outpath = TABLES_DIR / filename
    with open(outpath, "w") as f:
        f.write("\n".join(lines))
    print(f"  Saved: {outpath}")


generate_cstar_latex()


# --- Table 3: Ranking inversions ---

def generate_inversion_latex(filename="table3_inversions.tex"):
    """Count ATE vs SESR ranking inversions."""
    lines = ["% Auto-generated ranking inversion table"]

    for c0 in UNIFORM_CLEARANCES:
        profile_key = f"uniform_{c0:.2f}"
        rank1_inv = 0
        top3_reorder = 0
        total_seqs = 0

        for seq in EUROC_SEQUENCES:
            # Get ATE ranking
            ate_ranking = []
            sesr_ranking = []
            for algo in ALGORITHMS:
                if (algo, seq) not in all_data:
                    continue
                if (algo, seq) not in sesr_results:
                    continue
                if profile_key not in sesr_results[(algo, seq)]:
                    continue

                ate_val = all_data[(algo, seq)]["ate"]
                sesr_val = sesr_results[(algo, seq)][profile_key]["sesr_breach_pct"]
                ate_ranking.append((algo, ate_val))
                sesr_ranking.append((algo, sesr_val))

            if len(ate_ranking) < 3:
                continue

            total_seqs += 1
            ate_sorted = [a for a, _ in sorted(ate_ranking, key=lambda x: x[1])]
            sesr_sorted = [a for a, _ in sorted(sesr_ranking, key=lambda x: x[1])]

            if ate_sorted[0] != sesr_sorted[0]:
                rank1_inv += 1
            if set(ate_sorted[:3]) != set(sesr_sorted[:3]):
                top3_reorder += 1

        if total_seqs > 0:
            lines.append(
                f"{c0:.2f} & {rank1_inv}/{total_seqs} & {top3_reorder}/{total_seqs} \\\\"
            )

    outpath = TABLES_DIR / filename
    with open(outpath, "w") as f:
        f.write("\n".join(lines))
    print(f"  Saved: {outpath}")


generate_inversion_latex()


# ================================================================
# SAVE FULL RESULTS AS JSON
# ================================================================

print("\n" + "=" * 60)
print("Saving full results")
print("=" * 60)

# Convert to serializable format
export = {}
for (algo, seq), data in all_data.items():
    key = f"{algo}__{seq}"
    export[key] = {
        "algorithm": algo,
        "sequence": seq,
        "ate_cm": round(data["ate"] * 100, 2),
        "c_star_cm": round(float(np.max(data["errors"])) * 100, 2),
        "peak_error_cm": round(float(np.max(data["errors"])) * 100, 2),
        "num_points": len(data["errors"]),
        "duration_s": round(float(data["timestamps"][-1]), 1),
    }

    # Add SESR results for key clearance values
    for c0 in [0.10, 0.15, 0.30]:
        pkey = f"uniform_{c0:.2f}"
        if (algo, seq) in sesr_results and pkey in sesr_results[(algo, seq)]:
            r = sesr_results[(algo, seq)][pkey]
            export[key][f"sesr_mean_c{int(c0*100):02d}"] = round(r["sesr_mean"], 4)
            export[key][f"sesr_max_c{int(c0*100):02d}"] = round(r["sesr_max"], 4)
            export[key][f"breach_pct_c{int(c0*100):02d}"] = round(r["sesr_breach_pct"], 2)

json_path = RESULTS_DIR / "sesr_bench_full_results.json"
with open(json_path, "w") as f:
    json.dump(export, f, indent=2)
print(f"  Saved: {json_path}")


# ================================================================
# FINAL SUMMARY
# ================================================================

print("\n" + "=" * 60)
print("PIPELINE COMPLETE")
print("=" * 60)
print(f"""
Results directory: {RESULTS_DIR}/
  figures/
    fig1_step_clearance.pdf        <- THE money figure
    fig2_sinusoidal_clearance.pdf
    fig3_heatmap_c010.pdf          <- Single-glance leaderboard
    fig4_heatmap_c015.pdf
    fig5_cstar_bars.pdf
  tables/
    table1_leaderboard.tex         <- Copy into paper
    table2_cstar.tex
    table3_inversions.tex
  sesr_bench_full_results.json     <- All numbers

Next steps:
  1. Open the paper LaTeX file
  2. Replace placeholder tables with the generated .tex files
  3. Replace placeholder figures with the generated .pdf files
  4. Verify ATE values against published papers (see Step 3 output)
  5. Compile and proofread
  6. Post to arXiv
""")
