#!/usr/bin/env python3
"""
Helper script to identify which SO101 robot is connected to which port.

This script will move one robot at a time to help you identify which physical
robot corresponds to which USB port.
"""

import time
import logging
from serial.tools import list_ports

from lerobot.common.robots import make_robot_from_config, so101_follower
from lerobot.common.utils.utils import init_logging


def find_robot_ports():
    """Find USB serial ports that are likely to be robot/motor controllers."""
    robot_ports = []
    for port in list_ports.comports():
        if "usbmodem" in port.device or "usbserial" in port.device or "ttyUSB" in port.device or "ttyACM" in port.device:
            robot_ports.append(port.device)
    return robot_ports


def test_robot_port(port):
    """Test a single robot port by making it move slightly."""
    print(f"\n{'='*60}")
    print(f"Testing port: {port}")
    print(f"{'='*60}")
    
    try:
        # Create robot config
        config = so101_follower.SO101FollowerConfig(port=port)
        robot = make_robot_from_config(config)
        
        # Connect without calibration
        print("Connecting to robot...")
        robot.connect(calibrate=False)
        
        # Get the motor bus
        bus = robot.bus
        
        # Read current positions
        print("Reading current positions...")
        current_positions = bus.sync_read("Present_Position", normalize=False)
        
        print("\nThis robot will now move slightly.")
        print("Watch which physical robot moves!")
        input("Press ENTER when ready...")
        
        # Move each motor slightly (just 500 encoder steps)
        test_positions = {}
        for motor, pos in current_positions.items():
            if motor != "gripper":  # Don't move gripper for safety
                test_positions[motor] = pos + 500  # Move 500 steps forward
            else:
                test_positions[motor] = pos
        
        print("Moving robot...")
        bus.sync_write("Goal_Position", test_positions, normalize=False)
        time.sleep(2)  # Wait for movement
        
        # Move back to original position
        print("Moving back to original position...")
        bus.sync_write("Goal_Position", current_positions, normalize=False)
        time.sleep(2)
        
        # Disconnect
        robot.disconnect()
        
        # Ask user which robot moved
        print("\nWhich robot moved?")
        print("1. The LEFT robot")
        print("2. The RIGHT robot")
        print("3. The robot I want to use as LEADER (moves by hand)")
        print("4. The robot I want to use as FOLLOWER (copies movements)")
        print("5. I'm not sure / didn't see movement")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        return True, choice
        
    except Exception as e:
        print(f"Error testing port {port}: {e}")
        return False, None


def main():
    init_logging()
    
    print("SO101 Robot Identification Tool")
    print("="*60)
    print("This tool will help you identify which USB port corresponds")
    print("to which physical robot (leader vs follower).")
    print("="*60)
    
    # Find available ports
    ports = find_robot_ports()
    
    if len(ports) == 0:
        print("\nNo robot ports detected!")
        print("Please ensure your robots are connected via USB.")
        return
    elif len(ports) == 1:
        print(f"\nOnly one robot port detected: {ports[0]}")
        print("Please connect both robots for teleoperation.")
        return
    elif len(ports) > 2:
        print(f"\nMultiple ports detected: {ports}")
        print("Please ensure only the two SO101 robots are connected.")
        
    print(f"\nFound ports: {ports}")
    
    # Test each port
    port_info = {}
    for i, port in enumerate(ports[:2]):  # Test first two ports
        success, choice = test_robot_port(port)
        if success:
            port_info[port] = choice
    
    # Show summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    leader_port = None
    follower_port = None
    
    for port, choice in port_info.items():
        if choice == "3":
            leader_port = port
            print(f"Leader (hand-controlled): {port}")
        elif choice == "4":
            follower_port = port
            print(f"Follower (copies movements): {port}")
    
    # Generate the teleoperation command
    if leader_port and follower_port:
        print("\n" + "="*60)
        print("To run teleoperation with these robots, use:")
        print("="*60)
        print(f"python teleoperate_no_calib.py \\")
        print(f"    --teleop.port={leader_port} \\")
        print(f"    --robot.port={follower_port}")
    else:
        print("\nPlease run this script again and identify which robot should be")
        print("the leader (hand-controlled) and which should be the follower.")
    
    # Also save to a file for convenience
    if leader_port and follower_port:
        with open("robot_ports.txt", "w") as f:
            f.write(f"LEADER_PORT={leader_port}\n")
            f.write(f"FOLLOWER_PORT={follower_port}\n")
        print(f"\nPort assignments also saved to robot_ports.txt")


if __name__ == "__main__":
    main() 