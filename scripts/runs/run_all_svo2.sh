#!/bin/bash
source /opt/ros/noetic/setup.bash
source ~/svo_ws/devel/setup.bash
roscore &
sleep 3
mkdir -p ~/sesr-build/trajectories/svo2

BAGS="MH_01_easy:MH01 MH_02_easy:MH02 MH_03_medium:MH03 MH_05_difficult:MH05 V1_01_easy:V101 V2_02_medium:V202"

for entry in $BAGS; do
    BAG=$(echo $entry | cut -d: -f1)
    SHORT=$(echo $entry | cut -d: -f2)
    for RUN in 1 2 3 4 5; do
        echo "=== $BAG run $RUN === $(date)"
        rm -f /tmp/svo_traj.txt
        roslaunch ~/svo_ws/src/headless_launch/euroc_stereo_headless.launch &
        SVO_PID=$!
        sleep 5
        python3 ~/sesr-build/pose_to_tum.py _topic:=/svo/pose_imu _out:=/tmp/svo_traj.txt &
        DUMP_PID=$!
        sleep 1
        rosbag play /home/stavan/sesr-build/euroc/bags/${BAG}.bag > /dev/null 2>&1
        sleep 5
        kill $DUMP_PID 2>/dev/null
        kill $SVO_PID 2>/dev/null
        killall svo_node 2>/dev/null
        sleep 2
        if [ -s /tmp/svo_traj.txt ]; then
            cp /tmp/svo_traj.txt ~/sesr-build/trajectories/svo2/${SHORT}_run${RUN}.txt
            echo "Saved: ${SHORT}_run${RUN}.txt"
        else
            echo "FAILED: $BAG run $RUN"
        fi
    done
done
killall roscore rosmaster 2>/dev/null
echo "=== ALL DONE === $(date)"
