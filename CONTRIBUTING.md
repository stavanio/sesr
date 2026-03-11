# Contributing to SESR-Bench

## Adding Your Algorithm to the Leaderboard

We welcome results from any VIO or visual odometry algorithm.

### Steps

1. Run your algorithm on the EuRoC sequences listed in the paper:
   - MH_01_easy, MH_02_easy, MH_03_medium, MH_05_difficult
   - V1_01_easy, V2_02_medium

2. Save trajectory estimates in TUM format:
   ```
   timestamp tx ty tz qx qy qz qw
   ```

3. Run the SESR-Bench evaluation:
   ```bash
   pip install sesr-bench[all]
   sesr-bench full --gt <groundtruth> --est <your_trajectory> --format euroc --output json
   ```

4. Submit a pull request with:
   - Your results JSON files in `results/euroc/<your_algorithm>/`
   - A brief description of the algorithm and configuration used
   - The version or commit hash of the algorithm

### Requirements

- Run each algorithm 5 times per sequence (VIO is nondeterministic)
- Report the median-ATE run
- Use SE(3) Umeyama alignment without scale correction
- Use default algorithm configurations as published by the authors

### Reporting Format

Each JSON file should contain the output of `sesr-bench full`, which includes
ATE, SESR statistics under all clearance profiles, CSE at multiple thresholds,
and critical clearance.

## Bug Reports and Feature Requests

Open an issue on GitHub. Include:
- Python version
- evo version
- Minimal reproduction steps

## Code Contributions

- Follow existing code style
- Add tests for new functionality
- Update the README if adding features
