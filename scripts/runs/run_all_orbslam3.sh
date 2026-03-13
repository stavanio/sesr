#!/bin/bash
cd ~/sesr-build/ORB_SLAM3
export DISPLAY=
TRAJ_DIR=~/sesr-build/trajectories/orbslam3
mkdir -p $TRAJ_DIR

SEQS=("MH_01_easy:MH01:machine_hall" "MH_02_easy:MH02:machine_hall" "MH_03_medium:MH03:machine_hall" "MH_05_difficult:MH05:machine_hall" "V1_01_easy:V101:vicon_room1" "V2_02_medium:V202:vicon_room2")

for entry in "${SEQS[@]}"; do
    IFS=: read SEQ TS ENV <<< "$entry"
    for RUN in 1 2 3 4 5; do
        echo "=== $SEQ run $RUN === $(date)"
        ./Examples/Stereo-Inertial/stereo_inertial_euroc \
            Vocabulary/ORBvoc.txt \
            Examples/Stereo-Inertial/EuRoC.yaml \
            ~/sesr-build/euroc/$ENV/$SEQ \
            Examples/Stereo-Inertial/EuRoC_TimeStamps/${TS}.txt \
            dataset-${TS}_run${RUN} 2>&1 | tail -3
        if [ -f "f_dataset-${TS}_run${RUN}.txt" ]; then
            cp "f_dataset-${TS}_run${RUN}.txt" "$TRAJ_DIR/${TS}_run${RUN}.txt"
            rm -f "f_dataset-${TS}_run${RUN}.txt" "kf_dataset-${TS}_run${RUN}.txt"
            echo "Saved: ${TS}_run${RUN}.txt"
        else
            echo "FAILED: ${TS} run ${RUN}"
        fi
    done
done
echo "=== ALL DONE === $(date)"
