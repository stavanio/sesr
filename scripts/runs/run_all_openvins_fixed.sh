#!/bin/bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
killall roscore rosmaster rosout 2>/dev/null
sleep 2
roscore &
sleep 3
cd ~/catkin_ws
mkdir -p ~/sesr-build/trajectories/openvins_fixed

BAGS="MH_01_easy:MH01 MH_02_easy:MH02 MH_03_medium:MH03 MH_05_difficult:MH05 V1_01_easy:V101 V2_02_medium:V202"

for entry in $BAGS; do
    BAG=$(echo $entry | cut -d: -f1)
    SHORT=$(echo $entry | cut -d: -f2)
    for RUN in 1 2 3 4 5; do
        echo "=== $BAG run $RUN === $(date)"
        rm -f /tmp/openvins_traj.txt
        python3 ~/sesr-build/odom_to_tum.py _topic:=/ros1_serial_msckf/odomimu _out:=/tmp/openvins_traj.txt &
        DUMP_PID=$!
        sleep 1
        rosrun ov_msckf ros1_serial_msckf src/open_vins/config/euroc_mav/estimator_config.yaml _path_bag:=/home/stavan/sesr-build/euroc/bags/${BAG}.bag > /dev/null 2>&1
        sleep 2
        kill $DUMP_PID 2>/dev/null
        wait $DUMP_PID 2>/dev/null
        sleep 1
        if [ -s /tmp/openvins_traj.txt ]; then
            cp /tmp/openvins_traj.txt ~/sesr-build/trajectories/openvins_fixed/${SHORT}_run${RUN}.txt
            NLINES=$(wc -l < /tmp/openvins_traj.txt)
            echo "Saved: ${SHORT}_run${RUN}.txt ($NLINES poses)"
        else
            echo "FAILED: $BAG run $RUN"
        fi
    done
done
killall roscore rosmaster 2>/dev/null
echo "=== ALL DONE === $(date)"
