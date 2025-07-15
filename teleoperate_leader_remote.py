#!/usr/bin/env python3
"""
Leader-side teleoperation script using PubNub for internet communication.

This script:
1. Connects to 2 leader robots (<9V) via USB
2. Reads their positions at high frequency
3. Publishes position data to PubNub for follower robots

Usage:
    python teleoperate_leader_remote.py
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

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) for graceful shutdown."""
    global shutdown_requested
    logger.info("\n\n⚠️  Shutdown requested. Cleaning up...")
    shutdown_requested = True


class NetworkMonitor:
    """Monitor network statistics and latency."""
    
    def __init__(self):
        self.sent_count = 0
        self.ack_count = 0
        self.last_sent_time = {}
        self.latencies = []
        self.max_latency_samples = 100
        
    def message_sent(self, sequence: int):
        """Record when a message was sent."""
        self.sent_count += 1
        self.last_sent_time[sequence] = time.time()
        
    def message_acknowledged(self, sequence: int, timestamp: float):
        """Calculate latency when acknowledgment received."""
        if sequence in self.last_sent_time:
            latency = (time.time() - self.last_sent_time[sequence]) * 1000  # ms
            self.latencies.append(latency)
            if len(self.latencies) > self.max_latency_samples:
                self.latencies.pop(0)
            self.ack_count += 1
            del self.last_sent_time[sequence]
            return latency
        return None
        
    def get_stats(self) -> Dict:
        """Get current network statistics."""
        if not self.latencies:
            return {
                "avg_latency": 0, 
                "max_latency": 0, 
                "packet_loss": 0,
                "sent": self.sent_count,
                "acked": self.ack_count
            }
            
        avg_latency = sum(self.latencies) / len(self.latencies)
        max_latency = max(self.latencies)
        packet_loss = 1 - (self.ack_count / self.sent_count) if self.sent_count > 0 else 0
        
        return {
            "avg_latency": avg_latency,
            "max_latency": max_latency,
            "packet_loss": packet_loss,
            "sent": self.sent_count,
            "acked": self.ack_count
        }


class StatusListener(SubscribeCallback):
    """Listen for status updates from followers."""
    
    def __init__(self, monitor: NetworkMonitor):
        self.monitor = monitor
        self.follower_status = {}
        
    def message(self, pubnub, message):
        """Handle status messages from followers."""
        data = message.message
        if isinstance(data, dict) and data.get("type") == "ack":
            # Acknowledgment from follower
            sequence = data.get("sequence")
            timestamp = data.get("timestamp")
            if sequence is not None and timestamp is not None:
                latency = self.monitor.message_acknowledged(sequence, timestamp)
                if latency and latency > pubnub_config.LATENCY_WARNING_MS:
                    logger.warning(f"{Fore.YELLOW}High latency: {latency:.1f}ms{Style.RESET_ALL}")
                
        elif isinstance(data, dict) and data.get("type") == "status":
            # Status update from follower
            self.follower_status[data.get("follower_id")] = data
            

class LeaderTeleop:
    """Main teleoperation class for leader side."""
    
    def __init__(self, motor_ids: List[int], baudrate: int = 1000000):
        self.motor_ids = motor_ids
        self.baudrate = baudrate
        self.leaders: List[SO101Controller] = []
        self.running = False
        self.sequence = 0
        
        # Network components
        self.pubnub: Optional[PubNub] = None
        self.monitor = NetworkMonitor()
        self.status_listener = StatusListener(self.monitor)
        
        # Performance tracking
        self.last_publish_time = 0
        self.publish_times = []
        
    def setup_pubnub(self):
        """Initialize PubNub connection."""
        logger.info("Setting up PubNub connection...")
        
        pnconfig = PNConfiguration()
        pnconfig.subscribe_key = pubnub_config.SUBSCRIBE_KEY
        pnconfig.publish_key = pubnub_config.PUBLISH_KEY
        pnconfig.user_id = f"leader-{platform.node()}"
        pnconfig.ssl = True
        pnconfig.enable_subscribe = True
        # Disable PubNub's internal logging
        pnconfig.log_verbosity = False
        pnconfig.enable_logging = False
        
        self.pubnub = PubNub(pnconfig)
        self.pubnub.add_listener(self.status_listener)
        
        # Subscribe to status channel for follower feedback
        self.pubnub.subscribe().channels([pubnub_config.STATUS_CHANNEL]).execute()
        
        logger.info(f"{Fore.GREEN}✓ PubNub connected as {pnconfig.user_id}{Style.RESET_ALL}")
        
    def auto_detect_leaders(self) -> List[str]:
        """Find and identify leader robots."""
        ports = find_robot_ports()
        leader_ports = []
        
        logger.info(f"Found {len(ports)} serial ports")
        
        for port in ports:
            try:
                is_leader, voltage = identify_robot_by_voltage(port, self.motor_ids)
                if is_leader:
                    leader_ports.append(port)
                    logger.info(f"{Fore.GREEN}✓ Leader robot found at {port} ({voltage:.1f}V){Style.RESET_ALL}")
            except Exception as e:
                logger.warning(f"Failed to identify {port}: {e}")
                
        if len(leader_ports) != 2:
            raise RuntimeError(f"Expected 2 leader robots, found {len(leader_ports)}")
            
        return leader_ports
        
    def connect_leaders(self):
        """Connect to leader robots."""
        leader_ports = self.auto_detect_leaders()
        
        self.leaders = [
            SO101Controller(leader_ports[0], self.motor_ids, self.baudrate, "Leader1"),
            SO101Controller(leader_ports[1], self.motor_ids, self.baudrate, "Leader2")
        ]
        
        for leader in self.leaders:
            leader.connect()
            
        logger.info(f"{Fore.GREEN}✓ Connected to {len(self.leaders)} leader robots{Style.RESET_ALL}")
        
    def publish_positions(self, positions: Dict[str, Dict[int, int]]):
        """Publish position data to PubNub."""
        self.sequence += 1
        
        # Convert motor IDs to strings for JSON serialization
        json_positions = {}
        for robot_id, robot_positions in positions.items():
            json_positions[robot_id] = {str(motor_id): int(pos) for motor_id, pos in robot_positions.items()}
        
        message = {
            "type": "telemetry",
            "timestamp": time.time(),
            "sequence": self.sequence,
            "positions": json_positions
        }
        
        try:
            # Publish to telemetry channel
            self.pubnub.publish().channel(pubnub_config.TELEMETRY_CHANNEL).message(message).sync()
            self.monitor.message_sent(self.sequence)
            
            # Track publish rate
            now = time.time()
            if self.last_publish_time > 0:
                self.publish_times.append(now - self.last_publish_time)
                if len(self.publish_times) > 100:
                    self.publish_times.pop(0)
            self.last_publish_time = now
            
        except PubNubException as e:
            logger.error(f"Failed to publish: {e}")
            
    def display_status(self):
        """Display current status and statistics."""
        stats = self.monitor.get_stats()
        
        # Clear screen and move cursor to top
        print("\033[2J\033[H", end="")
        
        print(f"{Style.BRIGHT}=== LEADER TELEOPERATION ==={Style.RESET_ALL}")
        print(f"Connected Leaders: {len(self.leaders)}")
        print()
        
        # Network stats
        print(f"{Style.BRIGHT}Network Statistics:{Style.RESET_ALL}")
        print(f"  Average Latency: {stats['avg_latency']:.1f}ms")
        print(f"  Max Latency:     {stats['max_latency']:.1f}ms")
        print(f"  Packet Loss:     {stats['packet_loss']*100:.1f}%")
        print(f"  Messages Sent:   {stats['sent']}")
        
        # Publish rate
        if self.publish_times:
            avg_interval = sum(self.publish_times) / len(self.publish_times)
            actual_fps = 1.0 / avg_interval if avg_interval > 0 else 0
            print(f"  Publish Rate:    {actual_fps:.1f} Hz")
            
        # Follower status
        print()
        print(f"{Style.BRIGHT}Follower Status:{Style.RESET_ALL}")
        for follower_id, status in self.status_listener.follower_status.items():
            age = time.time() - status.get("timestamp", 0)
            if age < 5:  # Only show recent status
                print(f"  {follower_id}: Connected, {status.get('motors_active', 0)} motors active")
                
        print()
        print(f"{Fore.CYAN}Press Ctrl+C to stop{Style.RESET_ALL}")
        
    def teleoperation_loop(self):
        """Main loop reading positions and publishing."""
        self.running = True
        target_interval = 1.0 / pubnub_config.TARGET_FPS
        
        # Start display thread
        display_thread = threading.Thread(target=self.display_loop, daemon=True)
        display_thread.start()
        
        logger.info(f"Starting teleoperation at {pubnub_config.TARGET_FPS} Hz...")
        
        try:
            while self.running and not shutdown_requested:
                loop_start = time.time()
                
                # Read positions from all leaders
                positions = {}
                for leader in self.leaders:
                    leader_positions = leader.read_positions()
                    if leader_positions:
                        positions[leader.robot_id] = leader_positions
                        
                # Publish if we have data
                if positions:
                    self.publish_positions(positions)
                    
                # Maintain target rate
                elapsed = time.time() - loop_start
                if elapsed < target_interval:
                    time.sleep(target_interval - elapsed)
                    
        except KeyboardInterrupt:
            logger.info("\nStopping teleoperation...")
        finally:
            self.running = False
            
    def display_loop(self):
        """Separate thread for updating display."""
        while self.running and not shutdown_requested:
            self.display_status()
            time.sleep(0.5)  # Update display at 2Hz
            
    def shutdown(self):
        """Clean shutdown."""
        self.running = False
        
        # Publish disconnect message
        if self.pubnub:
            try:
                disconnect_msg = {
                    "type": "disconnect",
                    "timestamp": time.time(),
                    "leader_id": f"leader-{platform.node()}"
                }
                self.pubnub.publish().channel(pubnub_config.STATUS_CHANNEL).message(disconnect_msg).sync()
            except:
                pass
                
            self.pubnub.unsubscribe_all()
            
        # Disconnect robots
        logger.info("Disconnecting robots...")
        for leader in self.leaders:
            try:
                leader.disconnect()
            except Exception as e:
                logger.warning(f"Failed to disconnect {leader.robot_id}: {e}")
                
        logger.info("Shutdown complete")


def main():
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(description="Leader-side teleoperation via PubNub")
    parser.add_argument("--motor_ids", type=str, default="1,2,3,4,5,6",
                       help="Comma-separated motor IDs")
    parser.add_argument("--baudrate", type=int, default=1000000,
                       help="Serial baudrate")
    parser.add_argument("--fps", type=int, default=60,
                       help="Target update rate (Hz)")
    
    args = parser.parse_args()
    
    # Parse motor IDs
    motor_ids = [int(id.strip()) for id in args.motor_ids.split(",")]
    
    # Override config FPS if specified
    if args.fps:
        pubnub_config.TARGET_FPS = args.fps
    
    # Create and run teleoperation
    teleop = LeaderTeleop(motor_ids, args.baudrate)
    
    try:
        # Setup
        teleop.setup_pubnub()
        teleop.connect_leaders()
        
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