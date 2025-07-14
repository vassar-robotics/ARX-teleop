#!/usr/bin/env python3
"""
Standalone teleoperation script for SO101 robots without calibration.

This script connects to two SO101 robots with Feetech STS3215 servos and performs teleoperation
without using calibration files. It uses raw encoder values (0-4095) directly.

The script automatically identifies which robot is the leader (5V) and which is the follower (12V)
based on their voltage readings.

Requirements:
- pyserial
- scservo_sdk (for Feetech motors)

Example usage:
```shell
# Auto-detect ports and identify leader/follower by voltage:
python teleoperate_no_calib_standalone.py

# Specify ports manually:
python teleoperate_no_calib_standalone.py --leader_port=/dev/ttyUSB0 --follower_port=/dev/ttyUSB1

# Custom motor IDs and settings:
python teleoperate_no_calib_standalone.py --motor_ids=1,2,3,4,5,6,7 --fps=30
```
"""

import argparse
import logging
import platform
import time
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def find_robot_ports() -> List[str]:
    """Find USB serial ports that are likely to be robot/motor controllers."""
    try:
        from serial.tools import list_ports
    except ImportError:
        logger.error("pyserial not installed. Please install with: pip install pyserial")
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


class SO101Controller:
    """Controller for SO101 robot with Feetech STS3215 motors."""
    
    # Feetech register addresses
    TORQUE_ENABLE = 40
    PRESENT_POSITION = 56
    GOAL_POSITION = 42
    PRESENT_VOLTAGE = 62
    LOCK = 55
    
    def __init__(self, port: str, motor_ids: List[int], baudrate: int = 1000000):
        self.port = port
        self.motor_ids = motor_ids
        self.baudrate = baudrate
        self.connected = False
        self.resolution = 4096  # STS3215 has 4096 resolution (0-4095)
        
        try:
            import scservo_sdk as scs  # type: ignore
            self.scs = scs
        except ImportError:
            raise RuntimeError("scservo_sdk not installed. Please install from Feetech SDK")
            
        self.port_handler: Any = None
        self.packet_handler: Any = None
        
    def connect(self) -> None:
        """Connect to the robot."""
        self.port_handler = self.scs.PortHandler(self.port)
        self.packet_handler = self.scs.PacketHandler(0)  # Protocol 0
        
        if not self.port_handler.openPort():
            raise RuntimeError(f"Failed to open port '{self.port}'")
            
        if not self.port_handler.setBaudRate(self.baudrate):
            raise RuntimeError(f"Failed to set baudrate to {self.baudrate}")
            
        # Test connection by pinging motors
        for motor_id in self.motor_ids:
            model_number, result, error = self.packet_handler.ping(self.port_handler, motor_id)
            if result != self.scs.COMM_SUCCESS:
                raise RuntimeError(f"Failed to ping motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")
                
        self.connected = True
        logger.info(f"Connected to SO101 robot at {self.port} with motors: {self.motor_ids}")
        
    def disconnect(self) -> None:
        """Disconnect from the robot."""
        if self.port_handler:
            self.port_handler.closePort()
        self.connected = False
        
    def read_voltage(self) -> float:
        """Read voltage from the first motor."""
        motor_id = self.motor_ids[0]
        raw_voltage, result, error = self.packet_handler.read1ByteTxRx(
            self.port_handler, motor_id, self.PRESENT_VOLTAGE)
        
        if result != self.scs.COMM_SUCCESS:
            raise RuntimeError(f"Failed to read voltage: {self.packet_handler.getTxRxResult(result)}")
            
        # Feetech motors report voltage in units of 0.1V
        return raw_voltage / 10.0
        
    def read_positions(self) -> Dict[int, int]:
        """Read current positions from all motors."""
        positions = {}
        for motor_id in self.motor_ids:
            position, result, error = self.packet_handler.read2ByteTxRx(
                self.port_handler, motor_id, self.PRESENT_POSITION)
            if result == self.scs.COMM_SUCCESS:
                positions[motor_id] = position
            else:
                logger.warning(f"Failed to read position from motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")
        return positions
        
    def write_positions(self, positions: Dict[int, int]) -> None:
        """Write goal positions to motors."""
        for motor_id, position in positions.items():
            # Clamp position to valid range
            position = max(0, min(self.resolution - 1, position))
            
            result, error = self.packet_handler.write2ByteTxRx(
                self.port_handler, motor_id, self.GOAL_POSITION, position)
            if result != self.scs.COMM_SUCCESS:
                logger.warning(f"Failed to write position to motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")
                
    def enable_torque(self) -> None:
        """Enable torque on all motors."""
        for motor_id in self.motor_ids:
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, motor_id, self.TORQUE_ENABLE, 1)
            if result != self.scs.COMM_SUCCESS:
                logger.warning(f"Failed to enable torque on motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")
                
            # Set Lock to 1 (locked)
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, motor_id, self.LOCK, 1)
            if result != self.scs.COMM_SUCCESS:
                logger.warning(f"Failed to set lock on motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")


def identify_robot_by_voltage(port: str, motor_ids: List[int]) -> tuple[bool, float]:
    """
    Identify if a robot is leader (5V) or follower (12V) by reading voltage.
    
    Returns:
        tuple: (is_leader, voltage) where is_leader is True for 5V robots
    """
    try:
        logger.info(f"Connecting to robot at {port} to read voltage...")
        robot = SO101Controller(port, motor_ids)
        robot.connect()
        
        voltage = robot.read_voltage()
        robot.disconnect()
        
        # Determine if this is leader (5V) or follower (12V)
        # Allow some tolerance (4.5-5.5V for leader, 11-13V for follower)
        is_leader = 4.5 <= voltage <= 5.5
        
        logger.info(f"Port {port}: Voltage = {voltage:.1f}V -> {'LEADER' if is_leader else 'FOLLOWER'}")
        
        return is_leader, voltage
        
    except Exception as e:
        logger.error(f"Error reading voltage from {port}: {e}")
        raise


def auto_detect_and_identify_ports(motor_ids: List[int]) -> tuple[str, str]:
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
        logger.warning(f"More than 2 ports detected: {ports}. Will test first 2 ports.")
        ports = ports[:2]
    
    logger.info(f"\nDetected ports: {ports}")
    logger.info("Identifying robots by voltage...")
    
    leader_port = None
    follower_port = None
    
    for port in ports:
        is_leader, voltage = identify_robot_by_voltage(port, motor_ids)
        
        if is_leader and leader_port is None:
            leader_port = port
        elif not is_leader and follower_port is None:
            follower_port = port
        else:
            # Multiple robots with same voltage type
            if is_leader:
                logger.warning(f"Multiple leader robots (5V) detected!")
            else:
                logger.warning(f"Multiple follower robots (12V) detected!")
    
    if not leader_port:
        raise RuntimeError("No leader robot (5V) detected!")
    if not follower_port:
        raise RuntimeError("No follower robot (12V) detected!")
    
    logger.info(f"\n✓ Successfully identified robots:")
    logger.info(f"  Leader (5V):   {leader_port}")
    logger.info(f"  Follower (12V): {follower_port}")
    
    return leader_port, follower_port


def move_cursor_up(lines: int) -> None:
    """Move terminal cursor up by specified number of lines."""
    print(f"\033[{lines}A", end="")


def busy_wait(duration: float) -> None:
    """Busy wait for the specified duration in seconds."""
    start_time = time.perf_counter()
    while time.perf_counter() - start_time < duration:
        pass


def teleoperation_loop(leader: SO101Controller, follower: SO101Controller, 
                      fps: int, display_data: bool = False, duration: Optional[float] = None) -> None:
    """
    Main teleoperation loop.
    
    Reads positions from leader and sends them to follower using raw encoder values.
    """
    # Verify both are connected
    if not leader.connected or not follower.connected:
        raise RuntimeError("Both leader and follower must be connected")
    
    # Enable torque on follower
    logger.info("Enabling torque on follower robot...")
    follower.enable_torque()
    
    start_time = time.perf_counter()
    
    logger.info("\nStarting teleoperation without calibration...")
    logger.info(f"Using raw encoder values (0-{leader.resolution-1}) for all motors")
    logger.info("Press Ctrl+C to stop\n")
    
    while True:
        loop_start = time.perf_counter()
        
        # Read raw positions from leader
        leader_positions = leader.read_positions()
        
        if not leader_positions:
            logger.warning("Failed to read any positions from leader")
            continue
            
        # Send positions directly to follower
        follower.write_positions(leader_positions)
        
        if display_data:
            # Display the raw values
            print("\n" + "-" * 50)
            print(f"{'MOTOR ID':<10} | {'RAW VALUE':>10} | {'%':>6}")
            print("-" * 50)
            for motor_id, raw_value in leader_positions.items():
                # Calculate percentage of range (0-100%)
                percent = (raw_value / (leader.resolution - 1)) * 100
                print(f"{motor_id:<10} | {raw_value:>10} | {percent:>5.1f}%")
            
            dt_s = time.perf_counter() - loop_start
            target_loop_time = 1 / fps
            if dt_s < target_loop_time:
                busy_wait(target_loop_time - dt_s)
            loop_s = time.perf_counter() - loop_start
            
            print(f"\nLoop time: {loop_s * 1000:.2f}ms ({1 / loop_s:.0f} Hz)")
            
            if duration is not None and time.perf_counter() - start_time >= duration:
                return
            
            # Move cursor up to overwrite the display
            move_cursor_up(len(leader_positions) + 6)
        else:
            # Just maintain the loop rate
            dt_s = time.perf_counter() - loop_start
            target_loop_time = 1 / fps
            if dt_s < target_loop_time:
                busy_wait(target_loop_time - dt_s)
            
            if duration is not None and time.perf_counter() - start_time >= duration:
                return


def main():
    parser = argparse.ArgumentParser(description="Standalone teleoperation for SO101 robots with STS3215 servos")
    parser.add_argument("--motor_ids", type=str, default="1,2,3,4,5,6,7",
                       help="Comma-separated list of motor IDs (default: 1,2,3,4,5,6,7)")
    parser.add_argument("--leader_port", type=str,
                       help="Serial port for leader robot (5V)")
    parser.add_argument("--follower_port", type=str,
                       help="Serial port for follower robot (12V)")
    parser.add_argument("--baudrate", type=int, default=1000000,
                       help="Baudrate (default: 1000000)")
    parser.add_argument("--fps", type=int, default=60,
                       help="Target frames per second (default: 60)")
    parser.add_argument("--duration", type=float,
                       help="Duration in seconds (default: infinite)")
    parser.add_argument("--no_display", action="store_true",
                       help="Disable real-time data display")
    
    args = parser.parse_args()
    
    # Parse motor IDs
    motor_ids = [int(id.strip()) for id in args.motor_ids.split(",")]
    
    # Determine ports
    if args.leader_port and args.follower_port:
        leader_port = args.leader_port
        follower_port = args.follower_port
        logger.info(f"Using specified ports:")
        logger.info(f"  Leader:   {leader_port}")
        logger.info(f"  Follower: {follower_port}")
    else:
        try:
            leader_port, follower_port = auto_detect_and_identify_ports(motor_ids)
        except RuntimeError as e:
            logger.error(str(e))
            return
    
    # Create robot controllers
    leader = SO101Controller(leader_port, motor_ids, args.baudrate)
    follower = SO101Controller(follower_port, motor_ids, args.baudrate)
    
    try:
        # Connect both robots
        logger.info("\nConnecting to robots...")
        leader.connect()
        follower.connect()
        
        # Run teleoperation
        teleoperation_loop(
            leader, 
            follower, 
            args.fps, 
            display_data=not args.no_display,
            duration=args.duration
        )
        
    except KeyboardInterrupt:
        logger.info("\nTeleoperation stopped by user")
    except Exception as e:
        logger.error(f"Error during teleoperation: {e}")
        raise
    finally:
        # Always disconnect properly
        logger.info("Disconnecting robots...")
        try:
            leader.disconnect()
        except:
            pass
        try:
            follower.disconnect()
        except:
            pass
        logger.info("Teleoperation complete!")


if __name__ == "__main__":
    main() 