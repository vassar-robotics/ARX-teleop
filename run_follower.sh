#!/bin/bash
# ARX Follower Launcher - Sets up environment and runs follower script

echo "Resetting CAN interfaces..."

# # Reset can0 for drivetrain
# sudo ip link set can0 down
# sudo ip link set can0 up type can bitrate 1000000
# sudo ip link set can0 txqueuelen 300

# Set can1 as left arm
# sudo ip link set can1 down
# sudo slcand -o -f -s8 /dev/arm-l can1
# sudo ip link set can1 up


# # Set can2 as right arm
# sudo ip link set can2 down
# sudo slcand -o -f -s8 /dev/arm-r can2
# sudo ip link set can2 up


echo "CAN interfaces reset complete."

# Set library paths
export LD_LIBRARY_PATH=/home/vassar/ARX-teleop/arx_control/lib/arx_r5_src:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/home/vassar/ARX-teleop/arx_control/lib:$LD_LIBRARY_PATH

# Set Python path
export PYTHONPATH=/home/vassar/ARX-teleop/arx_control/lib/arx_r5_python:$PYTHONPATH
export PYTHONPATH=/home/vassar/ARX-teleop:$PYTHONPATH

sudo fuser -k 5000/tcp

# Run the follower script with calibration file
# Use LD_PRELOAD to avoid library conflicts (same as run_dt_control.sh)
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 python3 teleop_single_arx_follower.py --calibration_file arx_leader_calibration.json "$@"