#!/usr/bin/env python3
"""
ARX R5 Keyboard Control Script

Controls an ARX R5 robot arm using keyboard input.
Use this script to manually control the arm for testing and teleoperation setup.

Requirements:
- ARX R5 arm connected via CAN adapter
- CAN interface configured (e.g., can0)
- ARX libraries built and accessible

Usage:
    python test_arx_via_keyboard.py
"""

from arx_control import ARXArm
from typing import Dict, Any
import numpy as np
import curses
import time


def keyboard_control(stdscr):
    """
    Main keyboard control loop using curses.
    
    Controls:
    - w/s: Move forward/backward (X axis)
    - a/d: Move left/right (Y axis) 
    - ↑/↓ arrows: Move up/down (Z axis)
    - ←/→ arrows: Also move left/right (Y axis)
    - m/n: Rotate roll
    - l/.: Rotate pitch
    - ,//: Rotate yaw
    - c: Close gripper
    - o: Open gripper
    - i: Enable gravity compensation mode
    - r: Return to home position
    - q: Quit program
    """
    
    # Configure curses
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(1)   # Non-blocking mode
    stdscr.timeout(10)  # Keyboard read timeout
    curses.mousemask(0)  # Disable mouse events
    
    # Initialize control variables
    xyzrpy = np.zeros(6)  # End effector pose [x, y, z, roll, pitch, yaw]
    gripper = 0.0  # Gripper position
    
    # Movement increments
    linear_step = 0.005   # 5mm steps for position
    angular_step = 0.02   # ~1.1 degree steps for rotation
    gripper_step = 0.2    # Gripper step size
    
    print("Starting ARX R5 keyboard control...")
    print("Use 'q' to quit, 'i' for gravity compensation, 'r' to go home")
    
    while True:
        key = stdscr.getch()  # Get keyboard input
        stdscr.clear()
        
        # Get current arm state for display
        try:
            ee_pose = arm.get_ee_pose_xyzrpy()
            joint_pos = arm.get_joint_positions()
            joint_vel = arm.get_joint_velocities()
            joint_curr = arm.get_joint_currents()
            
            # Display current state
            stdscr.addstr(0, 0, f"EE_POSE: [{' '.join([f'{val:.3f}' for val in ee_pose])}]")
            stdscr.addstr(2, 0, f"JOINT_POS: [{' '.join([f'{val:.3f}' for val in joint_pos])}]")
            stdscr.addstr(4, 0, f"JOINT_VEL: [{' '.join([f'{val:.3f}' for val in joint_vel])}]")
            stdscr.addstr(6, 0, f"JOINT_CURR: [{' '.join([f'{val:.3f}' for val in joint_curr])}]")
            stdscr.addstr(8, 0, f"CURRENT TARGET: [{' '.join([f'{val:.3f}' for val in xyzrpy])}]")
            stdscr.addstr(10, 0, f"GRIPPER: {gripper:.2f}")
            
            # Controls help
            stdscr.addstr(12, 0, "Controls: w/s=X, a/d=Y, ↑↓=Z, m/n=roll, l/.=pitch, ,/=yaw, c/o=gripper, i=gravity, r=home, q=quit")
            
        except Exception as e:
            stdscr.addstr(0, 0, f"Error reading arm state: {e}")
        
        # Handle keyboard input
        if key == ord('q'):  # Quit
            break
        elif key == -1:  # No key pressed
            pass
        elif key == ord('i'):  # Gravity compensation
            try:
                arm.gravity_compensation()
                xyzrpy = arm.get_ee_pose_xyzrpy()  # Update current pose
                stdscr.addstr(14, 0, "Gravity compensation enabled")
            except Exception as e:
                stdscr.addstr(14, 0, f"Error enabling gravity compensation: {e}")
                
        elif key == ord('r'):  # Go home
            try:
                xyzrpy = np.zeros(6)
                arm.go_home()
                stdscr.addstr(14, 0, "Going to home position")
            except Exception as e:
                stdscr.addstr(14, 0, f"Error going home: {e}")
                
        # Linear movement
        elif key == ord('w'):  # Forward
            xyzrpy[0] += linear_step
            try:
                arm.set_ee_pose_xyzrpy(xyzrpy=xyzrpy)
            except Exception as e:
                stdscr.addstr(14, 0, f"Movement error: {e}")
                xyzrpy[0] -= linear_step  # Revert
                
        elif key == ord('s'):  # Backward
            xyzrpy[0] -= linear_step
            try:
                arm.set_ee_pose_xyzrpy(xyzrpy=xyzrpy)
            except Exception as e:
                stdscr.addstr(14, 0, f"Movement error: {e}")
                xyzrpy[0] += linear_step  # Revert
                
        elif key == ord('a'):  # Left
            xyzrpy[1] += linear_step
            try:
                arm.set_ee_pose_xyzrpy(xyzrpy=xyzrpy)
            except Exception as e:
                stdscr.addstr(14, 0, f"Movement error: {e}")
                xyzrpy[1] -= linear_step  # Revert
                
        elif key == ord('d'):  # Right
            xyzrpy[1] -= linear_step
            try:
                arm.set_ee_pose_xyzrpy(xyzrpy=xyzrpy)
            except Exception as e:
                stdscr.addstr(14, 0, f"Movement error: {e}")
                xyzrpy[1] += linear_step  # Revert
                
        elif key == curses.KEY_UP:  # Up
            xyzrpy[2] += linear_step
            try:
                arm.set_ee_pose_xyzrpy(xyzrpy=xyzrpy)
            except Exception as e:
                stdscr.addstr(14, 0, f"Movement error: {e}")
                xyzrpy[2] -= linear_step  # Revert
                
        elif key == curses.KEY_DOWN:  # Down
            xyzrpy[2] -= linear_step
            try:
                arm.set_ee_pose_xyzrpy(xyzrpy=xyzrpy)
            except Exception as e:
                stdscr.addstr(14, 0, f"Movement error: {e}")
                xyzrpy[2] += linear_step  # Revert
                
        elif key == curses.KEY_LEFT:  # Also left
            xyzrpy[1] += linear_step
            try:
                arm.set_ee_pose_xyzrpy(xyzrpy=xyzrpy)
            except Exception as e:
                stdscr.addstr(14, 0, f"Movement error: {e}")
                xyzrpy[1] -= linear_step  # Revert
                
        elif key == curses.KEY_RIGHT:  # Also right
            xyzrpy[1] -= linear_step
            try:
                arm.set_ee_pose_xyzrpy(xyzrpy=xyzrpy)
            except Exception as e:
                stdscr.addstr(14, 0, f"Movement error: {e}")
                xyzrpy[1] += linear_step  # Revert
                
        # Rotational movement
        elif key == ord(','):  # Yaw positive
            xyzrpy[5] += angular_step
            try:
                arm.set_ee_pose_xyzrpy(xyzrpy=xyzrpy)
            except Exception as e:
                stdscr.addstr(14, 0, f"Rotation error: {e}")
                xyzrpy[5] -= angular_step  # Revert
                
        elif key == ord('/'):  # Yaw negative
            xyzrpy[5] -= angular_step
            try:
                arm.set_ee_pose_xyzrpy(xyzrpy=xyzrpy)
            except Exception as e:
                stdscr.addstr(14, 0, f"Rotation error: {e}")
                xyzrpy[5] += angular_step  # Revert
                
        elif key == ord('m'):  # Roll positive
            xyzrpy[3] += angular_step
            try:
                arm.set_ee_pose_xyzrpy(xyzrpy=xyzrpy)
            except Exception as e:
                stdscr.addstr(14, 0, f"Rotation error: {e}")
                xyzrpy[3] -= angular_step  # Revert
                
        elif key == ord('n'):  # Roll negative
            xyzrpy[3] -= angular_step
            try:
                arm.set_ee_pose_xyzrpy(xyzrpy=xyzrpy)
            except Exception as e:
                stdscr.addstr(14, 0, f"Rotation error: {e}")
                xyzrpy[3] += angular_step  # Revert
                
        elif key == ord('l'):  # Pitch positive
            xyzrpy[4] += angular_step
            try:
                arm.set_ee_pose_xyzrpy(xyzrpy=xyzrpy)
            except Exception as e:
                stdscr.addstr(14, 0, f"Rotation error: {e}")
                xyzrpy[4] -= angular_step  # Revert
                
        elif key == ord('.'):  # Pitch negative
            xyzrpy[4] -= angular_step
            try:
                arm.set_ee_pose_xyzrpy(xyzrpy=xyzrpy)
            except Exception as e:
                stdscr.addstr(14, 0, f"Rotation error: {e}")
                xyzrpy[4] += angular_step  # Revert
                
        # Gripper control
        elif key == ord('c'):  # Close gripper
            gripper -= gripper_step
            gripper = max(gripper, -1.0)  # Clamp to valid range
            try:
                arm.set_catch_pos(pos=gripper)
            except Exception as e:
                stdscr.addstr(14, 0, f"Gripper error: {e}")
                
        elif key == ord('o'):  # Open gripper
            gripper += gripper_step
            gripper = min(gripper, 1.0)  # Clamp to valid range
            try:
                arm.set_catch_pos(pos=gripper)
            except Exception as e:
                stdscr.addstr(14, 0, f"Gripper error: {e}")
        
        stdscr.refresh()


def main():
    """Main function - initializes arm and starts keyboard control"""
    
    # ARM CONFIGURATION
    arm_config: Dict[str, Any] = {
        "can_port": "can0",  # CAN interface port
        "type": 1,           # 1 for R5 robot, 0 for X5lite
    }
    
    try:
        # Initialize the arm
        global arm
        arm = ARXArm(arm_config)
        print("ARX R5 arm initialized successfully!")
        
        # Start keyboard control interface
        curses.wrapper(keyboard_control)
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure to:")
        print("1. Run ./run_keyboard_control.sh which sets up the environment")
        print("2. Or manually set: export LD_LIBRARY_PATH=/home/vassar/code/ARX-teleop/arx_control/lib/arx_r5_src:$LD_LIBRARY_PATH")
        print("3. Set up the CAN interface")
        
    except Exception as e:
        print(f"Error initializing arm: {e}")
        print("Make sure:")
        print("1. ARX R5 arm is connected and powered on")
        print("2. CAN interface is properly configured")
        print("3. You have necessary permissions for CAN access")


if __name__ == "__main__":
    main()
