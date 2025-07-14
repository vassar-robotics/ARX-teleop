#!/usr/bin/env python3
"""
Helper to set servos to their middle position without generating calibration files.

This script connects to a robot or teleoperator, disables torque, and sets the homing
offsets so that the current position becomes the middle point of the servo's range.

Example:

```shell
# Default usage (auto-detects port, uses so101_follower robot, continuous mode):
python set_middle_position.py

# Process a single robot and exit:
python set_middle_position.py --single

# For a different robot type:
python set_middle_position.py --robot.type=koch_follower

# For a teleoperator:
python set_middle_position.py --teleop.type=so100_leader
```
"""

import logging
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from pprint import pformat

import draccus

from lerobot.common.cameras.opencv.configuration_opencv import OpenCVCameraConfig  # noqa: F401
from lerobot.common.cameras.realsense.configuration_realsense import RealSenseCameraConfig  # noqa: F401
from lerobot.common.robots import (  # noqa: F401
    Robot,
    RobotConfig,
    koch_follower,
    lekiwi,
    make_robot_from_config,
    so100_follower,
    so101_follower,
)
from lerobot.common.teleoperators import (  # noqa: F401
    Teleoperator,
    TeleoperatorConfig,
    koch_leader,
    make_teleoperator_from_config,
    so100_leader,
    so101_leader,
)
from lerobot.common.utils.utils import init_logging


def find_robot_ports():
    """
    Find USB serial ports that are likely to be robot/motor controllers.
    
    Returns:
        list: List of port names that match common robot port patterns
    """
    try:
        from serial.tools import list_ports
    except ImportError:
        logging.error("pyserial not installed. Cannot auto-detect ports.")
        return []
    
    robot_ports = []
    
    if platform.system() == "Darwin":  # macOS
        # On macOS, robot ports typically show up as /dev/tty.usbmodem* or /dev/tty.usbserial*
        for port in list_ports.comports():
            if "usbmodem" in port.device or "usbserial" in port.device:
                robot_ports.append(port.device)
    elif platform.system() == "Linux":
        # On Linux, robot ports typically show up as /dev/ttyUSB* or /dev/ttyACM*
        for port in list_ports.comports():
            if "ttyUSB" in port.device or "ttyACM" in port.device:
                robot_ports.append(port.device)
    elif platform.system() == "Windows":
        # On Windows, any COM port could be a robot
        for port in list_ports.comports():
            if "COM" in port.device:
                robot_ports.append(port.device)
    
    return robot_ports


def auto_detect_port():
    """
    Automatically detect a single robot port.
    
    Returns:
        str: The detected port name
        
    Raises:
        RuntimeError: If no ports or multiple ports are found
    """
    ports = find_robot_ports()
    
    if len(ports) == 0:
        raise RuntimeError(
            "No robot ports detected. Please ensure your device is connected via USB."
        )
    elif len(ports) == 1:
        logging.info(f"Auto-detected port: {ports[0]}")
        return ports[0]
    else:
        raise RuntimeError(
            f"Multiple potential robot ports detected: {ports}\n"
            "Please disconnect all but one robot."
        )


def wait_for_keypress():
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


@dataclass
class SetMiddlePositionConfig:
    # Default to so101_follower robot with auto-detected port
    robot: RobotConfig | None = field(default_factory=lambda: so101_follower.SO101FollowerConfig(port=None))
    teleop: TeleoperatorConfig | None = None
    single: bool = False  # If True, process one robot and exit
    
    # Don't serialize robot/teleop configs in post_init
    _device_template: RobotConfig | TeleoperatorConfig | None = field(init=False, default=None)

    def __post_init__(self):
        # If teleop is specified, clear the default robot
        if self.teleop is not None:
            self.robot = None
            
        if bool(self.teleop) == bool(self.robot):
            raise ValueError("Choose either a teleop or a robot.")

        # Store a template of the device config for creating new instances
        self._device_template = self.robot if self.robot else self.teleop


def set_middle_position(device):
    """
    Set servos to their middle position by configuring homing offsets.
    
    This function:
    1. Disables torque on all motors
    2. Reads current positions
    3. Sets homing offsets so current positions become the middle point
    
    Args:
        device: A Robot or Teleoperator instance
    """
    logging.info(f"\nSetting middle position for {device}")
    
    # Access the motor bus
    if hasattr(device, 'bus'):
        bus = device.bus
    else:
        # For some robots/teleoperators, the bus might be accessed differently
        logging.error(f"Cannot access motor bus for {device}")
        return
    
    # Disable torque to allow manual positioning
    bus.disable_torque()
    
    # Set Phase (Setting byte) to 76 and Lock to 0 for all servos
    logging.info("Setting Phase to 76 and Lock to 0 for all servos...")
    try:
        for motor in bus.motors:
            # Set Phase (address 18, Setting byte) to 76
            bus.write("Phase", motor, 76)
            # Set Lock (address 55) to 0
            bus.write("Lock", motor, 0)
            logging.debug(f"Set Phase=76 and Lock=0 for motor: {motor}")
    except Exception as e:
        logging.warning(f"Could not set Phase/Lock parameters: {e}")
    
    # For robots with operating mode settings (like position mode)
    if hasattr(bus, 'write') and hasattr(bus, 'motors'):
        for motor in bus.motors:
            try:
                # Try to set position mode if applicable
                from lerobot.common.motors.dynamixel.dynamixel import OperatingMode as DynamixelOperatingMode
                from lerobot.common.motors.feetech.feetech import OperatingMode as FeetechOperatingMode
                
                # Determine which operating mode to use based on bus type
                if hasattr(bus, 'model_ctrl_table'):
                    if 'dynamixel' in bus.__class__.__module__:
                        if motor != 'gripper':
                            bus.write("Operating_Mode", motor, DynamixelOperatingMode.EXTENDED_POSITION.value)
                        else:
                            bus.write("Operating_Mode", motor, DynamixelOperatingMode.CURRENT_POSITION.value)
                    else:
                        bus.write("Operating_Mode", motor, FeetechOperatingMode.POSITION.value)
            except Exception as e:
                logging.debug(f"Could not set operating mode for {motor}: {e}")
    
    input("\nMove the device to the desired middle position and press ENTER...")
    
    # Set half-turn homings (this makes current position the middle)
    logging.info("Setting homing offsets...")
    homing_offsets = bus.set_half_turn_homings()
    
    logging.info("\nHoming offsets set:")
    for motor, offset in homing_offsets.items():
        logging.info(f"  {motor}: {offset}")
    
    logging.info("\n✓ Middle position set successfully!")
    logging.info("The current position is now the middle point for all servos.")
    logging.info("Phase (Setting byte) has been set to 76 and Lock to 0 for all servos.")


def process_single_robot(cfg: SetMiddlePositionConfig):
    """Process a single robot by detecting port and setting middle position."""
    if cfg._device_template is None:
        logging.error("No device template configured")
        return False
        
    # Create a new device config with auto-detected port
    device_config = type(cfg._device_template)(
        **{k: v for k, v in asdict(cfg._device_template).items() if k != 'port'},
        port=None
    )
    
    # Auto-detect port
    try:
        device_config.port = auto_detect_port()
    except RuntimeError as e:
        logging.error(str(e))
        return False
    
    # Create device instance
    if isinstance(device_config, RobotConfig):
        device = make_robot_from_config(device_config)
    elif isinstance(device_config, TeleoperatorConfig):
        device = make_teleoperator_from_config(device_config)
    
    # Connect and process
    try:
        device.connect(calibrate=False)
        set_middle_position(device)
        return True
    except Exception as e:
        logging.error(f"Error processing robot: {e}")
        return False
    finally:
        try:
            device.disconnect()
            logging.info("Disconnected from device.")
        except:
            pass


@draccus.wrap()
def main(cfg: SetMiddlePositionConfig):
    init_logging()
    
    if cfg.single:
        # Single robot mode
        logging.info("Single robot mode - will process one robot and exit")
        logging.info("Configuration:")
        logging.info(pformat({k: v for k, v in asdict(cfg).items() if not k.startswith('_')}))
        
        if process_single_robot(cfg):
            logging.info("\n✅ Successfully processed 1 robot")
        else:
            logging.error("\n❌ Failed to process robot")
    else:
        # Continuous mode for multiple robots
        logging.info("🔄 Continuous mode - Press SPACE to process next robot, 'q' to quit")
        logging.info(f"Device type: {cfg._device_template.__class__.__name__}")
        
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
                
                if process_single_robot(cfg):
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