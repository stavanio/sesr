#!/bin/bash
cd ~/sesr-build/basalt
export DISPLAY=
TRAJ_DIR=~/sesr-build/trajectories/basalt
mkdir -p $TRAJ_DIR

SEQS=("MH_01_easy:machine_hall" "MH_02_easy:machine_hall" "MH_03_medium:machine_hall" "MH_05_difficult:machine_hall" "V1_01_easy:vicon_room1" "V2_02_medium:vicon_room2")

for entry in "${SEQS[@]}"; do
    IFS=: read SEQ ENV <<< "$entry"
    SHORT=$(echo $SEQ | sed 's/_easy//;s/_medium//;s/_difficult//' | sed 's/_0//')
    for RUN in 1 2 3 4 5; do
        echo "=== $SEQ run $RUN === $(date)"
        timeout 600 ./build/basalt_vio \
            --dataset-path ~/sesr-build/euroc/$ENV/$SEQ \
            --dataset-type euroc \
            --config-path data/euroc_config.json \
            --cam-calib data/euroc_ds_calib.json \
            --show-gui 0 \
            --save-trajectory tum 2>&1 | tail -3
        if [ -f "trajectory.txt" ]; then
            cp trajectory.txt "$TRAJ_DIR/${SHORT}_run${RUN}.txt"
            rm -f trajectory.txt
            echo "Saved: ${SHORT}_run${RUN}.txt"
        else
            echo "FAILED: $SEQ run $RUN"
        fi
    done
done
echo "=== ALL DONE === $(date)"
