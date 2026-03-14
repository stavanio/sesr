#!/bin/bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roscore &
sleep 3
cd ~/catkin_ws
mkdir -p ~/sesr-build/trajectories/rovio

BAGS="MH_01_easy:MH01 MH_02_easy:MH02 MH_03_medium:MH03 MH_05_difficult:MH05 V1_01_easy:V101 V2_02_medium:V202"

for entry in $BAGS; do
    BAG=$(echo $entry | cut -d: -f1)
    SHORT=$(echo $entry | cut -d: -f2)
    for RUN in 1 2 3 4 5; do
        echo "=== $BAG run $RUN === $(date)"
        rosrun rovio rovio_node src/rovio/cfg/rovio.info _camera0_config:=src/rovio/cfg/euroc_cam0.yaml _camera1_config:=src/rovio/cfg/euroc_cam1.yaml &
        sleep 3
        python3 ~/sesr-build/odom_to_tum.py _topic:=/rovio/odometry _out:=/tmp/rovio_traj.txt &
        sleep 1
        rosbag play /home/stavan/sesr-build/euroc/bags/${BAG}.bag > /dev/null 2>&1
        sleep 5
        killall rovio_node 2>/dev/null
        kill %3 2>/dev/null
        sleep 2
        if [ -s /tmp/rovio_traj.txt ]; then
            cp /tmp/rovio_traj.txt ~/sesr-build/trajectories/rovio/${SHORT}_run${RUN}.txt
            rm -f /tmp/rovio_traj.txt
            echo "Saved: ${SHORT}_run${RUN}.txt"
        else
            echo "FAILED: $BAG run $RUN"
        fi
    done
done
killall roscore rosmaster 2>/dev/null
echo "=== ALL DONE === $(date)"
