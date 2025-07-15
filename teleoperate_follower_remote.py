#!/usr/bin/env python3
"""
Follower-side teleoperation script using PubNub for internet communication.

This script:
1. Connects to 2 follower robots (>=9V) via USB
2. Subscribes to position data from PubNub
3. Applies received positions to follower robots with safety checks

Usage:
    python teleoperate_follower_remote.py
"""

import os
import logging

# Disable PubNub logging via environment variable
os.environ['PUBNUB_LOG_LEVEL'] = 'NONE'

# Configure logging BEFORE importing other modules
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Suppress verbose HTTP logs from various libraries
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)
logging.getLogger('httpx').setLevel(logging.ERROR)
logging.getLogger('httpcore').setLevel(logging.ERROR)
logging.getLogger('pubnub').setLevel(logging.WARNING)
# Disable all INFO logs from modules starting with 'http'
for name in logging.root.manager.loggerDict:
    if name.startswith('http'):
        logging.getLogger(name).setLevel(logging.ERROR)

import argparse
import json
import platform
import signal
import subprocess
import sys
import time
import threading
from typing import Dict, List, Optional

try:
    from pubnub.pnconfiguration import PNConfiguration
    from pubnub.pubnub import PubNub
    from pubnub.exceptions import PubNubException
    from pubnub.callbacks import SubscribeCallback
    from pubnub.enums import PNStatusCategory
except ImportError:
    print("PubNub not installed. Please install with: pip install pubnub")
    sys.exit(1)

try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    # Fallback if colorama not installed
    class Fore:
        RED = GREEN = YELLOW = CYAN = MAGENTA = ""
    class Style:
        RESET_ALL = BRIGHT = ""

# Import our modules
import pubnub_config
from teleoperate_multi_arms_standalone import SO101Controller, find_robot_ports, identify_robot_by_voltage


def setup_usb_permissions_linux(ports: List[str]) -> bool:
    """
    Attempt to set proper permissions for USB ports on Linux.
    Returns True if successful or not needed, False if manual intervention required.
    """
    if platform.system() != "Linux":
        return True  # Not Linux, no special permissions needed
        
    import subprocess
    import getpass
    
    needs_permission_fix = False
    for port in ports:
        # Check if we can access the port
        try:
            import serial
            test_port = serial.Serial(port, 9600)
            test_port.close()
        except serial.SerialException as e:
            if "Permission denied" in str(e) or "Errno 13" in str(e):
                needs_permission_fix = True
                break
    
    if not needs_permission_fix:
        return True
        
    logger.warning(f"{Fore.YELLOW}USB ports need permission fix on Linux{Style.RESET_ALL}")
    
    # Check if we're running with sudo
    if os.geteuid() == 0:
        # Running as root, can fix permissions directly
        for port in ports:
            try:
                subprocess.run(["chmod", "666", port], check=True)
                logger.info(f"{Fore.GREEN}✓ Fixed permissions for {port}{Style.RESET_ALL}")
            except subprocess.CalledProcessError:
                logger.error(f"Failed to set permissions for {port}")
                return False
        return True
    
    # Not running as root, provide options
    logger.info("\nTo fix USB permissions, you have several options:")
    logger.info(f"\n{Style.BRIGHT}Option 1: Use the provided setup script (recommended):{Style.RESET_ALL}")
    logger.info("  sudo ./setup_usb_permissions_linux.sh")
    
    logger.info(f"\n{Style.BRIGHT}Option 2: Run this script with sudo (temporary fix):{Style.RESET_ALL}")
    logger.info(f"  sudo python {sys.argv[0]}")
    
    logger.info(f"\n{Style.BRIGHT}Option 3: Add user to dialout group:{Style.RESET_ALL}")
    logger.info(f"  sudo usermod -a -G dialout {getpass.getuser()}")
    logger.info("  Then log out and back in")
    
    logger.info(f"\n{Style.BRIGHT}Option 4: Create udev rule manually:{Style.RESET_ALL}")
    logger.info("  See setup instructions below...")
    
    # Try to run chmod with sudo
    logger.info(f"\n{Fore.CYAN}Attempting to fix permissions automatically...{Style.RESET_ALL}")
    try:
        for port in ports:
            cmd = ["sudo", "-n", "chmod", "666", port]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"{Fore.GREEN}✓ Fixed permissions for {port}{Style.RESET_ALL}")
            else:
                # sudo requires password
                logger.info(f"\n{Fore.YELLOW}Manual permission fix required for {port}{Style.RESET_ALL}")
                logger.info(f"Run: sudo chmod 666 {port}")
                return False
    except Exception as e:
        logger.error(f"Error setting permissions: {e}")
        return False
        
    return True


def create_udev_rule_file():
    """Create a udev rule file content for USB serial devices."""
    content = """# USB Serial Device Rules for Robot Arms
# This file allows all users to access USB serial devices
# Created by teleoperate_follower_remote.py

# For FTDI USB Serial devices (common for robot controllers)
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", MODE="0666"

# For CH340/CH341 USB Serial devices
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0666"

# For CP210x USB Serial devices
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", MODE="0666"

# For Prolific USB Serial devices
SUBSYSTEM=="tty", ATTRS{idVendor}=="067b", MODE="0666"

# Generic rule for all USB serial devices (use with caution)
# SUBSYSTEM=="tty", SUBSYSTEMS=="usb", MODE="0666"
"""
    
    filename = "99-robot-usb-serial.rules"
    logger.info(f"\n{Style.BRIGHT}To create a permanent fix, save this as /etc/udev/rules.d/{filename}:{Style.RESET_ALL}")
    logger.info("-" * 60)
    print(content)
    logger.info("-" * 60)
    logger.info("\nThen run:")
    logger.info("  sudo cp 99-robot-usb-serial.rules /etc/udev/rules.d/")
    logger.info("  sudo udevadm control --reload-rules")
    logger.info("  sudo udevadm trigger")
    
    # Save to current directory for convenience
    try:
        with open(filename, 'w') as f:
            f.write(content)
        logger.info(f"\n{Fore.GREEN}✓ Created {filename} in current directory{Style.RESET_ALL}")
    except Exception as e:
        logger.warning(f"Could not create rule file: {e}")


# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) for graceful shutdown."""
    global shutdown_requested
    logger.info("\n\n⚠️  Shutdown requested. Cleaning up...")
    shutdown_requested = True


class PositionSmoother:
    """Smooth position changes to prevent jerky movements."""
    
    def __init__(self, smoothing_factor: float = 0.8):
        self.smoothing_factor = smoothing_factor
        self.current_positions = {}
        
    def smooth(self, motor_id: int, target_position: int) -> int:
        """Apply exponential smoothing to position changes."""
        if motor_id not in self.current_positions:
            self.current_positions[motor_id] = target_position
            return target_position
            
        current = self.current_positions[motor_id]
        smoothed = int(current * self.smoothing_factor + target_position * (1 - self.smoothing_factor))
        
        # Enforce maximum change limit
        change = abs(smoothed - current)
        if change > pubnub_config.MAX_POSITION_CHANGE:
            # Limit the change
            direction = 1 if smoothed > current else -1
            smoothed = current + (direction * pubnub_config.MAX_POSITION_CHANGE)
            
        self.current_positions[motor_id] = smoothed
        return smoothed


class TelemetryListener(SubscribeCallback):
    """Listen for telemetry data from leaders."""
    
    def __init__(self):
        self.latest_data = None
        self.last_sequence = 0
        self.received_count = 0
        self.dropped_count = 0
        self.last_receive_time = 0
        
    def status(self, pubnub, status):
        """Handle connection status changes."""
        if status.category == PNStatusCategory.PNConnectedCategory:
            logger.info(f"{Fore.GREEN}✓ Connected to PubNub channels{Style.RESET_ALL}")
        elif status.category == PNStatusCategory.PNReconnectedCategory:
            logger.info(f"{Fore.YELLOW}Reconnected to PubNub{Style.RESET_ALL}")
        elif status.category == PNStatusCategory.PNDisconnectedCategory:
            logger.warning(f"{Fore.RED}Disconnected from PubNub{Style.RESET_ALL}")
            
    def message(self, pubnub, message):
        """Handle incoming telemetry messages."""
        try:
            # Get the message data
            data = message.message
                
            if isinstance(data, dict) and data.get("type") == "telemetry":
                self.latest_data = data
                self.last_receive_time = time.time()
                self.received_count += 1
                
                # Check for dropped packets
                sequence = data.get("sequence", 0)
                if self.last_sequence > 0 and sequence > self.last_sequence + 1:
                    self.dropped_count += sequence - self.last_sequence - 1
                self.last_sequence = sequence
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")


class FollowerTeleop:
    """Main teleoperation class for follower side."""
    
    def __init__(self, motor_ids: List[int], baudrate: int = 1000000):
        self.motor_ids = motor_ids
        self.baudrate = baudrate
        self.followers: List[SO101Controller] = []
        self.running = False
        
        # Network components
        self.pubnub: Optional[PubNub] = None
        self.telemetry_listener = TelemetryListener()
        
        # Position smoothing
        self.smoothers = {}
        
        # Mapping (will be dynamic in future)
        self.mapping = {
            "Leader1": "Follower1",
            "Leader2": "Follower2"
        }
        
        # Performance tracking
        self.last_update_time = 0
        self.update_times = []
        self.latencies = []
        
    def setup_pubnub(self):
        """Initialize PubNub connection."""
        logger.info("Setting up PubNub connection...")
        
        pnconfig = PNConfiguration()
        pnconfig.subscribe_key = pubnub_config.SUBSCRIBE_KEY
        pnconfig.publish_key = pubnub_config.PUBLISH_KEY
        pnconfig.user_id = f"follower-{platform.node()}"
        pnconfig.ssl = True
        pnconfig.enable_subscribe = True
        # Disable PubNub's internal logging
        pnconfig.log_verbosity = False
        pnconfig.enable_logging = False
        
        self.pubnub = PubNub(pnconfig)
        self.pubnub.add_listener(self.telemetry_listener)
        
        # Subscribe to telemetry channel
        self.pubnub.subscribe().channels([pubnub_config.TELEMETRY_CHANNEL]).execute()
        
        logger.info(f"{Fore.GREEN}✓ PubNub connected as {pnconfig.user_id}{Style.RESET_ALL}")
        
    def auto_detect_followers(self) -> List[str]:
        """Find and identify follower robots."""
        ports = find_robot_ports()
        follower_ports = []
        
        logger.info(f"Found {len(ports)} serial ports")
        
        # Handle USB permissions on Linux
        if platform.system() == "Linux" and ports:
            if not setup_usb_permissions_linux(ports):
                logger.warning(f"\n{Fore.YELLOW}Could not automatically fix USB permissions{Style.RESET_ALL}")
                logger.info("You may need to run the commands shown above before continuing")
                
                # Ask if user wants to see udev rule
                try:
                    response = input(f"\n{Fore.CYAN}Would you like to create a udev rule file for permanent fix? (y/N): {Style.RESET_ALL}")
                    if response.lower() == 'y':
                        create_udev_rule_file()
                except KeyboardInterrupt:
                    pass
                
                # Give user time to fix permissions
                try:
                    input(f"\n{Fore.CYAN}Press Enter after fixing permissions to continue...{Style.RESET_ALL}")
                except KeyboardInterrupt:
                    raise RuntimeError("User cancelled")
        
        for port in ports:
            try:
                is_leader, voltage = identify_robot_by_voltage(port, self.motor_ids)
                if not is_leader:  # Followers have >=9V
                    follower_ports.append(port)
                    logger.info(f"{Fore.GREEN}✓ Follower robot found at {port} ({voltage:.1f}V){Style.RESET_ALL}")
            except Exception as e:
                logger.warning(f"Failed to identify {port}: {e}")
                
        if len(follower_ports) != 2:
            raise RuntimeError(f"Expected 2 follower robots, found {len(follower_ports)}")
            
        return follower_ports
        
    def connect_followers(self):
        """Connect to follower robots."""
        follower_ports = self.auto_detect_followers()
        
        self.followers = [
            SO101Controller(follower_ports[0], self.motor_ids, self.baudrate, "Follower1"),
            SO101Controller(follower_ports[1], self.motor_ids, self.baudrate, "Follower2")
        ]
        
        for follower in self.followers:
            follower.connect()
            follower.enable_torque()
            
            # Create position smoother for this follower
            self.smoothers[follower.robot_id] = PositionSmoother(pubnub_config.POSITION_SMOOTHING)
            
        logger.info(f"{Fore.GREEN}✓ Connected to {len(self.followers)} follower robots{Style.RESET_ALL}")
        
    def send_acknowledgment(self, sequence: int, timestamp: float):
        """Send acknowledgment back to leader."""
        try:
            ack_msg = {
                "type": "ack",
                "sequence": sequence,
                "timestamp": timestamp,
                "follower_id": f"follower-{platform.node()}"
            }
            self.pubnub.publish().channel(pubnub_config.STATUS_CHANNEL).message(ack_msg).sync()
        except:
            pass  # Don't fail on ack errors
            
    def send_status(self):
        """Send periodic status updates."""
        try:
            status_msg = {
                "type": "status",
                "timestamp": time.time(),
                "follower_id": f"follower-{platform.node()}",
                "motors_active": sum(len(f.motor_ids) for f in self.followers),
                "followers_connected": len(self.followers)
            }
            self.pubnub.publish().channel(pubnub_config.STATUS_CHANNEL).message(status_msg).sync()
        except:
            pass
            
    def apply_positions(self, telemetry_data: Dict):
        """Apply received positions to follower robots."""
        timestamp = telemetry_data.get("timestamp", 0)
        sequence = telemetry_data.get("sequence", 0)
        positions_data = telemetry_data.get("positions", {})
        
        # Calculate latency
        latency = (time.time() - timestamp) * 1000  # ms
        self.latencies.append(latency)
        if len(self.latencies) > 100:
            self.latencies.pop(0)
            
        # Safety check: reject if latency too high
        if latency > pubnub_config.MAX_LATENCY_MS:
            logger.warning(f"{Fore.RED}Rejecting data: latency {latency:.1f}ms > {pubnub_config.MAX_LATENCY_MS}ms{Style.RESET_ALL}")
            return
            
        # Send acknowledgment
        self.send_acknowledgment(sequence, timestamp)
        
        # Apply positions based on mapping
        for leader_id, leader_positions in positions_data.items():
            follower_id = self.mapping.get(leader_id)
            if not follower_id:
                continue
                
            # Find the corresponding follower
            follower = next((f for f in self.followers if f.robot_id == follower_id), None)
            if not follower:
                continue
                
            # Apply smoothing and send positions
            smoother = self.smoothers[follower_id]
            smoothed_positions = {}
            
            for motor_id_str, position in leader_positions.items():
                # Convert string motor ID back to int
                motor_id = int(motor_id_str)
                smoothed_positions[motor_id] = smoother.smooth(motor_id, position)
                
            follower.write_positions(smoothed_positions)
            
    def display_status(self):
        """Display current status and statistics."""
        # Clear screen and move cursor to top
        print("\033[2J\033[H", end="")
        
        print(f"{Style.BRIGHT}=== FOLLOWER TELEOPERATION ==={Style.RESET_ALL}")
        print(f"Connected Followers: {len(self.followers)}")
        print()
        
        # Current mapping
        print(f"{Style.BRIGHT}Current Mapping:{Style.RESET_ALL}")
        for leader, follower in self.mapping.items():
            print(f"  {leader} → {follower}")
        print()
        
        # Network stats
        print(f"{Style.BRIGHT}Network Statistics:{Style.RESET_ALL}")
        if self.latencies:
            avg_latency = sum(self.latencies) / len(self.latencies)
            max_latency = max(self.latencies)
            print(f"  Average Latency: {avg_latency:.1f}ms")
            print(f"  Max Latency:     {max_latency:.1f}ms")
        else:
            print(f"  Latency: No data yet")
            
        print(f"  Received:        {self.telemetry_listener.received_count}")
        print(f"  Dropped:         {self.telemetry_listener.dropped_count}")
        
        # Update rate
        if self.update_times:
            avg_interval = sum(self.update_times) / len(self.update_times)
            actual_fps = 1.0 / avg_interval if avg_interval > 0 else 0
            print(f"  Update Rate:     {actual_fps:.1f} Hz")
            
        # Connection status
        if self.telemetry_listener.last_receive_time > 0:
            age = time.time() - self.telemetry_listener.last_receive_time
            if age < 1:
                status = f"{Fore.GREEN}Connected{Style.RESET_ALL}"
            elif age < 5:
                status = f"{Fore.YELLOW}Slow{Style.RESET_ALL}"
            else:
                status = f"{Fore.RED}Disconnected{Style.RESET_ALL}"
            print(f"  Status:          {status} (last data {age:.1f}s ago)")
            
        print()
        print(f"{Fore.CYAN}Press Ctrl+C to stop{Style.RESET_ALL}")
        
    def teleoperation_loop(self):
        """Main loop processing received positions."""
        self.running = True
        
        # Start display thread
        display_thread = threading.Thread(target=self.display_loop, daemon=True)
        display_thread.start()
        
        # Start status thread
        status_thread = threading.Thread(target=self.status_loop, daemon=True)
        status_thread.start()
        
        logger.info("Starting follower teleoperation...")
        
        try:
            while self.running and not shutdown_requested:
                # Check for new telemetry data
                if self.telemetry_listener.latest_data:
                    # Process the latest data
                    self.apply_positions(self.telemetry_listener.latest_data)
                    
                    # Track update rate
                    now = time.time()
                    if self.last_update_time > 0:
                        self.update_times.append(now - self.last_update_time)
                        if len(self.update_times) > 100:
                            self.update_times.pop(0)
                    self.last_update_time = now
                    
                    # Clear to prevent reprocessing
                    self.telemetry_listener.latest_data = None
                    
                # Small sleep to prevent CPU spinning
                time.sleep(0.001)
                
        except KeyboardInterrupt:
            logger.info("\nStopping teleoperation...")
        finally:
            self.running = False
            
    def display_loop(self):
        """Separate thread for updating display."""
        while self.running and not shutdown_requested:
            self.display_status()
            time.sleep(0.5)  # Update display at 2Hz
            
    def status_loop(self):
        """Send periodic status updates."""
        while self.running and not shutdown_requested:
            self.send_status()
            time.sleep(2)  # Send status every 2 seconds
            
    def shutdown(self):
        """Clean shutdown."""
        self.running = False
        
        # Unsubscribe from channels
        if self.pubnub:
            self.pubnub.unsubscribe_all()
            
        # Disable torque and disconnect robots
        logger.info("Disabling torque on all follower robots...")
        for follower in self.followers:
            try:
                if follower.connected:
                    follower.disable_torque()
            except Exception as e:
                logger.warning(f"Failed to disable torque on {follower.robot_id}: {e}")
                
        logger.info("Disconnecting robots...")
        for follower in self.followers:
            try:
                follower.disconnect()
            except Exception as e:
                logger.warning(f"Failed to disconnect {follower.robot_id}: {e}")
                
        logger.info("Shutdown complete")


def main():
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(description="Follower-side teleoperation via PubNub")
    parser.add_argument("--motor_ids", type=str, default="1,2,3,4,5,6",
                       help="Comma-separated motor IDs")
    parser.add_argument("--baudrate", type=int, default=1000000,
                       help="Serial baudrate")
    
    args = parser.parse_args()
    
    # Parse motor IDs
    motor_ids = [int(id.strip()) for id in args.motor_ids.split(",")]
    
    # Create and run teleoperation
    teleop = FollowerTeleop(motor_ids, args.baudrate)
    
    try:
        # Setup
        teleop.setup_pubnub()
        teleop.connect_followers()
        
        # Run main loop
        teleop.teleoperation_loop()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    finally:
        teleop.shutdown()
        
    return 0


if __name__ == "__main__":
    sys.exit(main()) 