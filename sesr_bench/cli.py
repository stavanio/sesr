"""
SESR-Bench command-line interface.

Usage:
    sesr-bench evaluate --gt groundtruth.csv --est estimated.txt --format euroc --clearance uniform --c0 0.15
    sesr-bench full --gt groundtruth.csv --est estimated.txt --format euroc --output csv
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="SESR-Bench: Clearance-Aware VIO Evaluation",
        prog="sesr-bench",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # evaluate subcommand
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate single clearance profile")
    eval_parser.add_argument("--gt", required=True, help="Ground truth trajectory file")
    eval_parser.add_argument("--est", required=True, help="Estimated trajectory file")
    eval_parser.add_argument("--format", default="euroc", choices=["euroc", "tum", "kitti"])
    eval_parser.add_argument("--clearance", default="uniform",
                             choices=["uniform", "sinusoidal", "step", "error_correlated"])
    eval_parser.add_argument("--c0", type=float, default=0.15, help="Clearance for uniform profile (m)")

    # full subcommand
    full_parser = subparsers.add_parser("full", help="Run full SESR-Bench protocol")
    full_parser.add_argument("--gt", required=True, help="Ground truth trajectory file")
    full_parser.add_argument("--est", required=True, help="Estimated trajectory file")
    full_parser.add_argument("--format", default="euroc", choices=["euroc", "tum", "kitti"])
    full_parser.add_argument("--output", default="csv", choices=["csv", "json", "latex", "dict"])

    # c-star subcommand
    cstar_parser = subparsers.add_parser("c-star", help="Compute critical clearance only")
    cstar_parser.add_argument("--gt", required=True, help="Ground truth trajectory file")
    cstar_parser.add_argument("--est", required=True, help="Estimated trajectory file")
    cstar_parser.add_argument("--format", default="euroc", choices=["euroc", "tum", "kitti"])

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    from .evo_integration import evaluate_trajectory, full_evaluation

    if args.command == "evaluate":
        result = evaluate_trajectory(
            gt_file=args.gt,
            est_file=args.est,
            format=args.format,
            clearance_profile=args.clearance,
            c0=args.c0,
        )
        print(result)

    elif args.command == "full":
        output = full_evaluation(
            gt_file=args.gt,
            est_file=args.est,
            format=args.format,
            output=args.output,
        )
        print(output)

    elif args.command == "c-star":
        result = evaluate_trajectory(
            gt_file=args.gt,
            est_file=args.est,
            format=args.format,
            clearance_profile="uniform",
            c0=1.0,  # doesn't matter for c*
        )
        print(f"Critical clearance c* = {result.c_star * 100:.2f} cm")
        print(f"(Deploy only in environments with >= {result.c_star * 100:.1f} cm clearance)")


if __name__ == "__main__":
    main()
