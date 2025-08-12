# Set library paths
export LD_LIBRARY_PATH=/home/vassar/code/ARX-teleop/arx_control/lib/arx_r5_src:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/home/vassar/code/ARX-teleop/arx_control/lib:$LD_LIBRARY_PATH

# Set Python path
export PYTHONPATH=/home/vassar/code/ARX-teleop/arx_control/lib/arx_r5_python:$PYTHONPATH
export PYTHONPATH=/home/vassar/code/ARX-teleop:$PYTHONPATH

sudo fuser -k 5000/tcp

# Run the follower script with calibration file
# Use LD_PRELOAD to avoid library conflicts (same as run_dt_control.sh)
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 python3 i2rt/test_via_pos.py