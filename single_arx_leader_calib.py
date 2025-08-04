#!/usr/bin/env python3
"""
ARX Leader Arm Calibration Script

This script calibrates the leader servo arm positions to correspond with the ARX R5 
follower arm's home position. Since both arms cannot be connected simultaneously 
due to OS compatibility issues, this script handles only the leader arm calibration.

The calibration process:
1. Connect to the leader servo arm (Waveshare + SC servos)
2. User manually positions the leader arm to match the ARX R5 home position
3. Record the current servo positions as the "home" reference
4. Save calibration data for use in teleoperation

Usage:
    python single_arx_leader_calib.py [--port PORT] [--motor_ids IDS]
"""

import argparse
import json
import logging
import os
import platform
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    # Fallback if colorama not installed
    class Fore:
        RED = GREEN = YELLOW = CYAN = MAGENTA = BLUE = ""
    class Style:
        RESET_ALL = BRIGHT = ""

# Default calibration file path
CALIBRATION_FILE = "arx_leader_calibration.json"


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


def auto_detect_port() -> str:
    """Automatically detect a single robot port."""
    ports = find_robot_ports()
    
    if len(ports) == 0:
        raise RuntimeError("No robot ports detected. Please ensure your device is connected via USB.")
    elif len(ports) == 1:
        logger.info(f"Auto-detected port: {ports[0]}")
        return ports[0]
    else:
        logger.info(f"Multiple ports detected: {ports}")
        logger.info("Using the first port. To use a different port, specify it with --port")
        return ports[0]


class LeaderArmCalibrator:
    """Calibrates leader servo arm positions for ARX teleoperation."""
    
    def __init__(self, port: str, motor_ids: List[int], baudrate: int = 1000000):
        self.port = port
        self.motor_ids = motor_ids
        self.baudrate = baudrate
        self.connected = False
        self.servo_controller = None
        
        # Servo specifications (STS3215)
        self.resolution = 4096  # 0-4095
        self.max_position = 4095
        
        # Initialize servo controller
        self._init_servo_controller()
        
    def _init_servo_controller(self):
        """Initialize the servo controller."""
        try:
            import scservo_sdk as scs
            self.scs = scs
        except ImportError:
            raise RuntimeError("scservo_sdk not installed. Please install from Feetech SDK")
            
        self.port_handler = None
        self.packet_handler = None
        
    def connect(self) -> bool:
        """Connect to the servo controller."""
        try:
            self.port_handler = self.scs.PortHandler(self.port)
            self.packet_handler = self.scs.PacketHandler(0)  # Protocol 0
            
            if not self.port_handler.openPort():
                raise RuntimeError(f"Failed to open port '{self.port}'")
                
            if not self.port_handler.setBaudRate(self.baudrate):
                raise RuntimeError(f"Failed to set baudrate to {self.baudrate}")
                
            # Test connection by pinging motors
            logger.info("Testing connection to servos...")
            for motor_id in self.motor_ids:
                ping_result = self.packet_handler.ping(self.port_handler, motor_id)
                if isinstance(ping_result, tuple) and len(ping_result) >= 2:
                    if len(ping_result) >= 3:
                        model_number, result, error = ping_result[:3]
                    else:
                        model_number, result = ping_result[:2]
                    
                    if result != self.scs.COMM_SUCCESS:
                        raise RuntimeError(f"Failed to ping motor {motor_id}")
                        
                logger.info(f"✓ Motor {motor_id} connected")
                
            self.connected = True
            logger.info(f"{Fore.GREEN}✓ Connected to leader arm on {self.port}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from the servo controller."""
        if self.port_handler:
            self.port_handler.closePort()
        self.connected = False
        logger.info("Disconnected from leader arm")
        
    def read_servo_positions(self) -> Dict[int, int]:
        """Read current positions from all servos."""
        if not self.connected:
            raise RuntimeError("Not connected to servos")
            
        positions = {}
        for motor_id in self.motor_ids:
            try:
                read_result = self.packet_handler.read2ByteTxRx(
                    self.port_handler, motor_id, 56)  # PRESENT_POSITION = 56
                
                if isinstance(read_result, tuple) and len(read_result) >= 2:
                    if len(read_result) >= 3:
                        position, result, error = read_result[:3]
                    else:
                        position, result = read_result[:2]
                    
                    if result == self.scs.COMM_SUCCESS:
                        positions[motor_id] = position
                    else:
                        logger.warning(f"Failed to read position from motor {motor_id}")
                else:
                    logger.warning(f"Unexpected read result from motor {motor_id}: {read_result}")
                    
            except Exception as e:
                logger.warning(f"Exception reading motor {motor_id}: {e}")
                
        return positions
        
    def read_servo_voltage(self) -> float:
        """Read voltage from the first servo to identify robot type."""
        if not self.connected:
            raise RuntimeError("Not connected to servos")
            
        motor_id = self.motor_ids[0]
        try:
            read_result = self.packet_handler.read1ByteTxRx(
                self.port_handler, motor_id, 62)  # PRESENT_VOLTAGE = 62
            
            if isinstance(read_result, tuple) and len(read_result) >= 2:
                if len(read_result) >= 3:
                    raw_voltage, result, error = read_result[:3]
                else:
                    raw_voltage, result = read_result[:2]
                
                if result == self.scs.COMM_SUCCESS:
                    return raw_voltage / 10.0  # Convert to volts
                    
        except Exception as e:
            logger.warning(f"Failed to read voltage: {e}")
            
        return 0.0
        
    def display_current_positions(self):
        """Display current servo positions in a readable format."""
        positions = self.read_servo_positions()
        voltage = self.read_servo_voltage()
        
        print(f"\n{Fore.CYAN}Current Leader Arm Status:{Style.RESET_ALL}")
        print(f"Voltage: {voltage:.1f}V")
        print(f"{'Motor ID':<10} | {'Position':>10} | {'Degrees':>10} | {'Percent':>8}")
        print("-" * 50)
        
        for motor_id in sorted(self.motor_ids):
            position = positions.get(motor_id, -1)
            if position >= 0:
                degrees = (position / self.resolution) * 360
                percent = (position / self.max_position) * 100
                print(f"{motor_id:<10} | {position:>10} | {degrees:>9.1f}° | {percent:>7.1f}%")
            else:
                print(f"{motor_id:<10} | {'ERROR':>10} | {'---':>10} | {'---':>8}")
                
    def capture_home_positions(self) -> Dict[int, int]:
        """Capture current positions as home reference."""
        positions = self.read_servo_positions()
        
        if len(positions) != len(self.motor_ids):
            missing = set(self.motor_ids) - set(positions.keys())
            raise RuntimeError(f"Failed to read positions from motors: {missing}")
            
        return positions
        
    def save_calibration(self, home_positions: Dict[int, int], 
                        calibration_file: str = CALIBRATION_FILE) -> bool:
        """Save calibration data to JSON file."""
        try:
            voltage = self.read_servo_voltage()
            is_leader = 4.5 <= voltage <= 5.5
            
            calibration_data = {
                "timestamp": time.time(),
                "timestamp_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                "motor_ids": self.motor_ids,
                "home_positions": home_positions,
                "servo_resolution": self.resolution,
                "port": self.port,
                "voltage": voltage,
                "is_leader": is_leader,
                "notes": "Leader arm home positions corresponding to ARX R5 home pose"
            }
            
            with open(calibration_file, 'w') as f:
                json.dump(calibration_data, f, indent=2)
                
            logger.info(f"{Fore.GREEN}✓ Calibration saved to {calibration_file}{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save calibration: {e}")
            return False
            
    def load_calibration(self, calibration_file: str = CALIBRATION_FILE) -> Optional[Dict]:
        """Load calibration data from JSON file."""
        try:
            if not os.path.exists(calibration_file):
                logger.warning(f"Calibration file not found: {calibration_file}")
                return None
                
            with open(calibration_file, 'r') as f:
                calibration_data = json.load(f)
                
            logger.info(f"✓ Loaded calibration from {calibration_file}")
            logger.info(f"  Created: {calibration_data.get('timestamp_str', 'Unknown')}")
            logger.info(f"  Motor IDs: {calibration_data.get('motor_ids', [])}")
            
            return calibration_data
            
        except Exception as e:
            logger.error(f"Failed to load calibration: {e}")
            return None
            
    def test_calibration(self, calibration_file: str = CALIBRATION_FILE):
        """Test the current calibration by showing position differences."""
        calibration_data = self.load_calibration(calibration_file)
        if not calibration_data:
            logger.error("No calibration data available for testing")
            return
            
        home_positions = calibration_data["home_positions"]
        current_positions = self.read_servo_positions()
        
        print(f"\n{Fore.YELLOW}Calibration Test - Position Differences:{Style.RESET_ALL}")
        print(f"{'Motor':<8} | {'Home':>8} | {'Current':>8} | {'Diff':>8} | {'Radians':>10}")
        print("-" * 55)
        
        for motor_id in sorted(self.motor_ids):
            home_pos = home_positions.get(str(motor_id), 0)  # JSON keys are strings
            current_pos = current_positions.get(motor_id, 0)
            diff_tics = current_pos - home_pos
            
            # Convert to radians (same formula as teleoperation)
            diff_radians = diff_tics * (2 * 3.14159) / 4095.0
            
            print(f"{motor_id:<8} | {home_pos:>8} | {current_pos:>8} | {diff_tics:>8} | {diff_radians:>9.3f}")


def guided_calibration(calibrator: LeaderArmCalibrator, calibration_file: str = CALIBRATION_FILE):
    """Run the guided calibration process."""
    print(f"\n{Fore.BLUE}=== ARX Leader Arm Calibration Process ==={Style.RESET_ALL}")
    print()
    print("This process will calibrate your leader servo arm to work with the ARX R5 follower.")
    print()
    print(f"{Fore.YELLOW}IMPORTANT SETUP INSTRUCTIONS:{Style.RESET_ALL}")
    print("1. Ensure your ARX R5 follower arm is powered and in its HOME position")
    print("   (Run the ARX arm's go_home() function separately)")
    print("2. Manually position your leader servo arm to match the ARX R5 home pose")
    print("3. Make sure all joints are aligned as closely as possible")
    print("4. The leader arm should mimic the ARX arm's joint angles and orientation")
    print()
    
    # Display current status
    calibrator.display_current_positions()
    
    print(f"\n{Fore.CYAN}Calibration Steps:{Style.RESET_ALL}")
    print("1. Position the leader arm to match ARX R5 home position")
    print("2. Confirm the positions look correct")
    print("3. Capture and save the calibration")
    print()
    
    while True:
        print(f"{Fore.YELLOW}Current servo positions:{Style.RESET_ALL}")
        calibrator.display_current_positions()
        
        print(f"\n{Fore.GREEN}Options:{Style.RESET_ALL}")
        print("  [r] Refresh positions")
        print("  [c] Capture calibration (when leader matches ARX home)")
        print("  [t] Test existing calibration")
        print("  [q] Quit")
        
        choice = input("\nEnter choice: ").lower().strip()
        
        if choice == 'r':
            continue  # Refresh display
            
        elif choice == 'c':
            print(f"\n{Fore.YELLOW}Capturing calibration...{Style.RESET_ALL}")
            try:
                home_positions = calibrator.capture_home_positions()
                
                print(f"\n{Fore.CYAN}Captured positions:{Style.RESET_ALL}")
                for motor_id, pos in sorted(home_positions.items()):
                    print(f"  Motor {motor_id}: {pos}")
                
                confirm = input(f"\n{Fore.YELLOW}Save this calibration? (y/n): {Style.RESET_ALL}").lower()
                if confirm in ['y', 'yes']:
                    if calibrator.save_calibration(home_positions, calibration_file):
                        print(f"\n{Fore.GREEN}✓ Calibration completed successfully!{Style.RESET_ALL}")
                        print(f"Calibration saved to: {calibration_file}")
                        print("\nYou can now use this calibration in teleoperation.")
                        break
                    else:
                        print(f"{Fore.RED}✗ Failed to save calibration{Style.RESET_ALL}")
                else:
                    print("Calibration cancelled.")
                    
            except Exception as e:
                logger.error(f"Error during calibration: {e}")
                
        elif choice == 't':
            calibrator.test_calibration(calibration_file)
            
        elif choice == 'q':
            print("Calibration cancelled.")
            break
            
        else:
            print("Invalid choice. Please try again.")


def main():
    parser = argparse.ArgumentParser(description="Calibrate leader servo arm for ARX teleoperation")
    parser.add_argument("--port", type=str, help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--motor_ids", type=str, default="1,2,3,4,5,6,7",
                       help="Comma-separated motor IDs (default: 1,2,3,4,5,6,7)")
    parser.add_argument("--baudrate", type=int, default=1000000,
                       help="Baudrate (default: 1000000)")
    parser.add_argument("--calibration_file", type=str, default=CALIBRATION_FILE,
                       help=f"Calibration file path (default: {CALIBRATION_FILE})")
    parser.add_argument("--test_only", action="store_true",
                       help="Only test existing calibration (don't modify)")
    
    args = parser.parse_args()
    
    # Parse motor IDs
    motor_ids = [int(id.strip()) for id in args.motor_ids.split(",")]
    logger.info(f"Using motor IDs: {motor_ids}")
    
    # Determine port
    if args.port:
        port = args.port
    else:
        try:
            port = auto_detect_port()
        except RuntimeError as e:
            logger.error(str(e))
            return 1
    
    # Create calibrator
    calibrator = LeaderArmCalibrator(port, motor_ids, args.baudrate)
    
    try:
        # Connect to servos
        if not calibrator.connect():
            logger.error("Failed to connect to leader arm")
            return 1
            
        # Check if we're just testing
        if args.test_only:
            calibrator.test_calibration(args.calibration_file)
        else:
            # Run guided calibration
            guided_calibration(calibrator, args.calibration_file)
            
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Calibration interrupted by user{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"Calibration error: {e}")
        return 1
    finally:
        calibrator.disconnect()
        
    return 0


if __name__ == "__main__":
    sys.exit(main())