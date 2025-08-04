ARX Control Module README
==========================

This module provides a minimal, streamlined interface for controlling ARX R5 robot arms.

## Contents

- single_arm.py: Main SingleArm class for robot control
- __init__.py: Module initialization and library loading
- setup_env.sh: Environment setup script for library paths
- X5liteaa0.urdf: Robot description for X5lite arm (type=0)
- R5_master.urdf: Robot description for R5 arm (type=1)

## Key Features

- Clean SingleArm class wrapping the C++ ARX library
- Quaternion ↔ Euler angle conversion utilities
- End-effector pose control (position + orientation)
- Joint position control
- Gripper control
- Gravity compensation and home positioning
- Real-time arm state monitoring

## Usage

1. Set up environment:
   ```bash
   source arx_control/setup_env.sh
   ```

2. Initialize the arm:
   ```python
   from arx_control import SingleArm
   
   config = {
       "can_port": "can0",  # Your CAN interface
       "type": 1,           # 1 for R5, 0 for X5lite
   }
   
   arm = SingleArm(config)
   ```

3. Control the arm:
   ```python
   # Go to home position
   arm.go_home()
   
   # Enable gravity compensation
   arm.gravity_compensation()
   
   # Move end effector (x, y, z, roll, pitch, yaw)
   pose = [0.3, 0.0, 0.2, 0.0, 0.0, 0.0]
   arm.set_ee_pose_xyzrpy(pose)
   
   # Control gripper (-1.0 = closed, 1.0 = open)
   arm.set_catch_pos(0.5)
   
   # Get current state
   ee_pose = arm.get_ee_pose_xyzrpy()
   joint_pos = arm.get_joint_positions()
   ```

## Dependencies

- The compiled ARX R5 libraries (from arx_local_control_example)
- numpy for array operations
- Properly configured CAN interface

## Configuration Options

- can_port: CAN interface name (e.g., "can0", "can1")
- type: Robot type (0 for X5lite, 1 for R5)
- num_joints: Number of joints (default: 7)
- dt: Control time step (default: 0.05)

## Error Handling

The module includes error handling for:
- Missing library dependencies
- CAN communication failures
- Invalid poses or movements
- Gripper position limits

## Notes

- This module depends on the compiled libraries in arx_local_control_example/
- Make sure to run setup_env.sh before using the module
- The arm must be physically connected and the CAN interface configured
- Use gravity compensation mode for manual manipulation