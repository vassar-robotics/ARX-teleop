#!/usr/bin/env python3
"""
Standalone script to set Feetech servo motors to their middle position.

This script connects to Feetech servo motors, disables torque, and sets the homing
offsets so that the current position becomes the middle point of the servo's range.

Requirements:
- pyserial
- scservo_sdk (for Feetech motors)

Example usage:
```shell
# Basic usage (uses defaults: motor IDs 1-6, auto-detect port, baudrate 1M):
python set_middle_position_standalone.py

# Custom motor IDs:
python set_middle_position_standalone.py --motor_ids=1,2,3,4

# Specify port manually:
python set_middle_position_standalone.py --port=/dev/ttyUSB0

# Continuous mode for multiple robots:
python set_middle_position_standalone.py --continuous
```
"""

import argparse
import logging
import platform
import sys
import time
from typing import Dict, List, Any

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


def auto_detect_port() -> str:
    """Automatically detect a single robot port."""
    ports = find_robot_ports()
    
    if len(ports) == 0:
        raise RuntimeError("No robot ports detected. Please ensure your device is connected via USB.")
    elif len(ports) == 1:
        logger.info(f"Auto-detected port: {ports[0]}")
        return ports[0]
    else:
        raise RuntimeError(f"Multiple potential robot ports detected: {ports}\n"
                          "Please disconnect all but one robot or specify port manually.")


def wait_for_keypress() -> bool:
    """Wait for spacebar or 'q' key press. Returns True for space, False for 'q'."""
    try:
        # For Unix-like systems (Linux, macOS)
        import termios
        import tty
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            while True:
                key = sys.stdin.read(1)
                if key == ' ':
                    return True
                elif key.lower() == 'q':
                    return False
                elif key == '\x03':  # Ctrl+C
                    raise KeyboardInterrupt
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except ImportError:
        # Fallback for Windows
        import msvcrt
        
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b' ':
                    return True
                elif key.lower() == b'q':
                    return False
    except Exception:
        # Ultimate fallback
        response = input("\nPress Enter to continue or 'q' to quit: ")
        return response.lower() != 'q'


class FeetechController:
    """Controller for Feetech motors."""
    
    # Feetech register addresses (for STS/SMS series)
    TORQUE_ENABLE = 40
    PRESENT_POSITION = 56
    HOMING_OFFSET = 31
    OPERATING_MODE = 33
    PHASE = 18
    LOCK = 55
    
    def __init__(self, port: str, motor_ids: List[int], baudrate: int = 1000000, 
                 motor_model: str = "sts3215"):
        self.port = port
        self.motor_ids = motor_ids
        self.baudrate = baudrate
        self.motor_model = motor_model
        self.connected = False
        
        # Set resolution based on motor model
        if motor_model in ["sts3215", "sts3250"]:
            self.resolution = 4096
        elif motor_model == "sm8512bl":
            self.resolution = 65536
        elif motor_model == "scs0009":
            self.resolution = 1024
        else:
            self.resolution = 4096  # Default
            
        try:
            import scservo_sdk as scs  # type: ignore
            self.scs = scs
        except ImportError:
            raise RuntimeError("scservo_sdk not installed. Please install from Feetech SDK")
            
        self.port_handler: Any = None
        self.packet_handler: Any = None
        
    def connect(self) -> None:
        """Connect to the Feetech bus."""
        self.port_handler = self.scs.PortHandler(self.port)
        self.packet_handler = self.scs.PacketHandler(0)  # Protocol 0 for most Feetech
        
        if not self.port_handler.openPort():
            raise RuntimeError(f"Failed to open port '{self.port}'")
            
        if not self.port_handler.setBaudRate(self.baudrate):
            raise RuntimeError(f"Failed to set baudrate to {self.baudrate}")
            
        # Test connection by pinging motors
        for motor_id in self.motor_ids:
            result, error = self.packet_handler.ping(self.port_handler, motor_id)
            if result != self.scs.COMM_SUCCESS:
                raise RuntimeError(f"Failed to ping motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")
                
        self.connected = True
        logger.info(f"Connected to Feetech motors: {self.motor_ids}")
        
    def disconnect(self) -> None:
        """Disconnect from the Feetech bus."""
        if self.port_handler:
            self.port_handler.closePort()
        self.connected = False
        
    def disable_torque(self) -> None:
        """Disable torque on all motors."""
        for motor_id in self.motor_ids:
            # Disable torque
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, motor_id, self.TORQUE_ENABLE, 0)
            if result != self.scs.COMM_SUCCESS:
                logger.warning(f"Failed to disable torque on motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")
                
            # Set Lock to 0
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, motor_id, self.LOCK, 0)
            if result != self.scs.COMM_SUCCESS:
                logger.warning(f"Failed to set lock on motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")
                
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
        
    def write_homing_offsets(self, offsets: Dict[int, int]) -> None:
        """Write homing offsets to all motors."""
        for motor_id, offset in offsets.items():
            # Convert negative offsets for sign-magnitude encoding
            if offset < 0:
                offset = abs(offset) | (1 << 11)  # Set sign bit (bit 11)
                
            result, error = self.packet_handler.write2ByteTxRx(
                self.port_handler, motor_id, self.HOMING_OFFSET, offset)
            if result != self.scs.COMM_SUCCESS:
                logger.warning(f"Failed to write homing offset to motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")
                
    def set_phase_and_lock(self) -> None:
        """Set Phase=76 and Lock=0 for Feetech motors."""
        logger.info("Setting Phase=76 and Lock=0 for all motors...")
        for motor_id in self.motor_ids:
            # Set Phase (Setting byte) to 76
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, motor_id, self.PHASE, 76)
            if result != self.scs.COMM_SUCCESS:
                logger.warning(f"Failed to set Phase on motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")
                
            # Set Lock to 0
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, motor_id, self.LOCK, 0)
            if result != self.scs.COMM_SUCCESS:
                logger.warning(f"Failed to set Lock on motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")
                
    def set_operating_mode(self) -> None:
        """Set operating mode for Feetech motors."""
        for motor_id in self.motor_ids:
            # Set to position mode (0)
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, motor_id, self.OPERATING_MODE, 0)
            if result != self.scs.COMM_SUCCESS:
                logger.warning(f"Failed to set operating mode on motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")
                
    def calculate_homing_offsets(self, positions: Dict[int, int]) -> Dict[int, int]:
        """Calculate homing offsets for Feetech motors."""
        offsets = {}
        for motor_id, pos in positions.items():
            # For Feetech: homing_offset = current_pos - int(max_res / 2)
            offsets[motor_id] = pos - int(self.resolution / 2)
        return offsets


def set_middle_position(controller: FeetechController) -> None:
    """Set servos to their middle position by configuring homing offsets."""
    logger.info(f"Setting middle position for {len(controller.motor_ids)} motors")
    
    # Disable torque to allow manual positioning
    controller.disable_torque()
    
    # Set Phase=76 and Lock=0
    controller.set_phase_and_lock()
    
    # Set operating mode
    controller.set_operating_mode()
    
    input("\nMove the device to the desired middle position and press ENTER...")
    
    # Read current positions
    positions = controller.read_positions()
    if not positions:
        logger.error("Failed to read positions from any motor")
        return
        
    # Calculate homing offsets
    offsets = controller.calculate_homing_offsets(positions)
    
    # Write homing offsets
    logger.info("Setting homing offsets...")
    controller.write_homing_offsets(offsets)
    
    logger.info("\nHoming offsets set:")
    for motor_id, offset in offsets.items():
        logger.info(f"  Motor {motor_id}: {offset}")
    
    logger.info("\n✓ Middle position set successfully!")
    logger.info("The current position is now the middle point for all servos.")
    logger.info("Phase (Setting byte) has been set to 76 and Lock to 0 for all servos.")


def process_single_robot(port: str, motor_ids: List[int], motor_model: str, baudrate: int) -> bool:
    """Process a single robot by setting middle position."""
    controller = None
    try:
        controller = FeetechController(port, motor_ids, baudrate, motor_model)
        controller.connect()
        set_middle_position(controller)
        return True
    except Exception as e:
        logger.error(f"Error processing robot: {e}")
        return False
    finally:
        if controller:
            try:
                controller.disconnect()
                logger.info("Disconnected from device.")
            except:
                pass


def main():
    parser = argparse.ArgumentParser(description="Set Feetech servo motors to their middle position")
    parser.add_argument("--motor_ids", type=str, default="1,2,3,4,5,6",
                       help="Comma-separated list of motor IDs (default: 1,2,3,4,5,6)")
    parser.add_argument("--port", type=str,
                       help="Serial port (e.g., /dev/ttyUSB0, COM3)")
    parser.add_argument("--auto_detect_port", action="store_true",
                       help="Auto-detect the serial port (deprecated, now default behavior)")
    parser.add_argument("--motor_model", type=str, default="sts3215",
                       help="Motor model (default: sts3215)")
    parser.add_argument("--baudrate", type=int, default=1000000,
                       help="Baudrate (default: 1000000)")
    parser.add_argument("--continuous", action="store_true",
                       help="Continuous mode for processing multiple robots")
    parser.add_argument("--single", action="store_true",
                       help="Process one robot and exit")
    
    args = parser.parse_args()
    
    # Parse motor IDs
    motor_ids = [int(id.strip()) for id in args.motor_ids.split(",")]
    
    # Determine port (auto-detect by default if no port specified)
    if args.port:
        port = args.port
    else:
        # Auto-detect port by default
        try:
            port = auto_detect_port()
            logger.info(f"Auto-detected port: {port}")
        except RuntimeError as e:
            logger.error(str(e))
            return
    
    if args.single or not args.continuous:
        # Single robot mode
        logger.info("Single robot mode - will process one robot and exit")
        logger.info(f"Motor IDs: {motor_ids}")
        logger.info(f"Port: {port}")
        logger.info(f"Motor model: {args.motor_model}")
        
        if process_single_robot(port, motor_ids, args.motor_model, args.baudrate):
            logger.info("\n✅ Successfully processed 1 robot")
        else:
            logger.error("\n❌ Failed to process robot")
    else:
        # Continuous mode for multiple robots
        logger.info("🔄 Continuous mode - Press SPACE to process next robot, 'q' to quit")
        logger.info(f"Motor IDs: {motor_ids}")
        logger.info(f"Motor model: {args.motor_model}")
        
        robot_count = 0
        
        try:
            while True:
                print(f"\n{'='*60}")
                print(f"Robots processed: {robot_count}")
                print("1. Connect a new robot via USB")
                print("2. Press SPACE when ready (or 'q' to quit)")
                print(f"{'='*60}")
                
                if not wait_for_keypress():
                    break
                
                print("\n🔍 Detecting robot...")
                
                # Auto-detect port for each robot
                try:
                    current_port = auto_detect_port()
                except RuntimeError as e:
                    logger.error(str(e))
                    continue
                
                if process_single_robot(current_port, motor_ids, args.motor_model, args.baudrate):
                    robot_count += 1
                    print(f"\n✅ Successfully processed robot #{robot_count}")
                else:
                    print("\n❌ Failed to process robot. Try again.")
                
                # Brief pause to allow USB disconnection
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        
        print(f"\n{'='*60}")
        print(f"🎉 Session complete! Total robots processed: {robot_count}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main() 