#!/usr/bin/env python3
"""
Standalone script to set Feetech servo motors to their middle position.

This script follows the exact logic from LeRobot's set_middle_position.py,
implementing the same algorithm in a standalone fashion.

The key steps are:
1. Disable torque
2. Detect voltage and set Phase accordingly:
   - Leader arm (5V): Phase=76
   - Follower arm (12V): Phase=12
3. Set Lock=0
4. Set operating mode to position mode
5. Reset calibration (homing offset to 0, limits to full range)
6. Read current positions
7. Calculate homing offsets (current_position - 2048)
8. Write homing offsets

Example usage:
```shell
python set_middle_position_standalone.py
```
"""

import argparse
import logging
import platform
import sys
import time
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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


def encode_sign_magnitude(value: int, sign_bit_index: int) -> int:
    """
    Encode a signed integer using sign-magnitude representation.
    Copied from LeRobot's encoding_utils.py
    """
    max_magnitude = (1 << sign_bit_index) - 1
    magnitude = abs(value)
    if magnitude > max_magnitude:
        raise ValueError(f"Magnitude {magnitude} exceeds {max_magnitude} (max for {sign_bit_index=})")

    direction_bit = 1 if value < 0 else 0
    return (direction_bit << sign_bit_index) | magnitude


class FeetechBus:
    """
    Simplified Feetech motor bus that implements only what's needed for calibration.
    This follows the exact logic from LeRobot's FeetechMotorsBus.
    """
    
    # Feetech register addresses
    TORQUE_ENABLE = 40
    LOCK = 55
    PHASE = 18
    OPERATING_MODE = 33
    HOMING_OFFSET = 31
    MIN_POSITION_LIMIT = 9
    MAX_POSITION_LIMIT = 11
    PRESENT_POSITION = 56
    RESPONSE_STATUS_LEVEL = 8
    RETURN_DELAY_TIME = 7
    PRESENT_VOLTAGE = 62
    
    # Model resolutions
    RESOLUTIONS = {
        "sts3215": 4096,
        "sts3250": 4096,
        "sm8512bl": 65536,
        "scs0009": 1024,
    }
    
    def __init__(self, port: str, motor_ids: List[int], baudrate: int = 1000000,
                 motor_model: str = "sts3215"):
        self.port = port
        self.motor_ids = motor_ids
        self.baudrate = baudrate
        self.motor_model = motor_model
        self.resolution = self.RESOLUTIONS.get(motor_model, 4096)
        
        try:
            import scservo_sdk as scs  # type: ignore
            self.scs = scs
        except ImportError:
            raise RuntimeError("scservo_sdk not installed. Please install from Feetech SDK")
        
        self.port_handler: Any = None
        self.packet_handler: Any = None
        
    def connect(self) -> None:
        """Connect to the motor bus."""
        self.port_handler = self.scs.PortHandler(self.port)
        self.packet_handler = self.scs.PacketHandler(0)  # Protocol 0 for Feetech
        
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
                        raise RuntimeError(f"Failed to ping motor {motor_id}")
                else:
                    raise RuntimeError(f"Unexpected ping result: {ping_result}")
            except Exception as e:
                raise RuntimeError(f"Failed to ping motor {motor_id}: {str(e)}")
        
        logger.info(f"Connected to Feetech motors: {self.motor_ids}")
        
    def disconnect(self) -> None:
        """Disconnect from the motor bus."""
        if self.port_handler:
            self.port_handler.closePort()
            logger.info("Disconnected from motors.")
    
    def write(self, data_name: str, motor_id: int, value: int) -> None:
        """Write a value to a motor register. This follows LeRobot's bus.write() logic."""
        if self.packet_handler is None or self.port_handler is None:
            raise RuntimeError("Not connected to motors")
            
        # Get register address and size
        if data_name == "Torque_Enable":
            addr, size = self.TORQUE_ENABLE, 1
        elif data_name == "Lock":
            addr, size = self.LOCK, 1
        elif data_name == "Phase":
            addr, size = self.PHASE, 1
        elif data_name == "Operating_Mode":
            addr, size = self.OPERATING_MODE, 1
        elif data_name == "Homing_Offset":
            addr, size = self.HOMING_OFFSET, 2
            # Apply sign-magnitude encoding for Homing_Offset (11-bit sign)
            if value < 0:
                value = encode_sign_magnitude(value, 11)
        elif data_name == "Min_Position_Limit":
            addr, size = self.MIN_POSITION_LIMIT, 2
        elif data_name == "Max_Position_Limit":
            addr, size = self.MAX_POSITION_LIMIT, 2
        elif data_name == "Return_Delay_Time":
            addr, size = self.RETURN_DELAY_TIME, 1
        elif data_name == "Response_Status_Level":
            addr, size = self.RESPONSE_STATUS_LEVEL, 1
        else:
            raise ValueError(f"Unknown data_name: {data_name}")
        
        # Write the value
        if size == 1:
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, motor_id, addr, value)
        else:  # size == 2
            result, error = self.packet_handler.write2ByteTxRx(
                self.port_handler, motor_id, addr, value)
        
        if result != self.scs.COMM_SUCCESS:
            logger.warning(f"Failed to write {data_name} to motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")
    
    def sync_read(self, data_name: str, motor_ids: Optional[List[int]] = None) -> Dict[int, int]:
        """Read values from multiple motors. This follows LeRobot's sync_read logic."""
        if self.packet_handler is None or self.port_handler is None:
            raise RuntimeError("Not connected to motors")
            
        if motor_ids is None:
            motor_ids = self.motor_ids
        
        if data_name != "Present_Position":
            raise ValueError(f"sync_read only implemented for Present_Position, not {data_name}")
        
        positions = {}
        for motor_id in motor_ids:
            try:
                result = self.packet_handler.read2ByteTxRx(
                    self.port_handler, motor_id, self.PRESENT_POSITION)
                
                # Handle different return formats
                if isinstance(result, tuple) and len(result) >= 2:
                    if len(result) >= 3:
                        position, comm_result, error = result[:3]
                    else:
                        position, comm_result = result[:2]
                    
                    if comm_result == self.scs.COMM_SUCCESS:
                        positions[motor_id] = position
                    else:
                        logger.warning(f"Failed to read position from motor {motor_id}")
                else:
                    logger.warning(f"Unexpected read result from motor {motor_id}: {result}")
            except Exception as e:
                logger.warning(f"Exception reading motor {motor_id}: {e}")
        
        return positions
    
    def disable_torque(self) -> None:
        """Disable torque on all motors. Follows LeRobot's disable_torque logic."""
        for motor_id in self.motor_ids:
            self.write("Torque_Enable", motor_id, 0)
            self.write("Lock", motor_id, 0)
    
    def configure_motors(self) -> None:
        """Configure motors for calibration. Follows LeRobot's configure_motors logic."""
        for motor_id in self.motor_ids:
            # Set Return_Delay_Time to 0 (minimum 2µs delay)
            self.write("Return_Delay_Time", motor_id, 0)
            # Set Response_Status_Level to 2 (return status packet for all commands)
            self.write("Response_Status_Level", motor_id, 2)
    
    def read_voltage(self) -> float:
        """Read voltage from the first motor."""
        if self.packet_handler is None or self.port_handler is None:
            raise RuntimeError("Not connected to motors")
            
        motor_id = self.motor_ids[0]  # Read from first motor
        try:
            result = self.packet_handler.read1ByteTxRx(
                self.port_handler, motor_id, self.PRESENT_VOLTAGE)
            
            # Handle different return formats
            if isinstance(result, tuple) and len(result) >= 2:
                if len(result) >= 3:
                    raw_voltage, comm_result, error = result[:3]
                else:
                    raw_voltage, comm_result = result[:2]
                
                if comm_result == self.scs.COMM_SUCCESS:
                    # Feetech motors report voltage in units of 0.1V
                    return raw_voltage / 10.0
                else:
                    raise RuntimeError(f"Failed to read voltage: {self.packet_handler.getTxRxResult(comm_result)}")
            else:
                raise RuntimeError(f"Unexpected read result: {result}")
        except Exception as e:
            raise RuntimeError(f"Failed to read voltage from motor {motor_id}: {str(e)}")
    
    def reset_calibration(self, motors: Optional[List[int]] = None) -> None:
        """
        Reset calibration to factory defaults.
        This follows LeRobot's MotorsBus.reset_calibration() exactly.
        """
        if motors is None:
            motors = self.motor_ids
        
        logger.info("Resetting calibration...")
        
        for motor_id in motors:
            max_res = self.resolution - 1
            self.write("Homing_Offset", motor_id, 0)
            self.write("Min_Position_Limit", motor_id, 0)
            self.write("Max_Position_Limit", motor_id, max_res)
    
    def _get_half_turn_homings(self, positions: Dict[int, int]) -> Dict[int, int]:
        """
        Calculate homing offsets. This follows LeRobot's Feetech-specific implementation.
        
        On Feetech Motors: Present_Position = Actual_Position - Homing_Offset
        To make position read as half of resolution (e.g., 2048):
        Homing_Offset = Actual_Position - (resolution / 2)
        """
        half_turn_homings = {}
        max_res = self.resolution - 1
        
        for motor_id, pos in positions.items():
            half_turn_homings[motor_id] = pos - int(max_res / 2)
        
        return half_turn_homings
    
    def set_half_turn_homings(self) -> Dict[int, int]:
        """
        Set half-turn homings. This follows LeRobot's MotorsBus.set_half_turn_homings() exactly.
        """
        # Step 1: Reset calibration
        self.reset_calibration()
        
        # Step 2: Read current positions
        actual_positions = self.sync_read("Present_Position")
        
        # Step 3: Calculate homing offsets
        homing_offsets = self._get_half_turn_homings(actual_positions)
        
        # Step 4: Write homing offsets
        # Note: Feetech motors may not return status packets for EEPROM writes
        for motor_id, offset in homing_offsets.items():
            self.write("Homing_Offset", motor_id, offset)
            # Add small delay after EEPROM write
            time.sleep(0.01)
        
        return homing_offsets


def set_middle_position(bus: FeetechBus) -> None:
    """
    Set servos to their middle position by configuring homing offsets.
    This follows the exact logic from LeRobot's set_middle_position.py.
    """
    logger.info(f"\nSetting middle position for motors: {bus.motor_ids}")
    
    # Detect voltage to determine if leader (5V) or follower (12V)
    try:
        voltage = bus.read_voltage()
        is_leader = 4.5 <= voltage <= 5.5  # Leader is ~5V
        robot_type = "LEADER" if is_leader else "FOLLOWER"
        phase_value = 76 if is_leader else 12
        
        logger.info(f"Detected {robot_type} robot (voltage: {voltage:.1f}V)")
        logger.info(f"Will set Phase={phase_value} for {robot_type} robot")
    except Exception as e:
        logger.warning(f"Failed to detect voltage: {e}")
        logger.warning("Defaulting to Phase=76 (leader)")
        phase_value = 76
    
    # Disable torque to allow manual positioning
    bus.disable_torque()
    
    # Set Phase and Lock to 0 for all servos
    logger.info(f"Setting Phase to {phase_value} and Lock to 0 for all servos...")
    for motor_id in bus.motor_ids:
        bus.write("Phase", motor_id, phase_value)
        bus.write("Lock", motor_id, 0)
        logger.debug(f"Set Phase={phase_value} and Lock=0 for motor: {motor_id}")
    
    # Set operating mode to position mode (0)
    for motor_id in bus.motor_ids:
        bus.write("Operating_Mode", motor_id, 0)  # Position mode
    
    input("\nMove the device to the desired middle position and press ENTER...")
    
    # Set half-turn homings (this makes current position the middle)
    logger.info("Setting homing offsets...")
    logger.info("Note: Warnings about 'no status packet' are normal for EEPROM writes on Feetech motors.")
    homing_offsets = bus.set_half_turn_homings()
    
    logger.info("\nHoming offsets set:")
    for motor_id, offset in homing_offsets.items():
        logger.info(f"  Motor {motor_id}: {offset}")
    
    logger.info("\n✓ Middle position set successfully!")
    logger.info("The current position is now the middle point for all servos.")
    logger.info(f"Phase (Setting byte) has been set to {phase_value} and Lock to 0 for all servos.")
    logger.info("\nIMPORTANT: Power cycle the motors for the calibration to take effect!")
    logger.info("After power cycling, motors will read ~2048 at their calibrated position.")


def main():
    parser = argparse.ArgumentParser(description="Set Feetech servo motors to their middle position")
    parser.add_argument("--motor_ids", type=str, default="1,2,3,4,5,6,7,8",
                       help="Comma-separated list of motor IDs (default: 1,2,3,4,5,6,7,8)")
    parser.add_argument("--port", type=str,
                       help="Serial port (e.g., /dev/ttyUSB0, COM3)")
    parser.add_argument("--motor_model", type=str, default="sts3215",
                       help="Motor model (default: sts3215)")
    parser.add_argument("--baudrate", type=int, default=1000000,
                       help="Baudrate (default: 1000000)")
    
    args = parser.parse_args()
    
    # Parse motor IDs
    motor_ids = [int(id.strip()) for id in args.motor_ids.split(",")]
    
    # Determine port
    if args.port:
        port = args.port
    else:
        try:
            port = auto_detect_port()
        except RuntimeError as e:
            logger.error(str(e))
            return
    
    # Create bus instance
    bus = FeetechBus(port, motor_ids, args.baudrate, args.motor_model)
    
    try:
        # Connect to motors
        bus.connect()
        
        # Configure motors for calibration
        bus.configure_motors()

        # Set middle position
        set_middle_position(bus)
        
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Disconnect
        if bus:
            bus.disconnect()


if __name__ == "__main__":
    main() 