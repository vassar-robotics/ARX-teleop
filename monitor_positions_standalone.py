#!/usr/bin/env python3
"""
Standalone script to continuously monitor and display motor positions.

This script connects to Feetech servo motors and displays their positions in real-time,
useful for debugging and monitoring motor states.

Requirements:
- pyserial
- scservo_sdk (for Feetech motors)

Example usage:
```shell
# Basic usage (auto-detect port, motor IDs 1-6):
python monitor_positions_standalone.py

# Custom motor IDs:
python monitor_positions_standalone.py --motor_ids=1,2,3,4

# Specify port manually:
python monitor_positions_standalone.py --port=/dev/ttyUSB0

# Custom refresh rate:
python monitor_positions_standalone.py --fps=10
```
"""

import argparse
import logging
import platform
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
        logger.info(f"Multiple ports detected: {ports}")
        logger.info("Using the first port. To use a different port, specify it with --port")
        return ports[0]


def move_cursor_up(lines: int) -> None:
    """Move terminal cursor up by specified number of lines."""
    print(f"\033[{lines}A", end="")


def clear_line() -> None:
    """Clear the current line."""
    print("\033[2K", end="")


def busy_wait(duration: float) -> None:
    """Busy wait for the specified duration in seconds."""
    start_time = time.perf_counter()
    while time.perf_counter() - start_time < duration:
        pass


class MotorMonitor:
    """Monitor for Feetech motors."""
    
    # Feetech register addresses
    PRESENT_POSITION = 56
    PRESENT_VOLTAGE = 62
    PRESENT_TEMPERATURE = 63
    PRESENT_LOAD = 60
    
    def __init__(self, port: str, motor_ids: List[int], baudrate: int = 1000000):
        self.port = port
        self.motor_ids = motor_ids
        self.baudrate = baudrate
        self.connected = False
        self.resolution = 4096  # STS3215 has 4096 resolution
        
        try:
            import scservo_sdk as scs  # type: ignore
            self.scs = scs
        except ImportError:
            raise RuntimeError("scservo_sdk not installed. Please install from Feetech SDK")
            
        self.port_handler: Any = None
        self.packet_handler: Any = None
        
    def connect(self) -> None:
        """Connect to the motors."""
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
                if len(ping_result) >= 3:
                    model_number, result, error = ping_result
                elif len(ping_result) == 2:
                    model_number, result = ping_result
                    error = 0
                else:
                    raise RuntimeError(f"Unexpected ping result format: {ping_result}")
                
                if result != self.scs.COMM_SUCCESS:
                    raise RuntimeError(f"Failed to ping motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")
            except Exception as e:
                raise RuntimeError(f"Failed to ping motor {motor_id}: {str(e)}")
                
        self.connected = True
        logger.info(f"Connected to motors: {self.motor_ids} on {self.port}")
        
    def disconnect(self) -> None:
        """Disconnect from the motors."""
        if self.port_handler:
            self.port_handler.closePort()
        self.connected = False
        
    def read_positions(self) -> Dict[int, int]:
        """Read current positions from all motors."""
        positions = {}
        for motor_id in self.motor_ids:
            position, result, error = self.packet_handler.read2ByteTxRx(
                self.port_handler, motor_id, self.PRESENT_POSITION)
            if result == self.scs.COMM_SUCCESS:
                positions[motor_id] = position
            else:
                positions[motor_id] = -1  # Error value
        return positions
        
    def read_voltage(self, motor_id: int) -> float:
        """Read voltage from a specific motor."""
        raw_voltage, result, error = self.packet_handler.read1ByteTxRx(
            self.port_handler, motor_id, self.PRESENT_VOLTAGE)
        
        if result == self.scs.COMM_SUCCESS:
            return raw_voltage / 10.0  # Convert to volts
        else:
            return -1.0
            
    def read_temperature(self, motor_id: int) -> int:
        """Read temperature from a specific motor."""
        temp, result, error = self.packet_handler.read1ByteTxRx(
            self.port_handler, motor_id, self.PRESENT_TEMPERATURE)
        
        if result == self.scs.COMM_SUCCESS:
            return temp
        else:
            return -1
            
    def read_load(self, motor_id: int) -> int:
        """Read load from a specific motor."""
        load, result, error = self.packet_handler.read2ByteTxRx(
            self.port_handler, motor_id, self.PRESENT_LOAD)
        
        if result == self.scs.COMM_SUCCESS:
            return load
        else:
            return -1


def monitor_loop(monitor: MotorMonitor, fps: int = 30, show_extra: bool = False) -> None:
    """Main monitoring loop."""
    logger.info("\n🔍 Starting position monitoring...")
    logger.info("Press Ctrl+C to stop\n")
    
    # Wait a moment before starting
    time.sleep(0.5)
    
    # Read initial voltage to determine robot type
    voltage = monitor.read_voltage(monitor.motor_ids[0])
    is_leader = 4.5 <= voltage <= 5.5
    robot_type = "LEADER (5V)" if is_leader else "FOLLOWER (12V)"
    
    first_iteration = True
    
    while True:
        loop_start = time.perf_counter()
        
        # Read positions
        positions = monitor.read_positions()
        
        if not positions:
            logger.warning("Failed to read any positions")
            continue
        
        # Prepare display
        if not first_iteration:
            # Move cursor up to overwrite previous display
            lines_to_move = len(monitor.motor_ids) + 7
            if show_extra:
                lines_to_move += len(monitor.motor_ids) + 3
            move_cursor_up(lines_to_move)
        else:
            first_iteration = False
        
        # Display header
        print("\n" + "=" * 70)
        print(f"🤖 Robot Type: {robot_type} | Port: {monitor.port}")
        print("=" * 70)
        print(f"{'Motor ID':<10} | {'Position':>10} | {'Degrees':>10} | {'Percent':>8} | {'Status':<10}")
        print("-" * 70)
        
        # Display positions
        for motor_id in sorted(monitor.motor_ids):
            position = positions.get(motor_id, -1)
            
            if position >= 0:
                # Calculate degrees (0-360) and percentage
                degrees = (position / monitor.resolution) * 360
                percent = (position / (monitor.resolution - 1)) * 100
                status = "OK"
                
                # Determine if at limits
                if position <= 10:
                    status = "MIN LIMIT"
                elif position >= monitor.resolution - 10:
                    status = "MAX LIMIT"
                
                print(f"{motor_id:<10} | {position:>10} | {degrees:>9.1f}° | {percent:>7.1f}% | {status:<10}")
            else:
                print(f"{motor_id:<10} | {'ERROR':>10} | {'---':>10} | {'---':>8} | {'COMM ERR':<10}")
        
        # Show extra info if requested
        if show_extra:
            print("\n" + "-" * 70)
            print(f"{'Motor ID':<10} | {'Voltage':>10} | {'Temp':>10} | {'Load':>10}")
            print("-" * 70)
            
            for motor_id in sorted(monitor.motor_ids):
                voltage = monitor.read_voltage(motor_id)
                temp = monitor.read_temperature(motor_id)
                load = monitor.read_load(motor_id)
                
                voltage_str = f"{voltage:.1f}V" if voltage > 0 else "ERROR"
                temp_str = f"{temp}°C" if temp > 0 else "ERROR"
                load_str = str(load) if load >= 0 else "ERROR"
                
                print(f"{motor_id:<10} | {voltage_str:>10} | {temp_str:>10} | {load_str:>10}")
        
        # Calculate timing
        dt_s = time.perf_counter() - loop_start
        target_loop_time = 1 / fps
        if dt_s < target_loop_time:
            busy_wait(target_loop_time - dt_s)
        
        loop_time = time.perf_counter() - loop_start
        print(f"\n📊 Update rate: {1/loop_time:.1f} Hz (target: {fps} Hz)")


def main():
    parser = argparse.ArgumentParser(description="Monitor Feetech motor positions in real-time")
    parser.add_argument("--motor_ids", type=str, default="1,2,3,4,5,6",
                       help="Comma-separated list of motor IDs (default: 1,2,3,4,5,6)")
    parser.add_argument("--port", type=str,
                       help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--baudrate", type=int, default=1000000,
                       help="Baudrate (default: 1000000)")
    parser.add_argument("--fps", type=int, default=30,
                       help="Target refresh rate in Hz (default: 30)")
    parser.add_argument("--extra", action="store_true",
                       help="Show extra info (voltage, temperature, load)")
    
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
    
    # Create monitor
    monitor = MotorMonitor(port, motor_ids, args.baudrate)
    
    try:
        # Connect
        monitor.connect()
        
        # Run monitoring loop
        monitor_loop(monitor, args.fps, args.extra)
        
    except KeyboardInterrupt:
        print("\n\n✋ Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Error during monitoring: {e}")
        raise
    finally:
        # Always disconnect properly
        logger.info("Disconnecting...")
        try:
            monitor.disconnect()
        except:
            pass
        logger.info("Monitor disconnected.")


if __name__ == "__main__":
    main() 