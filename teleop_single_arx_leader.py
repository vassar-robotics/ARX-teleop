#!/usr/bin/env python3
"""
Single-arm leader-side teleoperation script using ZMQ for communication.

This script:
1. Connects to 1 leader robot (<9V) via USB  # REMOVED: dual functionality for 2 leaders
2. Reads its positions at high frequency
3. Publishes position data via ZMQ for a single follower robot

Usage:
    python teleop_single_arx_leader.py
"""

import os
from turtle import right
import pygame
import time
import zmq
import json
import argparse
import json
import platform
import signal
import sys
import time
import threading
from typing import Dict, List, Optional
from vassar_feetech_servo_sdk import ServoController
from Network_Monitor import NetworkMonitor

# Import select for Unix systems
try:
    import select
except ImportError:
    # Windows doesn't have select for stdin
    select = None

try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    # Fallback if colorama not installed
    class Fore:
        RED = GREEN = YELLOW = CYAN = MAGENTA = ""
    class Style:
        RESET_ALL = BRIGHT = ""


# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) for graceful shutdown."""
    global shutdown_requested
    print("\n\n⚠️  Shutdown requested. Cleaning up...")
    shutdown_requested = True


class LeaderHardware: # TODO rename class to MarvinRobot
    """Main keader hardware class for teleoperation"""
    
    def __init__(self, motor_ids: List[int], baudrate: int = 1000000, left_leader_port: str = "/dev/tty.usbmodem5A680090901", right_leader_port: str = "/dev/tty.usbmodem5A680135841"):
        self.left_leader_port = left_leader_port
        self.right_leader_port = right_leader_port
        self.motor_ids = motor_ids
        self.baudrate = baudrate
        self.leader_left: Optional[ServoController] = None
        self.leader_right: Optional[ServoController] = None
        self.running = False
        self.sequence = 0
        self.GRIPPER_TORQUE_FACTOR = 0.001 # TODO check this

        self.left_positions = None
        self.right_positions = None
        
        # Publish network components
        self.zmq_socket = None
        self.monitor = NetworkMonitor()

        # Receive network components
        self.s = zmq.Context().socket(zmq.PULL)
        self.s.bind("tcp://0.0.0.0:5001")
        print("Leader set up to ZMQ")
        
        # Performance tracking
        self.last_publish_time = 0
        self.publish_times = []
        self.LIFT_SPEED_RPM = 50
        self.DRIVE_SPEED_RPM = 100
        self.TURN_SPEED_FACTOR = 0.7
        self.left_speed = 0
        self.right_speed = 0
        self.z_speed = 0
        self.dt_controls = {
            "left_speed": self.left_speed,
            "right_speed": self.right_speed,
            "z_speed": self.z_speed
        }

        self.setup_pygame()

    
    def connect_leader_arms(self):
        """Connect to the leader robot arms."""

        self.leader_left = ServoController(servo_ids=[1,2,3,4,5,6,7], servo_type="hls", port=self.left_leader_port)
        self.leader_right = ServoController(servo_ids=[1,2,3,4,5,6,7], servo_type="hls", port=self.right_leader_port)
        self.leader_left.connect()
        self.leader_right.connect()

        positions_left = self.leader_left.read_all_positions()
        positions_right = self.leader_right.read_all_positions()
        for motor_id, pos in positions_left.items():
            print(f"Left motor {motor_id}: {pos} ({pos/4095*100:.1f}%)")

        for motor_id, pos in positions_right.items():
            print(f"Right motor {motor_id}: {pos} ({pos/4095*100:.1f}%)")

        print(f"{Fore.GREEN}✓ Connected to 2 leader robots at {self.left_leader_port} and {self.right_leader_port}{Style.RESET_ALL}")
    
    def read_leader_positions(self):
        """Read positions from the leader robot."""
        self.left_positions = self.leader_left.read_all_positions()
        self.right_positions = self.leader_right.read_all_positions()

    def disconnect_leader_arms(self):
        """Disconnect from the leader robot."""
        self.leader_left.disconnect()
        self.leader_right.disconnect()
        print(f"{Fore.RED}✗ Disconnected from 2 leader robots at {self.left_leader_port} and {self.right_leader_port}{Style.RESET_ALL}")


    def setup_pygame(self):
        """Initialize pygame."""
        pygame.init()
        self.screen = pygame.display.set_mode((400, 320))
        pygame.display.set_caption("RS03 Tank Drive + Z-Axis Control")


    def draw_status(self):
        """Draw status information on screen"""
        self.screen.fill((0, 0, 0))
        
        font = pygame.font.Font(None, 36)
        
        # Title
        title = font.render("RS03 Tank Drive + Z", True, (255, 255, 255))
        self.screen.blit(title, (80, 20))
        
        # Instructionsleft
        font_small = pygame.font.Font(None, 24)
        instructions = [
            "W - Forward",
            "S - Backward", 
            "A - Turn Left",
            "D - Turn Right",
            "Q - Z-axis Up",
            "E - Z-axis Down",
            "ESC - Exit"
        ]
        
        y = 80
        for instruction in instructions:
            text = font_small.render(instruction, True, (200, 200, 200))
            self.screen.blit(text, (20, y))
            y += 25
            
        # Motor speeds
        left_text = font_small.render(f"Left Motor: {self.left_speed:.1f} RPM", True, (0, 255, 0))
        right_text = font_small.render(f"Right Motor: {self.right_speed:.1f} RPM", True, (0, 255, 0))
        self.screen.blit(left_text, (20, 250))
        self.screen.blit(right_text, (200, 250))
        
        # Z-axis position
        z_text = font_small.render(f"Z Position: {self.z_speed} ({self.z_speed/16384:.2f} rev)", True, (0, 255, 255))
        self.screen.blit(z_text, (20, 275))
        
        pygame.display.flip()

    def handle_dt_input(self, events):
        """Handle keyboard input for drivetrain."""
        keys = pygame.key.get_pressed()

        # Calculate base speeds for tank drive
        forward = 0
        turn = 0

        if keys[pygame.K_s]:
            forward = self.DRIVE_SPEED_RPM
        elif keys[pygame.K_w]:
            forward = -self.DRIVE_SPEED_RPM

        if keys[pygame.K_a]:
            turn = -self.DRIVE_SPEED_RPM * self.TURN_SPEED_FACTOR
        elif keys[pygame.K_d]:
            turn = self.DRIVE_SPEED_RPM * self.TURN_SPEED_FACTOR

        if keys[pygame.K_q]:
            self.z_speed =  self.LIFT_SPEED_RPM
        elif keys[pygame.K_e]:
            self.z_speed = -self.LIFT_SPEED_RPM
        else:
            self.z_speed = 0

        self.left_speed = forward + turn
        self.right_speed = forward - turn

        self.dt_controls = {
            "left_speed": self.left_speed,
            "right_speed": self.right_speed,
            "z_speed": self.z_speed
        }

    def apply_force_feedback(self, feedback_message):
        """Apply force feedback to the leader robot."""
        print(f"Received feedback message: {feedback_message}")
        feedback_data = json.loads(feedback_message)
        left_gripper_torque = self.GRIPPER_TORQUE_FACTOR * (feedback_data["left_delta"]["7"] - self.left_positions["7"])
        right_gripper_torque = self.GRIPPER_TORQUE_FACTOR * (feedback_data["right_delta"]["7"] - self.right_positions["7"])
        self.leader_left.set_torque(7, left_gripper_torque)
        self.leader_right.set_torque(7, right_gripper_torque)

    def publish_positions(self, left_positions: Dict[int, int], right_positions: Dict[int, int]):
        """Publish position data via ZMQ."""
        self.sequence += 1
        
        # SIMPLIFIED: No mapping needed for single arm - directly use positions
        # Convert motor IDs to strings for JSON serialization
        left_position_data = {str(motor_id): int(pos) for motor_id, pos in left_positions.items()}
        right_position_data = {str(motor_id): int(pos) for motor_id, pos in right_positions.items()}
        
        message = {
            "type": "telemetry",
            "timestamp": time.time(),
            "sequence": self.sequence,
            "left_positions": left_position_data,  # Single arm positions
            "right_positions": right_position_data,  # Single arm positions
            "dt_controls": self.dt_controls
        }
        
        try:
            # Send via ZMQ
            self.zmq_socket.send_string(json.dumps(message))
            self.monitor.message_sent(self.sequence)
            
            # Track publish rate
            now = time.time()
            if self.last_publish_time > 0:
                self.publish_times.append(now - self.last_publish_time)
                if len(self.publish_times) > 100:
                    self.publish_times.pop(0)
            self.last_publish_time = now
            
        except Exception as e:
            print(f"Failed to publish: {e}")
            
    def display_status(self):
        """Display current status and statistics - compact version."""
        stats = self.monitor.get_stats()
        
        # Build compact status line
        leader_status = "✓" if self.leader_left and self.leader_right else "❌"
        
        # Network info
        if stats['avg_latency'] > 0:
            net_info = f"Latency: {stats['avg_latency']:.1f}ms | Loss: {stats['packet_loss']*100:.1f}%"
        else:
            net_info = "Network: Disconnected"
        
        # Publish rate
        if self.publish_times:
            avg_interval = sum(self.publish_times) / len(self.publish_times)
            actual_fps = 1.0 / avg_interval if avg_interval > 0 else 0
            rate_info = f"Rate: {actual_fps:.1f}Hz"
        else:
            rate_info = "Rate: --"
        
        # Single compact line
        status_line = f"LEADER {leader_status} | {net_info} | {rate_info} | Sent: {stats['sent']}"
        print(f"\r{status_line:<80}", end="", flush=True)
        
    def teleoperation_loop(self):
        """Main loop reading positions and publishing."""
        self.running = True
        target_fps = 20  # Default 20 FPS
        target_interval = 1.0 / target_fps
        
        # Start display thread
        display_thread = threading.Thread(target=self.display_loop, daemon=True)
        display_thread.start()
        
        print(f"Starting single arm teleoperation at {target_fps} Hz...")
        print("Status updates every 2 seconds on single line. Press Ctrl+C to stop.")
        
        try:
            while self.running and not shutdown_requested:
                
                loop_start = time.time()

                # TODO check if draw status works here
                # Get all events
                events = pygame.event.get()
                
                # Handle system events
                for event in events:
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.running = False

                self.handle_dt_input(events)
                self.draw_status()

                # Receive feedback from follower
                feedback_message = self.s.recv_string(flags=zmq.NOBLOCK)  # Non-blocking receive
                if feedback_message:
                    print(f"Received message: {feedback_message}")
                
                # Read positions from the leader
                if self.leader_left and self.leader_right:
                    self.read_leader_positions()
                    if self.left_positions and self.right_positions:
                        self.apply_force_feedback(feedback_message)
                        self.publish_positions(self.left_positions, self.right_positions)
                    
                # Maintain target rate
                elapsed = time.time() - loop_start
                if elapsed < target_interval:
                    time.sleep(target_interval - elapsed)

                    
        except KeyboardInterrupt:
            print()  # New line after status display
            print("Stopping teleoperation...")
        finally:
            self.running = False


            
    def display_loop(self):
        """Separate thread for updating display."""
        while self.running and not shutdown_requested:
            self.display_status()
            time.sleep(2.0)  # Update display at 0.5Hz (every 2 seconds) - much less frequent
            
    def shutdown(self):
        """Clean shutdown."""
        self.running = False
        print()  # New line after status display
        
        # Disconnect robot
        print("Disconnecting robot...")
        if self.leader_left and self.leader_right:
            try:
                self.leader_left.disconnect()
                self.leader_right.disconnect()
            except Exception as e:
                print(f"Failed to disconnect leader: {e}")
                
        print("Shutdown complete")


def main():
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(description="Single-arm leader-side teleoperation via ZMQ")
    parser.add_argument("--baudrate", type=int, default=1000000,
                       help="Serial baudrate")
    parser.add_argument("--fps", type=int, default=20,
                       help="Target update rate (Hz)")
    
    args = parser.parse_args()
    
    # Parse motor IDs
    motor_ids = [1,2,3,4,5,6,7]
    
    # Override config FPS if specified
    target_fps = args.fps if args.fps else 20
    
    # Create and run teleoperation
    leader_hardware = LeaderHardware(motor_ids, args.baudrate)
    
    try:
        # Set up ZMQ streaming
        context = zmq.Context()
        leader_hardware.zmq_socket = context.socket(zmq.PUSH)
        leader_hardware.zmq_socket.connect("tcp://192.168.165.119:5000")
        # leader_hardware.zmq_socket.connect("tcp://10.1.10.85:5000")
        print("Successfully connected to ZMQ")
        
        # Connect to leader robot
        leader_hardware.connect_leader_arms()
        
        # Run main loop
        leader_hardware.teleoperation_loop()
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        leader_hardware.shutdown()
        
    return 0


if __name__ == "__main__":
    sys.exit(main())