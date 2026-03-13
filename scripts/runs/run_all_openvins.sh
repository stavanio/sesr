#!/bin/bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roscore &
sleep 3
cd ~/catkin_ws
TRAJ_DIR=~/sesr-build/trajectories/openvins
mkdir -p $TRAJ_DIR

BAGS=("MH_01_easy:MH01" "MH_02_easy:MH02" "MH_03_medium:MH03" "MH_05_difficult:MH05" "V1_01_easy:V101" "V2_02_medium:V202")

for entry in "${BAGS[@]}"; do
    IFS=: read BAG SHORT <<< "$entry"
    for RUN in 1 2 3 4 5; do
        echo "=== $BAG run $RUN === $(date)"
        timeout 120 rosrun ov_msckf ros1_serial_msckf \
            src/open_vins/config/euroc_mav/estimator_config.yaml \
            _path_bag:=/home/stavan/sesr-build/euroc/bags/${BAG}.bag \
            > /tmp/ov_fulllog.txt 2>&1
        
        grep "q_GtoI" /tmp/ov_fulllog.txt > /tmp/openvins_raw.txt
        
        python3 -c "
import re
with open('/tmp/openvins_raw.txt') as f:
    lines = f.readlines()
dt = 0.05
with open('/tmp/openvins_traj.txt', 'w') as out:
    for i, line in enumerate(lines):
        m = re.search(r'q_GtoI = ([\-\d.]+),([\-\d.]+),([\-\d.]+),([\-\d.]+) \| p_IinG = ([\-\d.]+),([\-\d.]+),([\-\d.]+)', line)
        if m:
            qw,qx,qy,qz = m.group(1),m.group(2),m.group(3),m.group(4)
            tx,ty,tz = m.group(5),m.group(6),m.group(7)
            out.write(f'{i*dt:.6f} {tx} {ty} {tz} {qx} {qy} {qz} {qw}\n')
print(f'Extracted {sum(1 for _ in open(\"/tmp/openvins_traj.txt\"))} poses')
"
        if [ -s /tmp/openvins_traj.txt ]; then
            cp /tmp/openvins_traj.txt "$TRAJ_DIR/${SHORT}_run${RUN}.txt"
            echo "Saved: ${SHORT}_run${RUN}.txt"
        else
            echo "FAILED: $BAG run $RUN"
        fi
    done
done
kill %1 2>/dev/null
echo "=== ALL DONE === $(date)"
