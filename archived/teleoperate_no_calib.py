#!/usr/bin/env python3
"""
Teleoperation script for SO101 robots without calibration files.

This script assumes the robots have been set to their middle positions using set_middle_position.py
and uses raw encoder values (0-32767) directly without normalization.

The script automatically identifies which robot is the leader (5V) and which is the follower (12V)
based on their voltage readings.

Example usage:

```shell
# Default usage (auto-detects ports and identifies leader/follower by voltage):
python teleoperate_no_calib.py

# Specify ports manually:
python teleoperate_no_calib.py \
    --robot.port=/dev/tty.usbmodem58760431541 \
    --teleop.port=/dev/tty.usbmodem58760431551

# With cameras:
python teleoperate_no_calib.py \
    --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 1920, height: 1080, fps: 30}}"
```
"""

import logging
import platform
import time
from dataclasses import asdict, dataclass, field
from pprint import pformat

import draccus

from lerobot.common.robots import make_robot_from_config, so101_follower
from lerobot.common.teleoperators import make_teleoperator_from_config, so101_leader
from lerobot.common.utils.robot_utils import busy_wait
from lerobot.common.utils.utils import init_logging, move_cursor_up


def find_robot_ports():
    """Find USB serial ports that are likely to be robot/motor controllers."""
    try:
        from serial.tools import list_ports
    except ImportError:
        logging.error("pyserial not installed. Cannot auto-detect ports.")
        return []
    
    robot_ports = []
    
    if platform.system() == "Darwin":  # macOS
        for port in list_ports.comports():
            if "usbmodem" in port.device or "usbserial" in port.device:
                robot_ports.append(port.device)
    elif platform.system() == "Linux":
        for port in list_ports.comports():
            if "ttyUSB" in port.device or "ttyACM" in port.device:
                robot_ports.append(port.device)
    elif platform.system() == "Windows":
        for port in list_ports.comports():
            if "COM" in port.device:
                robot_ports.append(port.device)
    
    return robot_ports


def identify_robot_by_voltage(port):
    """
    Identify if a robot is leader (5V) or follower (12V) by reading voltage.
    
    Returns:
        tuple: (is_leader, voltage) where is_leader is True for 5V robots
    """
    try:
        # Create a temporary robot connection to read voltage
        config = so101_follower.SO101FollowerConfig(port=port)
        robot = make_robot_from_config(config)
        
        logging.info(f"Connecting to robot at {port} to read voltage...")
        robot.connect(calibrate=False)
        
        # Read voltage from any motor (they should all have the same voltage)
        motor_name = list(robot.bus.motors.keys())[0]
        raw_voltage = robot.bus.read("Present_Voltage", motor_name, normalize=False)
        
        # Feetech motors report voltage in units of 0.1V
        voltage = raw_voltage / 10.0
        
        robot.disconnect()
        
        # Determine if this is leader (5V) or follower (12V)
        # Allow some tolerance (4.5-5.5V for leader, 11-13V for follower)
        is_leader = 4.5 <= voltage <= 5.5
        
        logging.info(f"Port {port}: Voltage = {voltage:.1f}V -> {'LEADER' if is_leader else 'FOLLOWER'}")
        
        return is_leader, voltage
        
    except Exception as e:
        logging.error(f"Error reading voltage from {port}: {e}")
        raise


def auto_detect_and_identify_ports():
    """
    Automatically detect robot ports and identify leader vs follower by voltage.
    
    Returns:
        tuple: (leader_port, follower_port)
    """
    ports = find_robot_ports()
    
    if len(ports) == 0:
        raise RuntimeError(
            "No robot ports detected. Please ensure both robots are connected via USB."
        )
    elif len(ports) == 1:
        raise RuntimeError(
            "Only one robot port detected. Please ensure both leader and follower are connected."
        )
    elif len(ports) > 2:
        logging.warning(f"More than 2 ports detected: {ports}. Will test first 2 ports.")
        ports = ports[:2]
    
    logging.info(f"\nDetected ports: {ports}")
    logging.info("Identifying robots by voltage...")
    
    leader_port = None
    follower_port = None
    
    for port in ports:
        is_leader, voltage = identify_robot_by_voltage(port)
        
        if is_leader and leader_port is None:
            leader_port = port
        elif not is_leader and follower_port is None:
            follower_port = port
        else:
            # Multiple robots with same voltage type
            if is_leader:
                logging.warning(f"Multiple leader robots (5V) detected!")
            else:
                logging.warning(f"Multiple follower robots (12V) detected!")
    
    if not leader_port:
        raise RuntimeError("No leader robot (5V) detected!")
    if not follower_port:
        raise RuntimeError("No follower robot (12V) detected!")
    
    logging.info(f"\n✓ Successfully identified robots:")
    logging.info(f"  Leader (5V):   {leader_port}")
    logging.info(f"  Follower (12V): {follower_port}")
    
    return leader_port, follower_port


@dataclass
class TeleoperateNoCalibrConfig:
    # Default to SO101 robots with auto-detected ports
    teleop: so101_leader.SO101LeaderConfig = field(default_factory=lambda: so101_leader.SO101LeaderConfig(port=None))
    robot: so101_follower.SO101FollowerConfig = field(default_factory=lambda: so101_follower.SO101FollowerConfig(port=None))
    
    # Limit the maximum frames per second
    fps: int = 60
    teleop_time_s: float | None = None
    # Display debug info
    display_data: bool = True
    
    def __post_init__(self):
        # Auto-detect and identify ports if not specified
        if (not self.teleop.port or not self.robot.port):
            try:
                # Use voltage-based identification
                leader_port, follower_port = auto_detect_and_identify_ports()
                
                if not self.teleop.port:
                    self.teleop.port = leader_port
                if not self.robot.port:
                    self.robot.port = follower_port
                    
            except RuntimeError as e:
                logging.error(str(e))
                raise


def teleop_loop_no_calib(teleop, robot, fps, display_data=False, duration=None):
    """
    Teleoperation loop without calibration.
    
    This reads raw positions from the leader and sends them directly to the follower.
    All values are in the raw encoder range (0-32767).
    """
    # Get the motor bus instances
    teleop_bus = teleop.bus
    robot_bus = robot.bus
    
    # Verify both are connected
    if not teleop_bus.is_connected or not robot_bus.is_connected:
        raise RuntimeError("Both leader and follower must be connected")
    
    display_len = max(len(key) for key in robot.action_features)
    start = time.perf_counter()
    
    logging.info("\nStarting teleoperation without calibration...")
    logging.info("Using raw encoder values (0-32767) for all motors")
    logging.info("Press Ctrl+C to stop\n")
    
    while True:
        loop_start = time.perf_counter()
        
        # Read raw positions from leader (no normalization)
        leader_positions = teleop_bus.sync_read("Present_Position", normalize=False)
        
        # Prepare action dict with raw values
        action = {}
        for motor, raw_value in leader_positions.items():
            # Map motor names to action features (add .pos suffix)
            action_key = f"{motor}.pos"
            if action_key in robot.action_features:
                action[action_key] = raw_value
        
        # Send raw positions to follower (no normalization)
        robot_bus.sync_write("Goal_Position", leader_positions, normalize=False)
        
        if display_data:
            # Display the raw values
            print("\n" + "-" * (display_len + 20))
            print(f"{'MOTOR':<{display_len}} | {'RAW VALUE':>10} | {'%':>6}")
            print("-" * (display_len + 20))
            for motor, raw_value in leader_positions.items():
                # Calculate percentage of range (0-100%)
                percent = (raw_value / 32767) * 100
                print(f"{motor:<{display_len}} | {raw_value:>10} | {percent:>5.1f}%")
            
            dt_s = time.perf_counter() - loop_start
            busy_wait(1 / fps - dt_s)
            loop_s = time.perf_counter() - loop_start
            
            print(f"\nLoop time: {loop_s * 1e3:.2f}ms ({1 / loop_s:.0f} Hz)")
            
            if duration is not None and time.perf_counter() - start >= duration:
                return
            
            # Move cursor up to overwrite the display
            move_cursor_up(len(leader_positions) + 6)
        else:
            # Just maintain the loop rate
            dt_s = time.perf_counter() - loop_start
            busy_wait(1 / fps - dt_s)
            
            if duration is not None and time.perf_counter() - start >= duration:
                return


@draccus.wrap()
def teleoperate_no_calib(cfg: TeleoperateNoCalibrConfig):
    init_logging()
    logging.info("Teleoperation Configuration (No Calibration):")
    logging.info(pformat(asdict(cfg)))
    
    # Create robot and teleop instances
    teleop = make_teleoperator_from_config(cfg.teleop)
    robot = make_robot_from_config(cfg.robot)
    
    # Connect without calibration
    logging.info("\nConnecting to devices without calibration...")
    teleop.connect(calibrate=False)
    robot.connect(calibrate=False)
    
    try:
        # Run the teleoperation loop
        teleop_loop_no_calib(
            teleop, 
            robot, 
            cfg.fps, 
            display_data=cfg.display_data, 
            duration=cfg.teleop_time_s
        )
    except KeyboardInterrupt:
        logging.info("\nTeleoperation stopped by user")
    except Exception as e:
        logging.error(f"Error during teleoperation: {e}")
        raise
    finally:
        # Always disconnect properly
        logging.info("Disconnecting devices...")
        teleop.disconnect()
        robot.disconnect()
        logging.info("Teleoperation complete!")


if __name__ == "__main__":
    teleoperate_no_calib() 