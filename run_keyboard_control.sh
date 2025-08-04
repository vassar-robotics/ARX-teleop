#!/bin/bash
# ARX R5 Keyboard Control Launcher Script
# This script sets up the environment and launches the keyboard control

echo "Setting up ARX R5 environment..."

# Check if libraries exist
if [ ! -f "arx_control/lib/arx_r5_src/libarx_r5_src.so" ]; then
    echo "ERROR: ARX libraries not found!"
    echo "Please run: cd arx_control && ./setup_libraries.sh"
    echo "See arx_control/README_LIBRARIES.md for more information."
    exit 1
fi

# Set library paths for reorganized structure
export LD_LIBRARY_PATH=/home/vassar/code/ARX-teleop/arx_control/lib/arx_r5_src:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/home/vassar/code/ARX-teleop/arx_control/lib:$LD_LIBRARY_PATH

# Set Python path
export PYTHONPATH=/home/vassar/code/ARX-teleop/arx_control/lib/arx_r5_python:$PYTHONPATH
export PYTHONPATH=/home/vassar/code/ARX-teleop:$PYTHONPATH

echo "Environment ready!"
echo ""
echo "ARX R5 Keyboard Control"
echo "======================"
echo "Controls:"
echo "  Movement: w/s (forward/back), a/d (left/right), arrows (up/down, left/right)"
echo "  Rotation: m/n (roll), l/. (pitch), ,// (yaw)"
echo "  Gripper:  c (close), o (open)"
echo "  Other:    i (gravity compensation), r (home), q (quit)"
echo ""
echo "Starting keyboard control..."

# Run the keyboard control
python3 test_arx_via_keyboard.py