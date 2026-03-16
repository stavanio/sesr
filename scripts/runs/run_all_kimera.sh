#!/bin/bash
mkdir -p ~/sesr-build/trajectories/kimera

SEQS="MH_01_easy:machine_hall:MH01 MH_02_easy:machine_hall:MH02 MH_03_medium:machine_hall:MH03 MH_05_difficult:machine_hall:MH05 V1_01_easy:vicon_room1:V101 V2_02_medium:vicon_room2:V202"

for entry in $SEQS; do
    SEQ=$(echo $entry | cut -d: -f1)
    ENV=$(echo $entry | cut -d: -f2)
    SHORT=$(echo $entry | cut -d: -f3)
    for RUN in 1 2 3 4 5; do
        echo "=== $SEQ run $RUN === $(date)"
        docker run --rm           -v /home/stavan/sesr-build/euroc:/data/euroc           -v /home/stavan/sesr-build/trajectories/kimera:/data/output           kimera_vio /bin/bash -c "
            cd /root/Kimera-VIO
            sed -i 's|/path/to/euroc/dataset|/data/euroc/${ENV}/${SEQ}|' scripts/stereoVIOEuroc.bash
            sed -i 's/LOG_OUTPUT=0/LOG_OUTPUT=1/' scripts/stereoVIOEuroc.bash
            sed -i 's/--visualize=true/--visualize=false/' params/Euroc/flags/stereoVIOEuroc.flags
            sed -i 's/--visualize_mesh=true/--visualize_mesh=false/' params/Euroc/flags/stereoVIOEuroc.flags
            sed -i 's/--visualize_point_cloud=true/--visualize_point_cloud=false/' params/Euroc/flags/stereoVIOEuroc.flags
            sed -i 's/--viz_type=0/--viz_type=2/' params/Euroc/flags/stereoVIOEuroc.flags
            sed -i 's/--visualize_frontend_images=1/--visualize_frontend_images=0/' scripts/stereoVIOEuroc.bash
            sed -i 's/--save_frontend_images=1/--save_frontend_images=0/' scripts/stereoVIOEuroc.bash
            ./scripts/stereoVIOEuroc.bash > /dev/null 2>&1
            if [ -f output_logs/traj_vio.csv ]; then
                cp output_logs/traj_vio.csv /data/output/${SHORT}_run${RUN}.csv
                echo SAVED
            else
                echo NOSAVE
            fi
          "
        if [ -f ~/sesr-build/trajectories/kimera/${SHORT}_run${RUN}.csv ]; then
            echo "Saved: ${SHORT}_run${RUN}.csv"
        else
            echo "FAILED: $SEQ run $RUN"
        fi
    done
done
echo "=== ALL DONE === $(date)"
