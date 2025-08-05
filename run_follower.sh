#!/bin/bash
# ARX Follower Launcher - Sets up environment and runs follower script

# Set library paths
export LD_LIBRARY_PATH=/home/vassar/code/ARX-teleop/arx_control/lib/arx_r5_src:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/home/vassar/code/ARX-teleop/arx_control/lib:$LD_LIBRARY_PATH

# Set Python path
export PYTHONPATH=/home/vassar/code/ARX-teleop/arx_control/lib/arx_r5_python:$PYTHONPATH
export PYTHONPATH=/home/vassar/code/ARX-teleop:$PYTHONPATH

# Run the follower script with calibration file
python3 teleop_single_arx_follower.py --calibration_file arx_leader_calibration.json "$@"