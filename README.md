# SESR-Bench

**Clearance-Aware Evaluation for Visual-Inertial Odometry**

Standard VIO benchmarks rank algorithms by trajectory error (ATE). This ignores the deployment environment: 5 cm of error is fine in a warehouse, catastrophic in a 12 cm corridor gap.

SESR-Bench adds one quantity to your evaluation:

```
SESR = localization_error / clearance
```

If SESR < 1, the error fits inside the free space. If SESR >= 1, it does not.

## Dataset

7 VIO algorithms evaluated on 6 EuRoC MAV sequences, 5 runs each (210 trajectory files):

| Algorithm | Type | Source |
|-----------|------|--------|
| ORB-SLAM3 | Optimization (stereo-inertial) | Campos et al., T-RO 2021 |
| BASALT | Optimization (stereo-inertial) | Usenko et al., RA-L 2020 |
| OpenVINS | Filter (MSCKF) | Geneva et al., ICRA 2020 |
| VINS-Fusion | Optimization (stereo-inertial) | Qin et al., T-RO 2018 |
| ROVIO | Filter (direct) | Bloesch et al., IJRR 2017 |
| SVO2 | Semi-direct | Forster et al., T-RO 2017 |
| Kimera-VIO | Optimization (stereo-inertial) | Rosinol et al., ICRA 2020 |

Sequences: MH_01_easy, MH_02_easy, MH_03_medium, MH_05_difficult, V1_01_easy, V2_02_medium.

Each algorithm was executed five times per sequence. Reported values correspond to the median RMSE across runs.

## ATE Results (cm, median run)

| Algorithm | MH01 | MH02 | MH03 | MH05 | V101 | V202 |
|-----------|------|------|------|------|------|------|
| ORB-SLAM3 | 3.9 | 3.6 | 2.8 | 5.7 | 3.9 | 1.3 |
| BASALT | 7.3 | 5.0 | 6.2 | 14.5 | 4.3 | 4.9 |
| OpenVINS | 7.3 | 19.5 | 12.2 | 19.3 | 6.6 | 4.4 |
| SVO2 | 7.9 | 7.6 | 9.2 | 15.7 | 5.6 | 13.8 |
| VINS-Fusion | 26.0 | 22.4 | 30.5 | 32.4 | 11.2 | 12.4 |
| Kimera-VIO | 22.2 | 21.9 | 23.0 | 16.5 | 6.1 | 11.3 |
| ROVIO | 38.6 | 55.7 | 48.6 | 116.4 | 11.8 | 74.3 |

## Install

```bash
pip install evo numpy matplotlib seaborn
```

## Run Evaluation

```bash
cd ~/sesr
python3 scripts/sesr_evaluate.py
```

Outputs to `results/`: figures (PDF), LaTeX tables, and full JSON results.

## Independent Verification

You can spot-check any algorithm using the evo command-line tool:

```bash
# Algorithms with seconds-format timestamps (BASALT, ROVIO, SVO2):
evo_ape euroc data/groundtruth/MH03_gt.csv data/trajectories/basalt/MH3_run3.txt -va --align

# Algorithms with nanosecond timestamps (ORB-SLAM3, OpenVINS):
# First convert timestamps:
python3 scripts/convert_ns_to_seconds.py data/trajectories/orbslam3/MH01_run3.txt /tmp/orbslam3_sec.txt
evo_ape euroc data/groundtruth/MH01_gt.csv /tmp/orbslam3_sec.txt -va --align
```

### Timestamp formats by algorithm

| Algorithm | Timestamp format | evo-compatible? |
|-----------|-----------------|-----------------|
| ORB-SLAM3 | Nanoseconds (float) | Needs conversion |
| BASALT | Nanoseconds (scientific) | Needs conversion |
| OpenVINS | Seconds (float) | Yes |
| VINS-Fusion | CSV, nanoseconds | Custom parser in sesr_evaluate.py |
| ROVIO | Seconds (float) | Yes |
| SVO2 | Seconds (float) | Yes |
| Kimera-VIO | CSV, nanoseconds | Custom parser in sesr_evaluate.py |

## Repository Structure

```
sesr/
  sesr_bench/                    # Core Python package
    metrics.py                   # SESR, CSE computation
    profiles.py                  # Clearance profile generators
    cli.py                       # Command-line interface
  scripts/
    sesr_evaluate.py             # Full evaluation pipeline
    generate_key_figures.py      # Paper figures
    convert_ns_to_seconds.py     # Timestamp conversion for evo
    runs/                        # Reproducibility scripts
      run_all_orbslam3.sh
      run_all_basalt.sh
      run_all_openvins.sh
      run_all_openvins_fixed.sh
      run_all_vins_fusion.sh
      run_all_rovio.sh
      run_all_svo2.sh
      run_all_kimera.sh
      odom_to_tum.py             # ROS Odometry to TUM converter
      pose_to_tum.py             # ROS PoseWithCovariance to TUM converter
  data/
    trajectories/                # 210 trajectory files
      orbslam3/                  # 30 files (TUM format, ns timestamps)
      basalt/                    # 30 files (TUM format, ns timestamps)
      openvins/                  # 30 files (TUM format, seconds)
      vins_fusion/               # 30 files (CSV format)
      rovio/                     # 30 files (TUM format, seconds)
      svo2/                      # 30 files (TUM format, seconds)
      kimera/                    # 30 files (CSV format)
    groundtruth/                 # 6 EuRoC ground truth files
  results/                       # Evaluation outputs
    figures/                     # PDF figures
    tables/                      # LaTeX table fragments
    sesr_bench_results.json      # All numerical results
  tests/
    test_metrics.py
  README.md
  LICENSE
  CITATION.cff
  pyproject.toml
```

## Build Environment

All algorithms were built and run on an Azure Standard_D8ps_v6 VM (ARM64, 8 vCPU, 32 GB RAM, Ubuntu 20.04) with ROS Noetic. Kimera-VIO was run in Docker due to dependency conflicts. All other algorithms were built natively. The evaluation pipeline runs locally on any machine with Python 3.8+.

## Citation

If you use SESR-Bench in your work, please cite:

```bibtex
@article{dholakia2026sesr,
  title={SESR: Clearance-Aware Evaluation for Visual-Inertial Odometry},
  author={Dholakia, Stavan and Singh, Abhishek and Gazta, Aditya and Shukla, Shivani},
  journal={arXiv preprint},
  year={2026}
}
```

## License

MIT
