#!/usr/bin/env python3
"""Example of continuous reading with custom callback."""

import time
from i2rt.robots.utils import GripperType
import numpy as np
from datetime import datetime
from vassar_feetech_servo_sdk import ServoController
from i2rt.robots.get_robot import get_yam_robot

class PositionLogger:
    """Example class that logs position data."""
    
    def __init__(self):
        self.start_time = time.time()
        self.reading_count = 0
        
    def log_positions(self, positions):
        """Custom callback to log position data."""
        self.reading_count += 1
        elapsed = time.time() - self.start_time
        
        # Log data
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] Reading #{self.reading_count} "
              f"(elapsed: {elapsed:.1f}s)")
        
        # Print each servo's position
        for motor_id in sorted(positions.keys()):
            pos = positions[motor_id]
            percent = pos / 4095 * 100
            print(f"  Motor {motor_id}: {pos:4d} ({percent:5.1f}%)")
        print()


def main():
    robot = get_yam_robot("can0", gripper_type=GripperType.YAM_COMPACT_SMALL)
    
    # Define your servo configuration
    servo_ids = [1, 2, 3, 4, 5, 6, 7]
    servo_type = "hls"  # or "hls" for HLS servos
    
    # Create controller and logger
    controller = ServoController(servo_ids=servo_ids, servo_type=servo_type)
    logger = PositionLogger()
    
    # Use context manager for automatic cleanup
    with controller:
        print(f"Starting continuous reading of {servo_type.upper()} servos at 10Hz...")
        print("Press Ctrl+C to stop\n")
        
        try:
            # Read continuously at 10Hz
            frequency = 10.0
            loop_time = 1.0 / frequency
            
            while True:
                start = time.perf_counter()
                
                # Read positions
                positions = controller.read_positions()
                
                i2rt_positions = np.zeros(7)
                
                for motor_id in sorted(positions.keys()):
                    if motor_id == 7:
                        i2rt_positions[6] = positions[motor_id] / 2048 - 1
                    else:
                        pos = positions[motor_id]
                        i2rt_pos = ((pos / 2048) -1) * 3.141592653589793
                        i2rt_positions[motor_id - 1] = i2rt_pos

                

                # invert gripper
               

                robot.command_joint_pos(i2rt_positions)

                print(f"I2RT positions: {i2rt_positions}")
                print(f"Gripper position: {i2rt_positions[6]}")

                # Log with custom callback
                logger.log_positions(positions)
                
                # Maintain rate
                elapsed = time.perf_counter() - start
                if elapsed < loop_time:
                    time.sleep(loop_time - elapsed)
                    
        except KeyboardInterrupt:
            print(f"\nTotal readings: {logger.reading_count}")
            print(f"Duration: {time.time() - logger.start_time:.1f}s")


if __name__ == "__main__":
    main()