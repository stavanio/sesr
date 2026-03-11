# Results

This directory contains SESR-Bench evaluation results.

## Structure

```
results/
  euroc/                    # Per-algorithm results on EuRoC
    orbslam3/
      MH_01_easy.json       # SESR metrics for all clearance profiles
      MH_02_easy.json
      ...
    vins_mono/
      ...
  tartanair/                # Per-algorithm results on TartanAir
    ...
  figures/                  # Generated PDF figures for the paper
    fig1_step_clearance.pdf
    fig2_sinusoidal_clearance.pdf
    fig3_heatmap_c010.pdf
    fig5_cstar_bars.pdf
  tables/                   # Generated LaTeX table content
    table1_leaderboard.tex
    table2_cstar.tex
    table3_inversions.tex
  sesr_bench_full_results.json  # Complete results in one file
```

## Reproducing

```bash
pip install sesr-bench[all]
python scripts/evaluate_all.py
```

## Submitting Your Algorithm

1. Run your VIO on EuRoC sequences
2. Evaluate with SESR-Bench:
   ```bash
   sesr-bench full --gt MH_01_gt.csv --est your_MH01.txt --format euroc --output json > results.json
   ```
3. Submit a PR adding your results to this directory
