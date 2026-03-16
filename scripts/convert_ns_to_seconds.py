#!/usr/bin/env python3
"""
Convert TUM trajectory files with nanosecond timestamps to seconds.

Some VIO pipelines (ORB-SLAM3, certain OpenVINS configs) output timestamps
in nanoseconds. The evo evaluation toolkit expects seconds. This script
converts nanosecond timestamps to seconds for compatibility with evo_ape.

Usage:
    python3 convert_ns_to_seconds.py input.txt output.txt

    # Or convert all files in a directory:
    for f in data/trajectories/orbslam3/*.txt; do
        python3 convert_ns_to_seconds.py "$f" "${f%.txt}_sec.txt"
    done

    # Then verify with evo:
    evo_ape euroc data/groundtruth/MH01_gt.csv data/trajectories/orbslam3/MH01_run3_sec.txt -va --align
"""

import sys

def convert(inpath, outpath):
    with open(inpath) as fin, open(outpath, "w") as fout:
        for line in fin:
            line = line.strip()
            if not line or line.startswith("#"):
                fout.write(line + "\n")
                continue
            parts = line.split()
            if len(parts) < 8:
                fout.write(line + "\n")
                continue
            t = float(parts[0])
            if t > 1e15:
                t = t / 1e9
            parts[0] = f"{t:.9f}"
            fout.write(" ".join(parts) + "\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} input.txt output.txt")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
    print(f"Converted: {sys.argv[1]} -> {sys.argv[2]}")
