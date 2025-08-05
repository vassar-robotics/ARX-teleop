#!/bin/bash
# Combined script to reset CAN interface and run tank drive control
# This combines functionality from chassis_control_example/reset_dt_can.sh and run_tank_drive.sh

echo "Resetting CAN interface..."

# Reset CAN interface
sudo ip link set can0 down

# Bring CAN interface back up with proper configuration
sudo ip link set can0 up type can bitrate 1000000

echo "CAN interface reset complete."
echo "Starting tank drive control..."

# Use system libraries to avoid conda conflicts
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 python tank_drive_canopen.py "$@"