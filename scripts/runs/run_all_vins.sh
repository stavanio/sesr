#!/bin/bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roscore &
sleep 3
cd ~/catkin_ws
TRAJ_DIR=~/sesr-build/trajectories/vins_mono
VINS_OUT=/home/stavan/sesr-build/vins_output
mkdir -p $TRAJ_DIR $VINS_OUT

BAGS=("MH_01_easy:MH01" "MH_02_easy:MH02" "MH_03_medium:MH03" "MH_05_difficult:MH05" "V1_01_easy:V101" "V2_02_medium:V202")

for entry in "${BAGS[@]}"; do
    IFS=: read BAG SHORT <<< "$entry"
    for RUN in 1 2 3 4 5; do
        echo "=== $BAG run $RUN === $(date)"
        rm -f $VINS_OUT/vio.csv
        rosrun vins vins_node \
            src/VINS-Fusion/config/euroc/euroc_stereo_imu_config.yaml \
            > /dev/null 2>&1 &
        VINS_PID=$!
        sleep 2
        rosbag play /home/stavan/sesr-build/euroc/bags/${BAG}.bag \
            --clock -r 1.0 > /dev/null 2>&1
        sleep 5
        kill $VINS_PID 2>/dev/null
        sleep 2
        if [ -f "$VINS_OUT/vio.csv" ]; then
            cp "$VINS_OUT/vio.csv" "$TRAJ_DIR/${SHORT}_run${RUN}.txt"
            echo "Saved: ${SHORT}_run${RUN}.txt"
        else
            echo "FAILED: $BAG run $RUN"
        fi
    done
done
kill %1 2>/dev/null
echo "=== ALL DONE === $(date)"
