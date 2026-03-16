#!/usr/bin/env python3
"""
Generate the three key figures for Paper B1 (SESR-Bench).

Figure 1: Clearance profile families (what SESR evaluates against)
Figure 2: ATE vs SESR ranking divergence (the money plot)
Figure 3: Silent failure example (single trajectory deep dive)

Run from ~/sesr/:
    python3 scripts/generate_key_figures.py
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ================================================================
# Load results
# ================================================================

REPO = Path.home() / "sesr"
RESULTS = REPO / "results"
FIGURES = RESULTS / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

with open(RESULTS / "sesr_bench_results.json") as f:
    data = json.load(f)

ALGO_DISPLAY = {
    "orbslam3": "ORB-SLAM3",
    "basalt": "BASALT",
    "openvins": "OpenVINS",
    "vins_fusion": "VINS-Fusion",
    "rovio": "ROVIO",
    "svo2": "SVO2",
    "kimera": "Kimera-VIO",
}

ALGO_COLORS = {
    "orbslam3": "#1f77b4",
    "basalt": "#ff7f0e",
    "openvins": "#2ca02c",
    "vins_fusion": "#d62728",
    "rovio": "#9467bd",
    "svo2": "#8c564b",
    "kimera": "#e377c2",
}

ALGORITHMS = ["orbslam3", "basalt", "openvins", "vins_fusion", "rovio", "svo2", "kimera"]
SEQUENCES = ["MH01", "MH02", "MH03", "MH05", "V101", "V202"]


# ================================================================
# FIGURE 1: Clearance Profile Families
# ================================================================

def figure1_clearance_profiles():
    """Show the four clearance profile types used in evaluation."""
    t = np.linspace(0, 60, 1200)

    fig, axes = plt.subplots(2, 2, figsize=(10, 6), sharex=True)

    # Uniform
    ax = axes[0, 0]
    for c0, alpha in [(0.05, 0.3), (0.10, 0.5), (0.15, 0.65), (0.20, 0.75), (0.30, 0.85), (0.50, 0.95), (1.00, 1.0)]:
        ax.axhline(y=c0, alpha=alpha, color="steelblue", linewidth=1.5)
    ax.set_ylabel("Clearance (m)")
    ax.set_title("(a) Uniform", fontsize=11)
    ax.set_ylim(0, 1.1)
    ax.grid(True, alpha=0.2)

    # Sinusoidal
    ax = axes[0, 1]
    c = np.maximum(0.01, 0.3 + 0.2 * np.sin(2 * np.pi * t / 10.0))
    ax.plot(t, c, color="steelblue", linewidth=1.5)
    ax.fill_between(t, 0, c, alpha=0.15, color="steelblue")
    ax.set_title("(b) Sinusoidal", fontsize=11)
    ax.set_ylim(0, 0.6)
    ax.grid(True, alpha=0.2)

    # Step
    ax = axes[1, 0]
    phase = (t // 15).astype(int) % 2
    c = np.where(phase == 0, 1.0, 0.10)
    ax.plot(t, c, color="steelblue", linewidth=1.5)
    ax.fill_between(t, 0, c, alpha=0.15, color="steelblue")
    ax.set_ylabel("Clearance (m)")
    ax.set_xlabel("Time (s)")
    ax.set_title("(c) Step (wide/narrow)", fontsize=11)
    ax.set_ylim(0, 1.2)
    ax.grid(True, alpha=0.2)

    # Error-correlated
    ax = axes[1, 1]
    # Simulate a fake error trajectory for illustration
    np.random.seed(42)
    fake_error = np.abs(0.03 + 0.02 * np.cumsum(np.random.randn(len(t)) * 0.01))
    c = np.maximum(0.05, 0.5 - 2.0 * fake_error)
    ax.plot(t, c, color="steelblue", linewidth=1.5, label="clearance")
    ax.plot(t, fake_error, color="red", linewidth=0.8, alpha=0.7, label="error")
    ax.fill_between(t, 0, c, alpha=0.15, color="steelblue")
    ax.set_xlabel("Time (s)")
    ax.set_title("(d) Error-correlated", fontsize=11)
    ax.set_ylim(0, 0.6)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.2)

    fig.suptitle("Synthetic Clearance Profiles for SESR Evaluation", fontsize=13, y=1.01)
    plt.tight_layout()
    outpath = FIGURES / "fig1_clearance_profiles.pdf"
    plt.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {outpath}")


# ================================================================
# FIGURE 2: ATE vs SESR Ranking Divergence (THE MONEY PLOT)
# ================================================================

def figure2_ate_vs_sesr_divergence():
    """
    Scatter plot: x = ATE RMSE, y = SESR breach rate at c=0.15m.
    Each point is one (algorithm, sequence) pair.
    Color by algorithm. Annotate ranking inversions.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for ax_idx, (c_key, c_label, c_val) in enumerate([
        ("breach_pct_c15", "c = 0.15 m", 0.15),
        ("breach_pct_c10", "c = 0.10 m", 0.10),
    ]):
        ax = axes[ax_idx]

        for algo in ALGORITHMS:
            ates = []
            breaches = []
            for seq in SEQUENCES:
                key = f"{algo}__{seq}"
                if key in data and c_key in data[key]:
                    ates.append(data[key]["ate_cm"])
                    breaches.append(data[key][c_key])

            if ates:
                ax.scatter(ates, breaches,
                           label=ALGO_DISPLAY.get(algo, algo),
                           color=ALGO_COLORS.get(algo, "gray"),
                           s=70, alpha=0.85, edgecolors="white", linewidth=0.5, zorder=3)

        ax.set_xlabel("ATE RMSE (cm)", fontsize=11)
        ax.set_ylabel(f"SESR Breach Rate (%) at {c_label}", fontsize=11)
        ax.set_title(f"ATE vs SESR Breach Rate ({c_label})", fontsize=12)
        ax.legend(fontsize=8, loc="upper left", framealpha=0.9)
        ax.grid(True, alpha=0.2)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=-1)

        # Add annotation: "same ATE, different SESR" region
        if ax_idx == 1:
            ax.annotate("Same ATE,\ndifferent SESR",
                         xy=(8, 25), fontsize=9, color="red", alpha=0.7,
                         ha="center", style="italic")

    plt.tight_layout()
    outpath = FIGURES / "fig2_ate_vs_sesr_divergence.pdf"
    plt.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {outpath}")


# ================================================================
# FIGURE 2b: Ranking Inversion Bar Chart
# ================================================================

def figure2b_ranking_inversion():
    """
    For each sequence, rank algorithms by ATE and by SESR breach rate.
    Show how many rank-1 and top-3 inversions occur.
    """
    clearances = [0.05, 0.10, 0.15, 0.20, 0.30]
    c_labels = ["5cm", "10cm", "15cm", "20cm", "30cm"]

    rank1_inversions = []
    top3_reorders = []

    for c_val in clearances:
        c_key = f"breach_pct_c{int(c_val*100):02d}"
        r1_inv = 0
        t3_inv = 0
        total = 0

        for seq in SEQUENCES:
            ate_ranking = []
            sesr_ranking = []
            for algo in ALGORITHMS:
                key = f"{algo}__{seq}"
                if key in data and c_key in data[key]:
                    ate_ranking.append((algo, data[key]["ate_cm"]))
                    sesr_ranking.append((algo, data[key][c_key]))

            if len(ate_ranking) < 3:
                continue

            total += 1
            ate_sorted = [a for a, _ in sorted(ate_ranking, key=lambda x: x[1])]
            sesr_sorted = [a for a, _ in sorted(sesr_ranking, key=lambda x: x[1])]

            if ate_sorted[0] != sesr_sorted[0]:
                r1_inv += 1
            if set(ate_sorted[:3]) != set(sesr_sorted[:3]):
                t3_inv += 1

        rank1_inversions.append(r1_inv)
        top3_reorders.append(t3_inv)

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(clearances))
    width = 0.35
    ax.bar(x - width/2, rank1_inversions, width, label="Rank-1 inversion", color="#d62728", alpha=0.8)
    ax.bar(x + width/2, top3_reorders, width, label="Top-3 reorder", color="#ff7f0e", alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{c_labels[i]}" for i in range(len(clearances))])
    ax.set_xlabel("Clearance", fontsize=11)
    ax.set_ylabel("Number of sequences (out of 6)", fontsize=11)
    ax.set_title("ATE vs SESR Ranking Inversions by Clearance", fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, axis="y", alpha=0.2)
    ax.set_ylim(0, 7)

    plt.tight_layout()
    outpath = FIGURES / "fig2b_ranking_inversions.pdf"
    plt.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {outpath}")


# ================================================================
# FIGURE 3: Silent Failure Example
# ================================================================

def figure3_silent_failure():
    """
    Three-panel deep dive on a single algorithm/sequence showing:
    Top: position error over time
    Middle: clearance profile (step)
    Bottom: SESR with breach threshold
    
    Pick an algorithm where ATE looks "fine" but SESR breaches.
    Best candidate: an algorithm with moderate ATE on a medium sequence.
    """
    # We need the actual trajectory data for this, not just the JSON summary.
    # Re-run a minimal computation for the best candidate.
    
    try:
        from evo.core import trajectory, sync, geometry
        from evo.tools import file_interface
    except ImportError:
        print("  SKIP fig3: evo not installed")
        return

    TRAJ_DIR = REPO / "data" / "trajectories"
    GT_DIR = REPO / "data" / "groundtruth"

    # Pick BASALT on MH05 (ATE ~14.5 cm, peak 25 cm - looks fine, but breaches at 15cm clearance)
    # Or SVO2 on V202 (ATE 13.8, peak 62 cm - big peak error)
    # Best: SVO2 on MH05 (ATE 15.7 cm, peak 55.6 cm)
    
    candidates = [
        ("svo2", "MH05", "SVO2 on MH05"),
        ("vins_fusion", "MH03", "VINS-Fusion on MH03"),
        ("kimera", "MH02", "Kimera-VIO on MH02"),
    ]

    for algo, seq, title_str in candidates:
        # Load GT
        gt_file = GT_DIR / f"{seq}_gt.csv"
        if not gt_file.exists():
            continue
        gt = file_interface.read_euroc_csv_trajectory(str(gt_file))

        # Load trajectory (median run = run3)
        if algo == "basalt":
            seq_map = {"MH01":"MH1","MH02":"MH2","MH03":"MH3","MH05":"MH5","V101":"V11","V202":"V22"}
            pattern = f"{seq_map.get(seq, seq)}_run3.txt"
        else:
            pattern = f"{seq}_run3.txt"

        traj_file = TRAJ_DIR / algo / pattern
        if not traj_file.exists():
            continue

        # Parse with ns handling
        timestamps = []
        xyz = []
        quat = []
        with open(traj_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) < 8:
                    continue
                try:
                    t = float(parts[0])
                    if t > 1e15:
                        t = t / 1e9
                    timestamps.append(t)
                    xyz.append([float(parts[1]), float(parts[2]), float(parts[3])])
                    qx, qy, qz, qw = float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])
                    quat.append([qw, qx, qy, qz])
                except:
                    continue

        if len(timestamps) < 100:
            continue

        est = trajectory.PoseTrajectory3D(
            positions_xyz=np.array(xyz),
            orientations_quat_wxyz=np.array(quat),
            timestamps=np.array(timestamps),
        )

        gt_s, est_s = sync.associate_trajectories(gt, est, max_diff=0.05)
        if len(gt_s.timestamps) < 100:
            continue

        r, t_vec, s = geometry.umeyama_alignment(
            est_s.positions_xyz.T, gt_s.positions_xyz.T, with_scale=False
        )
        aligned = (r @ est_s.positions_xyz.T + t_vec[:, np.newaxis]).T
        errors = np.linalg.norm(aligned - gt_s.positions_xyz, axis=1)
        ts = gt_s.timestamps - gt_s.timestamps[0]

        ate_cm = np.sqrt(np.mean(errors**2)) * 100

        # Step clearance
        period = 15.0
        phase = (ts // period).astype(int) % 2
        clearance = np.where(phase == 0, 1.0, 0.10)

        sesr = errors / clearance
        breach_pct = 100.0 * np.mean(sesr >= 1.0)

        # Only plot if there are actual breaches
        if breach_pct < 0.5:
            continue

        # Plot
        fig = plt.figure(figsize=(12, 8))
        gs = gridspec.GridSpec(3, 1, height_ratios=[1, 0.7, 1], hspace=0.08)

        ax1 = fig.add_subplot(gs[0])
        ax2 = fig.add_subplot(gs[1], sharex=ax1)
        ax3 = fig.add_subplot(gs[2], sharex=ax1)

        # Top: position error
        ax1.plot(ts, errors * 100, "k-", linewidth=0.5, alpha=0.8)
        ax1.axhline(y=ate_cm, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
        ax1.text(ts[-1] * 0.02, ate_cm + 1, f"ATE = {ate_cm:.1f} cm", fontsize=9, color="gray")
        ax1.set_ylabel("Position Error (cm)", fontsize=10)
        ax1.grid(True, alpha=0.15)
        ax1.tick_params(labelbottom=False)
        ax1.set_title(f"Silent Failure Example: {title_str}", fontsize=12)

        # Middle: clearance
        ax2.fill_between(ts, 0, clearance, alpha=0.2, color="steelblue")
        ax2.plot(ts, clearance, "b-", linewidth=1.0)
        ax2.set_ylabel("Clearance (m)", fontsize=10)
        ax2.set_ylim(0, 1.2)
        ax2.grid(True, alpha=0.15)
        ax2.tick_params(labelbottom=False)

        # Bottom: SESR
        # Color breaches red
        ax3.plot(ts, sesr, color="darkred", linewidth=0.5, alpha=0.7)
        breach_mask = sesr >= 1.0
        if np.any(breach_mask):
            ax3.fill_between(ts, 1.0, sesr, where=breach_mask,
                             color="red", alpha=0.3, label=f"Breach ({breach_pct:.1f}% of trajectory)")
        ax3.axhline(y=1.0, color="black", linestyle="--", linewidth=1.0, alpha=0.8)
        ax3.text(ts[-1] * 0.98, 1.05, "SESR = 1 (collision boundary)", fontsize=8,
                 ha="right", color="black", alpha=0.7)
        ax3.set_ylabel("SESR", fontsize=10)
        ax3.set_xlabel("Time (s)", fontsize=10)
        ax3.grid(True, alpha=0.15)
        if np.any(breach_mask):
            ax3.legend(fontsize=9, loc="upper left")

        # Add ATE verdict annotation
        fig.text(0.5, -0.02,
                 f"ATE verdict: {ate_cm:.1f} cm (acceptable)    |    "
                 f"SESR verdict: {breach_pct:.1f}% of trajectory exceeds clearance (unsafe)",
                 ha="center", fontsize=10, style="italic", color="darkred")

        outpath = FIGURES / f"fig3_silent_failure_{algo}_{seq}.pdf"
        plt.savefig(outpath, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"  Saved: {outpath}")
        break  # Only need one good example

    else:
        # If no candidate had breaches with step clearance, try uniform 0.15m
        print("  Trying uniform clearance for silent failure figure...")
        for algo, seq, title_str in [
            ("svo2", "V202", "SVO2 on V202"),
            ("vins_fusion", "MH03", "VINS-Fusion on MH03"),
            ("rovio", "V101", "ROVIO on V101"),
        ]:
            key = f"{algo}__{seq}"
            if key in data and "breach_pct_c15" in data[key]:
                if data[key]["breach_pct_c15"] > 1.0:
                    print(f"  Found candidate: {algo}/{seq} with {data[key]['breach_pct_c15']}% breach at c=15cm")
                    # Would need to re-run trajectory loading here
                    break


# ================================================================
# FIGURE 4: Algorithm Comparison Heatmap (improved)
# ================================================================

def figure4_comparison_heatmap():
    """
    Side-by-side heatmaps: ATE vs SESR breach rate.
    Shows the ranking divergence at a glance.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # ATE heatmap
    ate_matrix = np.full((len(ALGORITHMS), len(SEQUENCES)), np.nan)
    for i, algo in enumerate(ALGORITHMS):
        for j, seq in enumerate(SEQUENCES):
            key = f"{algo}__{seq}"
            if key in data:
                ate_matrix[i, j] = data[key]["ate_cm"]

    import seaborn as sns
    sns.heatmap(ate_matrix, annot=True, fmt=".1f",
                xticklabels=SEQUENCES,
                yticklabels=[ALGO_DISPLAY.get(a, a) for a in ALGORITHMS],
                cmap="YlOrRd", vmin=0, vmax=80, ax=ax1, linewidths=0.5)
    ax1.set_title("ATE RMSE (cm)", fontsize=12)

    # SESR breach heatmap at c=0.15m
    sesr_matrix = np.full((len(ALGORITHMS), len(SEQUENCES)), np.nan)
    for i, algo in enumerate(ALGORITHMS):
        for j, seq in enumerate(SEQUENCES):
            key = f"{algo}__{seq}"
            if key in data and "breach_pct_c15" in data[key]:
                sesr_matrix[i, j] = data[key]["breach_pct_c15"]

    sns.heatmap(sesr_matrix, annot=True, fmt=".1f",
                xticklabels=SEQUENCES,
                yticklabels=[ALGO_DISPLAY.get(a, a) for a in ALGORITHMS],
                cmap="YlOrRd", vmin=0, vmax=50, ax=ax2, linewidths=0.5)
    ax2.set_title("SESR Breach Rate (%) at c = 0.15 m", fontsize=12)

    fig.suptitle("ATE vs SESR: Same Data, Different Story", fontsize=14, y=1.02)
    plt.tight_layout()
    outpath = FIGURES / "fig4_ate_vs_sesr_heatmaps.pdf"
    plt.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {outpath}")


# ================================================================
# FIGURE 5: Critical Clearance c* (the deployment threshold)
# ================================================================

def figure5_critical_clearance():
    """
    Bar chart: for each algorithm, what is the minimum clearance
    at which you can deploy without ANY breach?
    c* = max(error) across all sequences = the minimum safe clearance.
    """
    algo_cstars = defaultdict(list)
    for algo in ALGORITHMS:
        for seq in SEQUENCES:
            key = f"{algo}__{seq}"
            if key in data:
                algo_cstars[algo].append(data[key]["c_star_cm"])

    algos_sorted = sorted(algo_cstars.keys(), key=lambda a: np.mean(algo_cstars[a]))
    means = [np.mean(algo_cstars[a]) for a in algos_sorted]
    maxes = [np.max(algo_cstars[a]) for a in algos_sorted]
    mins = [np.min(algo_cstars[a]) for a in algos_sorted]
    labels = [ALGO_DISPLAY.get(a, a) for a in algos_sorted]

    fig, ax = plt.subplots(figsize=(9, 5))
    y_pos = np.arange(len(algos_sorted))
    
    # Bar for mean, error bars showing min-max range
    bars = ax.barh(y_pos, means, color=[ALGO_COLORS.get(a, "gray") for a in algos_sorted],
                   alpha=0.8, height=0.6)
    
    # Add min-max range
    for i in range(len(algos_sorted)):
        ax.plot([mins[i], maxes[i]], [y_pos[i], y_pos[i]], "k-", linewidth=2, alpha=0.5)
        ax.plot(mins[i], y_pos[i], "k|", markersize=10, alpha=0.5)
        ax.plot(maxes[i], y_pos[i], "k|", markersize=10, alpha=0.5)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Critical Clearance c* (cm)", fontsize=11)
    ax.set_title("Minimum Safe Deployment Clearance per Algorithm", fontsize=12)
    ax.grid(True, axis="x", alpha=0.2)

    # Add deployment zone annotations
    ax.axvline(x=10, color="green", linestyle="--", alpha=0.4, linewidth=1)
    ax.axvline(x=30, color="orange", linestyle="--", alpha=0.4, linewidth=1)
    ax.axvline(x=100, color="red", linestyle="--", alpha=0.4, linewidth=1)
    ax.text(5, len(algos_sorted) - 0.3, "tight", fontsize=8, color="green", alpha=0.6)
    ax.text(18, len(algos_sorted) - 0.3, "moderate", fontsize=8, color="orange", alpha=0.6)
    ax.text(60, len(algos_sorted) - 0.3, "wide only", fontsize=8, color="red", alpha=0.6)

    plt.tight_layout()
    outpath = FIGURES / "fig5_critical_clearance.pdf"
    plt.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {outpath}")


# ================================================================
# Run all
# ================================================================

if __name__ == "__main__":
    print("Generating key figures for Paper B1...")
    print()
    figure1_clearance_profiles()
    figure2_ate_vs_sesr_divergence()
    figure2b_ranking_inversion()
    figure3_silent_failure()
    figure4_comparison_heatmap()
    figure5_critical_clearance()
    print()
    print("Done. Key figures saved to:", FIGURES)
