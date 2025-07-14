#!/usr/bin/env python3
"""
Standalone teleoperation script for multiple SO101 robots without calibration.

This script connects to two leader robots (5V) and two follower robots (12V) with 
Feetech STS3215 servos and performs teleoperation without using calibration files.
It uses raw encoder values (0-4095) directly.

The script automatically identifies which robots are leaders vs followers by reading 
their voltage, then creates an initial random mapping. Press 's' to switch the mapping.

Requirements:
- pyserial
- scservo_sdk (for Feetech motors)

Example usage:
```shell
# Auto-detect all 4 robots and start teleoperation:
python teleoperate_multi_arms_standalone.py

# Custom motor IDs and settings:
python teleoperate_multi_arms_standalone.py --motor_ids=1,2,3,4 --fps=30
```
"""

import argparse
import logging
import platform
import random
import sys
import threading
import time
from typing import Dict, List, Any, Optional

# Import select for Unix systems
try:
    import select
except ImportError:
    # Windows doesn't have select for stdin
    select = None

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
    
    def __init__(self, port: str, motor_ids: List[int], baudrate: int = 1000000, robot_id: str = ""):
        self.port = port
        self.motor_ids = motor_ids
        self.baudrate = baudrate
        self.robot_id = robot_id  # For identification (e.g., "Leader1", "Follower1")
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
        logger.info(f"Connected to {self.robot_id} at {self.port}")
        
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
                logger.warning(f"Failed to read position from motor {motor_id} on {self.robot_id}")
        return positions
        
    def write_positions(self, positions: Dict[int, int]) -> None:
        """Write goal positions to motors."""
        for motor_id, position in positions.items():
            # Clamp position to valid range
            position = max(0, min(self.resolution - 1, position))
            
            result, error = self.packet_handler.write2ByteTxRx(
                self.port_handler, motor_id, self.GOAL_POSITION, position)
            if result != self.scs.COMM_SUCCESS:
                logger.warning(f"Failed to write position to motor {motor_id} on {self.robot_id}")
                
    def enable_torque(self) -> None:
        """Enable torque on all motors."""
        for motor_id in self.motor_ids:
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, motor_id, self.TORQUE_ENABLE, 1)
            if result != self.scs.COMM_SUCCESS:
                logger.warning(f"Failed to enable torque on motor {motor_id} on {self.robot_id}")
                
            # Set Lock to 1 (locked)
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, motor_id, self.LOCK, 1)
            if result != self.scs.COMM_SUCCESS:
                logger.warning(f"Failed to set lock on motor {motor_id} on {self.robot_id}")


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


def auto_detect_and_identify_ports(motor_ids: List[int]) -> tuple[List[str], List[str]]:
    """
    Automatically detect robot ports and identify leaders vs followers by voltage.
    
    Returns:
        tuple: (leader_ports, follower_ports)
    """
    ports = find_robot_ports()
    
    if len(ports) < 4:
        raise RuntimeError(
            f"Found {len(ports)} ports, but need 4 robots (2 leaders + 2 followers). "
            "Please ensure all robots are connected via USB."
        )
    elif len(ports) > 4:
        logger.warning(f"More than 4 ports detected: {ports}. Will test first 4 ports.")
        ports = ports[:4]
    
    logger.info(f"\nDetected ports: {ports}")
    logger.info("Identifying robots by voltage...")
    
    leader_ports = []
    follower_ports = []
    
    for port in ports:
        is_leader, voltage = identify_robot_by_voltage(port, motor_ids)
        
        if is_leader:
            leader_ports.append(port)
        else:
            follower_ports.append(port)
    
    if len(leader_ports) != 2:
        raise RuntimeError(f"Expected 2 leader robots (5V), found {len(leader_ports)}")
    if len(follower_ports) != 2:
        raise RuntimeError(f"Expected 2 follower robots (12V), found {len(follower_ports)}")
    
    logger.info(f"\n✓ Successfully identified robots:")
    logger.info(f"  Leaders (5V):   {leader_ports}")
    logger.info(f"  Followers (12V): {follower_ports}")
    
    return leader_ports, follower_ports


class KeyboardListener:
    """Non-blocking keyboard input listener."""
    
    def __init__(self):
        self.switch_requested = False
        self.stop_requested = False
        self._listener_thread = None
        self._running = False
        
    def start(self):
        """Start the keyboard listener in a separate thread."""
        self._running = True
        self._listener_thread = threading.Thread(target=self._listen, daemon=True)
        self._listener_thread.start()
        
    def stop(self):
        """Stop the keyboard listener."""
        self._running = False
        
    def _listen(self):
        """Listen for keyboard input."""
        try:
            # For Unix-like systems (Linux, macOS)
            import termios
            import tty
            
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                while self._running:
                    if select and sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1)
                        if key.lower() == 's':
                            self.switch_requested = True
                        elif key == '\x03':  # Ctrl+C
                            self.stop_requested = True
                            break
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except ImportError:
            # Fallback for Windows - simplified version
            while self._running:
                try:
                    import msvcrt
                    if msvcrt.kbhit():
                        key = msvcrt.getch()
                        if key.lower() == b's':
                            self.switch_requested = True
                        elif key == b'\x03':  # Ctrl+C
                            self.stop_requested = True
                            break
                except:
                    pass
                time.sleep(0.1)
        except Exception:
            # Ultimate fallback - no keyboard support
            logger.warning("Keyboard input not supported on this system")


def move_cursor_up(lines: int) -> None:
    """Move terminal cursor up by specified number of lines."""
    print(f"\033[{lines}A", end="")


def busy_wait(duration: float) -> None:
    """Busy wait for the specified duration in seconds."""
    start_time = time.perf_counter()
    while time.perf_counter() - start_time < duration:
        pass


def create_random_mapping(leaders: List[SO101Controller], followers: List[SO101Controller]) -> Dict[str, str]:
    """
    Create a random mapping between leaders and followers.
    
    Returns:
        Dict mapping leader robot_id to follower robot_id
    """
    follower_ids = [f.robot_id for f in followers]
    random.shuffle(follower_ids)
    
    mapping = {}
    for i, leader in enumerate(leaders):
        mapping[leader.robot_id] = follower_ids[i]
    
    return mapping


def switch_mapping(current_mapping: Dict[str, str]) -> Dict[str, str]:
    """
    Switch the current mapping (swap the assignments).
    
    Returns:
        New mapping with assignments swapped
    """
    leader_ids = list(current_mapping.keys())
    follower_ids = list(current_mapping.values())
    
    # Swap the assignments
    new_mapping = {
        leader_ids[0]: follower_ids[1],
        leader_ids[1]: follower_ids[0]
    }
    
    return new_mapping


def teleoperation_loop(leaders: List[SO101Controller], followers: List[SO101Controller], 
                      fps: int, display_data: bool = False, duration: Optional[float] = None) -> None:
    """
    Main teleoperation loop for multiple robot pairs.
    
    Reads positions from leaders and sends them to followers based on current mapping.
    """
    # Verify all robots are connected
    all_robots = leaders + followers
    for robot in all_robots:
        if not robot.connected:
            raise RuntimeError(f"Robot {robot.robot_id} is not connected")
    
    # Enable torque on all followers
    logger.info("Enabling torque on follower robots...")
    for follower in followers:
        follower.enable_torque()
    
    # Create follower lookup dictionary
    follower_dict = {f.robot_id: f for f in followers}
    
    # Create initial random mapping
    mapping = create_random_mapping(leaders, followers)
    logger.info(f"\nInitial mapping:")
    for leader_id, follower_id in mapping.items():
        logger.info(f"  {leader_id} → {follower_id}")
    
    # Start keyboard listener
    keyboard = KeyboardListener()
    keyboard.start()
    
    start_time = time.perf_counter()
    
    logger.info(f"\nStarting teleoperation with {len(leaders)} leader-follower pairs...")
    logger.info(f"Using raw encoder values (0-{leaders[0].resolution-1}) for all motors")
    logger.info("Press 's' to switch mapping, Ctrl+C to stop\n")
    
    try:
        while True:
            loop_start = time.perf_counter()
            
            # Check for keyboard input
            if keyboard.switch_requested:
                keyboard.switch_requested = False
                mapping = switch_mapping(mapping)
                logger.info(f"\n🔄 Mapping switched:")
                for leader_id, follower_id in mapping.items():
                    logger.info(f"  {leader_id} → {follower_id}")
                logger.info("")
            
            if keyboard.stop_requested:
                break
            
            # Read positions from all leaders and send to mapped followers
            all_positions = {}
            for leader in leaders:
                leader_positions = leader.read_positions()
                if leader_positions:
                    all_positions[leader.robot_id] = leader_positions
                    
                    # Send to mapped follower
                    follower_id = mapping[leader.robot_id]
                    follower = follower_dict[follower_id]
                    follower.write_positions(leader_positions)
            
            if display_data and all_positions:
                # Display current mapping and positions
                print("\n" + "="*70)
                print("CURRENT MAPPING:")
                for leader_id, follower_id in mapping.items():
                    print(f"  {leader_id} → {follower_id}")
                print("="*70)
                
                for leader_id, positions in all_positions.items():
                    follower_id = mapping[leader_id]
                    print(f"\n{leader_id} → {follower_id}:")
                    print("-" * 50)
                    print(f"{'MOTOR ID':<10} | {'RAW VALUE':>10} | {'%':>6}")
                    print("-" * 50)
                    for motor_id, raw_value in positions.items():
                        # Calculate percentage of range (0-100%)
                        percent = (raw_value / (leaders[0].resolution - 1)) * 100
                        print(f"{motor_id:<10} | {raw_value:>10} | {percent:>5.1f}%")
                
                dt_s = time.perf_counter() - loop_start
                target_loop_time = 1 / fps
                if dt_s < target_loop_time:
                    busy_wait(target_loop_time - dt_s)
                loop_s = time.perf_counter() - loop_start
                
                print(f"\nLoop time: {loop_s * 1000:.2f}ms ({1 / loop_s:.0f} Hz)")
                print("Press 's' to switch mapping, Ctrl+C to stop")
                
                if duration is not None and time.perf_counter() - start_time >= duration:
                    return
                
                # Move cursor up to overwrite the display
                total_lines = 8 + len(mapping) + sum(len(pos) + 5 for pos in all_positions.values())
                move_cursor_up(total_lines)
            else:
                # Just maintain the loop rate
                dt_s = time.perf_counter() - loop_start
                target_loop_time = 1 / fps
                if dt_s < target_loop_time:
                    busy_wait(target_loop_time - dt_s)
                
                if duration is not None and time.perf_counter() - start_time >= duration:
                    return
                    
    finally:
        keyboard.stop()


def main():
    parser = argparse.ArgumentParser(description="Multi-arm teleoperation for SO101 robots with STS3215 servos")
    parser.add_argument("--motor_ids", type=str, default="1,2,3,4,5,6",
                       help="Comma-separated list of motor IDs (default: 1,2,3,4,5,6)")
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
    
    # Initialize variables to avoid type errors
    leaders: List[SO101Controller] = []
    followers: List[SO101Controller] = []
    
    try:
        # Auto-detect and identify all 4 robots
        leader_ports, follower_ports = auto_detect_and_identify_ports(motor_ids)
        
        # Create robot controllers
        leaders = [
            SO101Controller(leader_ports[0], motor_ids, args.baudrate, "Leader1"),
            SO101Controller(leader_ports[1], motor_ids, args.baudrate, "Leader2")
        ]
        
        followers = [
            SO101Controller(follower_ports[0], motor_ids, args.baudrate, "Follower1"),
            SO101Controller(follower_ports[1], motor_ids, args.baudrate, "Follower2")
        ]
        
        # Connect all robots
        logger.info("\nConnecting to all robots...")
        for robot in leaders + followers:
            robot.connect()
        
        # Run teleoperation
        teleoperation_loop(
            leaders, 
            followers, 
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
        logger.info("Disconnecting all robots...")
        try:
            all_robots = leaders + followers
            for robot in all_robots:
                robot.disconnect()
        except:
            pass
        logger.info("Multi-arm teleoperation complete!")


if __name__ == "__main__":
    main() 