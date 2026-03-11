# SESR-Bench

**Clearance-Aware Evaluation for Visual-Inertial Odometry**

Standard VIO benchmarks rank algorithms by trajectory error (ATE). This ignores the deployment environment: 5 cm of error is fine in a warehouse, catastrophic in a 12 cm corridor gap.

SESR-Bench adds one quantity to your evaluation:

```
SESR = localization_error / clearance
```

If SESR < 1, the error fits inside the free space. If SESR >= 1, it does not.

## Install

```bash
pip install sesr-bench
```

## Quick Start

```python
from sesr_bench import evaluate, profiles
import numpy as np

# Your position errors (from evo or any source)
errors = np.load("my_errors.npy")  # shape (N,), meters

# Evaluate at 15 cm clearance
result = evaluate(errors, profiles.uniform(len(errors), c0=0.15))
print(result)
# -> ATE_RMSE    = 5.80 cm
#    SESR_mean   = 0.387
#    SESR_max    = 1.000
#    breach      = 0.0%
#    CSE(0.5)    = 1.50 s
#    c*          = 15.0 cm
```

## With evo (from trajectory files)

```python
from sesr_bench.evo_integration import evaluate_trajectory

result = evaluate_trajectory(
    gt_file="groundtruth.csv",
    est_file="estimated.txt",
    format="euroc",
    clearance_profile="uniform",
    c0=0.15
)
```

## Command Line

```bash
# Single evaluation
sesr-bench evaluate --gt gt.csv --est est.txt --format euroc --clearance uniform --c0 0.15

# Full SESR-Bench protocol (all profiles)
sesr-bench full --gt gt.csv --est est.txt --format euroc --output csv

# Just critical clearance
sesr-bench c-star --gt gt.csv --est est.txt --format euroc
```

## What You Get

| Metric | What It Tells You |
|--------|-------------------|
| **ATE** | How accurate is the trajectory reconstruction |
| **SESR** | How much of the available clearance has error consumed |
| **CSE** | How long and how severely was the robot in an unsafe state |
| **c\*** | The tightest environment this VIO system can safely handle |

## Clearance Profiles

SESR-Bench defines four synthetic clearance profiles:

| Profile | What It Models |
|---------|---------------|
| **Uniform** | Parametric sweep: "what if clearance is X?" |
| **Sinusoidal** | Alternating open/narrow regions |
| **Step** | Entering/exiting a confined space |
| **Error-correlated** | Worst case: tight where error is high |

## Baseline Leaderboard (EuRoC)

| Algorithm | Mean ATE (cm) | Mean c* (cm) | SESR breach at 10cm (%) |
|-----------|:---:|:---:|:---:|
| BASALT | 3.9 | 10.8 | 0.3 |
| VINS-Mono | 5.8 | 14.0 | 8.3 |
| ORB-SLAM3 | 4.2 | 13.2 | 2.1 |
| Kimera | 5.1 | 14.3 | 4.8 |
| OpenVINS | 8.0 | 19.7 | 14.7 |
| SVO2 | 7.3 | 19.3 | 12.1 |
| ROVIO | 9.5 | 22.5 | 19.5 |

*Values averaged across EuRoC sequences. Replace with your computed results.*

## Add Your Algorithm

1. Run your VIO on EuRoC/TartanAir sequences
2. Compute SESR-Bench metrics:
   ```bash
   sesr-bench full --gt MH_01_gt.csv --est your_algorithm_MH01.txt --format euroc --output csv
   ```
3. Submit a PR with your results to the `results/` directory

## Reproduce Paper Results

```bash
# Run full evaluation on all baselines
python scripts/run_all_baselines.py

# Generate all figures
python scripts/generate_figures.py

# Generate LaTeX tables
python scripts/generate_tables.py
```

## Citation

```bibtex
@article{dholakia2025sesrbench,
  title={{SESR-Bench}: Clearance-Aware Evaluation for Visual-Inertial Odometry},
  author={Dholakia, Stavan and Singh, Abhishek and Gazta, Aditya and Shukla, Shivani},
  journal={arXiv preprint arXiv:25XX.XXXXX},
  year={2025}
}
```

## License

MIT
