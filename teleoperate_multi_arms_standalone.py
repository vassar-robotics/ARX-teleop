#!/usr/bin/env python3
"""
Standalone teleoperation script for multiple SO101 robots without calibration.

This script connects to two leader robots (<9V) and two follower robots (>=9V) with 
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
import signal
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

# Global flag for graceful shutdown
shutdown_requested = False


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
            try:
                ping_result = self.packet_handler.ping(self.port_handler, motor_id)
                # Handle different return formats from Feetech SDK
                if isinstance(ping_result, tuple) and len(ping_result) >= 2:
                    if len(ping_result) >= 3:
                        model_number, result, error = ping_result[:3]
                    else:
                        model_number, result = ping_result[:2]
                    
                    if result != self.scs.COMM_SUCCESS:
                        raise RuntimeError(f"Failed to ping motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")
                else:
                    raise RuntimeError(f"Unexpected ping result: {ping_result}")
            except Exception as e:
                raise RuntimeError(f"Failed to ping motor {motor_id}: {str(e)}")
                
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
        try:
            read_result = self.packet_handler.read1ByteTxRx(
                self.port_handler, motor_id, self.PRESENT_VOLTAGE)
            
            # Handle different return formats
            if len(read_result) >= 3:
                raw_voltage, result, error = read_result
            elif len(read_result) == 2:
                raw_voltage, result = read_result
                error = 0
            else:
                raise RuntimeError(f"Unexpected read result format: {read_result}")
            
            if result != self.scs.COMM_SUCCESS:
                raise RuntimeError(f"Failed to read voltage: {self.packet_handler.getTxRxResult(result)}")
                
            # Feetech motors report voltage in units of 0.1V
            return raw_voltage / 10.0
        except Exception as e:
            raise RuntimeError(f"Failed to read voltage from motor {motor_id}: {str(e)}")
        
    def read_positions(self) -> Dict[int, int]:
        """Read current positions from all motors."""
        positions = {}
        for motor_id in self.motor_ids:
            try:
                read_result = self.packet_handler.read2ByteTxRx(
                    self.port_handler, motor_id, self.PRESENT_POSITION)
                
                # Handle different return formats
                if len(read_result) >= 3:
                    position, result, error = read_result
                elif len(read_result) == 2:
                    position, result = read_result
                    error = 0
                else:
                    logger.warning(f"Unexpected read result format from motor {motor_id} on {self.robot_id}: {read_result}")
                    continue
                    
                if result == self.scs.COMM_SUCCESS:
                    positions[motor_id] = position
                else:
                    logger.warning(f"Failed to read position from motor {motor_id} on {self.robot_id}")
            except Exception as e:
                logger.warning(f"Exception reading position from motor {motor_id} on {self.robot_id}: {e}")
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

    def disable_torque(self) -> None:
        """Disable torque on all motors."""
        for motor_id in self.motor_ids:
            # Set Lock to 0 (unlocked) first
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, motor_id, self.LOCK, 0)
            if result != self.scs.COMM_SUCCESS:
                logger.warning(f"Failed to unlock motor {motor_id} on {self.robot_id}")
                
            # Then disable torque
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, motor_id, self.TORQUE_ENABLE, 0)
            if result != self.scs.COMM_SUCCESS:
                logger.warning(f"Failed to disable torque on motor {motor_id} on {self.robot_id}")


def identify_robot_by_voltage(port: str, motor_ids: List[int]) -> tuple[bool, float] | None:
    """
    Identify if a robot is leader (<9V) or follower (>=9V) by reading voltage.
    
    Returns:
        tuple: (is_leader, voltage) where is_leader is True for <9V robots
        None: if connection fails
    """
    try:
        logger.info(f"Connecting to robot at {port} to read voltage...")
        robot = SO101Controller(port, motor_ids)
        robot.connect()
        
        voltage = robot.read_voltage()
        robot.disconnect()
        
        # Determine if this is leader (<9V) or follower (>=9V)
        is_leader = voltage < 9.0
        
        logger.info(f"Port {port}: Voltage = {voltage:.1f}V -> {'LEADER' if is_leader else 'FOLLOWER'}")
        
        return is_leader, voltage
        
    except Exception as e:
        logger.warning(f"Failed to connect to {port}: {e}")
        return None


def auto_detect_and_identify_ports(motor_ids: List[int]) -> tuple[List[str], List[str]]:
    """
    Automatically detect robot ports and identify leaders vs followers by voltage.
    
    Returns:
        tuple: (leader_ports, follower_ports)
    """
    ports = find_robot_ports()
    
    if len(ports) == 0:
        raise RuntimeError(
            "No robot ports detected. Please ensure all robots are connected via USB."
        )
    
    logger.info(f"\nDetected {len(ports)} potential robot ports: {ports}")
    logger.info("Identifying robots by voltage...")
    logger.info("(Note: USB hubs and other devices may appear as ports)")
    
    leader_ports = []
    follower_ports = []
    failed_ports = []
    
    for port in ports:
        result = identify_robot_by_voltage(port, motor_ids)
        
        if result is not None:
            is_leader, voltage = result
            
            if is_leader:
                leader_ports.append(port)
            else:
                follower_ports.append(port)
        else:
            failed_ports.append(port)
            logger.info(f"Skipping {port} - not a robot or connection failed")
    
    # Show summary
    total_robots = len(leader_ports) + len(follower_ports)
    logger.info(f"\n📊 Detection Summary:")
    logger.info(f"  Total ports scanned: {len(ports)}")
    logger.info(f"  Robots found: {total_robots}")
    logger.info(f"  Failed connections: {len(failed_ports)}")
    if failed_ports:
        logger.info(f"  Failed ports: {failed_ports}")
    
    # Check if we have valid configurations
    if total_robots == 2 and len(leader_ports) == 1 and len(follower_ports) == 1:
        logger.info("\n✓ Detected 2-robot configuration (1 leader + 1 follower)")
    elif total_robots == 4 and len(leader_ports) == 2 and len(follower_ports) == 2:
        logger.info("\n✓ Detected 4-robot configuration (2 leaders + 2 followers)")
    elif total_robots > 0:
        # Provide helpful guidance for non-standard configurations
        logger.warning(f"\n⚠️  Non-standard robot configuration detected:")
        logger.warning(f"  Found {len(leader_ports)} leader(s) (<9V) and {len(follower_ports)} follower(s) (>=9V)")
        logger.warning("  Expected configurations:")
        logger.warning(f"    - 1 leader + 1 follower (2 robots)")
        logger.warning(f"    - 2 leaders + 2 followers (4 robots)")
        logger.warning("  Please check:")
        logger.warning(f"    1. Check power supply voltages (leaders<9V, followers>=9V)")
        logger.warning(f"    2. Ensure all robots are properly connected")
        logger.warning(f"    3. If using a USB hub, try different ports or a powered hub")
        logger.warning(f"    4. Disconnect any non-robot USB serial devices")
        
        raise RuntimeError(
            f"Invalid robot configuration: {len(leader_ports)} leader(s), {len(follower_ports)} follower(s)"
        )
    else:
        raise RuntimeError("No robots detected. Check connections and power.")
    
    # Log the detected configuration
    logger.info(f"\n📍 Auto-detected ports:")
    logger.info(f"  Leaders (<9V):   {leader_ports}")
    logger.info(f"  Followers (>=9V): {follower_ports}")
    
    return leader_ports, follower_ports


def scan_all_ports(motor_ids: List[int]) -> None:
    """
    Scan all ports and try to identify robots without running teleoperation.
    Useful for debugging connection issues.
    """
    ports = find_robot_ports()
    
    if len(ports) == 0:
        logger.error("No potential robot ports detected.")
        return
    
    logger.info(f"\n🔍 Scanning {len(ports)} ports for robots...")
    logger.info(f"Testing with motor IDs: {motor_ids}")
    logger.info("-" * 70)
    
    robots_found = 0
    
    for i, port in enumerate(ports):
        logger.info(f"\n[{i+1}/{len(ports)}] Testing port: {port}")
        
        try:
            # Try to connect
            robot = SO101Controller(port, motor_ids)
            robot.connect()
            
            # Read voltage
            voltage = robot.read_voltage()
            robot_type = "LEADER (<9V)" if voltage < 9.0 else "FOLLOWER (>=9V)"
            print(f"\n  ✓ Robot connected on {port}:")
            
            # Try to read positions
            positions = robot.read_positions()
            
            logger.info(f"  ✓ Robot found!")
            logger.info(f"  Type: {robot_type}")
            logger.info(f"  Voltage: {voltage:.1f}V")
            logger.info(f"  Motors responding: {list(positions.keys())}")
            
            robots_found += 1
            robot.disconnect()
            
        except Exception as e:
            logger.error(f"  ✗ Failed: {str(e)}")
            
            # Try alternative motor IDs if the default fails
            if "Failed to ping motor" in str(e):
                logger.info("  Trying alternative motor ID ranges...")
                
                # Common motor ID ranges
                alt_ranges = [
                    [1, 2, 3, 4, 5, 6, 7],  # 7 motors
                    [1, 2, 3, 4],           # 4 motors
                    [0, 1, 2, 3, 4, 5, 6],  # Starting from 0
                    [2, 3, 4, 5, 6, 7],     # Starting from 2
                ]
                
                for alt_ids in alt_ranges:
                    if alt_ids == motor_ids:
                        continue
                    
                    try:
                        logger.info(f"    Testing IDs: {alt_ids}")
                        robot = SO101Controller(port, alt_ids)
                        robot.connect()
                        voltage = robot.read_voltage()
                        robot_type = "LEADER (<9V)" if voltage < 9.0 else "FOLLOWER (>=9V)"
                        
                        logger.info(f"    ✓ Robot found with motor IDs: {alt_ids}")
                        logger.info(f"    Type: {robot_type}, Voltage: {voltage:.1f}V")
                        robots_found += 1
                        robot.disconnect()
                        break
                        
                    except:
                        pass
    
    logger.info("-" * 70)
    logger.info(f"\n📊 Scan complete: {robots_found} robot(s) found out of {len(ports)} ports")
    
    if robots_found < 4 and len(ports) >= 4:
        logger.info("\n💡 Tips for missing robots:")
        logger.info("  1. Check if all robots are powered on")
        logger.info("  2. Try different USB ports or a powered USB hub")
        logger.info("  3. Verify motor IDs match your robot configuration")
        logger.info("  4. Ensure baudrate is correct (default: 1000000)")


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


def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) for graceful shutdown."""
    global shutdown_requested
    logger.info("\n\n⚠️  Shutdown requested. Cleaning up...")
    shutdown_requested = True


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
    
    # Determine if we're in 2-robot or 4-robot mode
    is_multi_mode = len(leaders) == 2
    
    # Create initial mapping
    if is_multi_mode:
        # 4-robot mode: create random mapping
        mapping = create_random_mapping(leaders, followers)
        logger.info(f"\nInitial mapping:")
        for leader_id, follower_id in mapping.items():
            logger.info(f"  {leader_id} → {follower_id}")
    else:
        # 2-robot mode: direct 1:1 mapping
        mapping = {leaders[0].robot_id: followers[0].robot_id}
        logger.info(f"\nDirect mapping: {leaders[0].robot_id} → {followers[0].robot_id}")
    
    # Start keyboard listener only for multi-mode
    keyboard = None
    if is_multi_mode:
        keyboard = KeyboardListener()
        keyboard.start()
        logger.info("\nPress 's' to switch mapping, Ctrl+C to stop")
    else:
        logger.info("\nPress Ctrl+C to stop")
    
    start_time = time.perf_counter()
    
    logger.info(f"\nStarting teleoperation with {len(leaders)} leader-follower pair(s)...")
    logger.info(f"Using raw encoder values (0-{leaders[0].resolution-1}) for all motors\n")
    
    try:
        while not shutdown_requested:
            loop_start = time.perf_counter()
            
            # Check for keyboard input (only in multi-mode)
            if keyboard:
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
                if is_multi_mode:
                    print("CURRENT MAPPING:")
                    for leader_id, follower_id in mapping.items():
                        print(f"  {leader_id} → {follower_id}")
                else:
                    print(f"TELEOPERATION: {leaders[0].robot_id} → {followers[0].robot_id}")
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
                if is_multi_mode:
                    print("Press 's' to switch mapping, Ctrl+C to stop")
                else:
                    print("Press Ctrl+C to stop")
                
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
        if keyboard:
            keyboard.stop()


def main():
    """Main function to run multi-arm teleoperation."""
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
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
    parser.add_argument("--scan", action="store_true",
                       help="Scan all detected ports to identify robots without teleoperation")
    
    args = parser.parse_args()
    
    # Parse motor IDs
    motor_ids = [int(id.strip()) for id in args.motor_ids.split(",")]
    
    # Initialize variables to avoid type errors
    leaders: List[SO101Controller] = []
    followers: List[SO101Controller] = []
    
    try:
        if args.scan:
            scan_all_ports(motor_ids)
        else:
            # Auto-detect and identify all robots
            leader_ports, follower_ports = auto_detect_and_identify_ports(motor_ids)
            
            # Create robot controllers based on what we found
            if len(leader_ports) == 1:
                # 2-robot mode
                leaders = [
                    SO101Controller(leader_ports[0], motor_ids, args.baudrate, "Leader")
                ]
                followers = [
                    SO101Controller(follower_ports[0], motor_ids, args.baudrate, "Follower")
                ]
                logger.info("\nConfigured for 2-robot teleoperation")
            else:
                # 4-robot mode
                leaders = [
                    SO101Controller(leader_ports[0], motor_ids, args.baudrate, "Leader1"),
                    SO101Controller(leader_ports[1], motor_ids, args.baudrate, "Leader2")
                ]
                followers = [
                    SO101Controller(follower_ports[0], motor_ids, args.baudrate, "Follower1"),
                    SO101Controller(follower_ports[1], motor_ids, args.baudrate, "Follower2")
                ]
                logger.info("\nConfigured for 4-robot teleoperation")
            
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
        logger.info("\nCleaning up...")
        try:
            # First disable torque on all robots (especially important for followers)
            logger.info("Disabling torque on all robots...")
            all_robots = leaders + followers
            for robot in all_robots:
                try:
                    if robot.connected:
                        robot.disable_torque()
                except Exception as e:
                    logger.warning(f"Failed to disable torque on {robot.robot_id}: {e}")
            
            # Then disconnect
            logger.info("Disconnecting all robots...")
            for robot in all_robots:
                try:
                    robot.disconnect()
                except Exception as e:
                    logger.warning(f"Failed to disconnect {robot.robot_id}: {e}")
        except:
            pass
        logger.info("Multi-arm teleoperation complete!")


if __name__ == "__main__":
    main() 