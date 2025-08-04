#!/usr/bin/env python3
"""
Test script for ARX leader arm calibration.

This script provides various tests to validate the calibration process
and help debug the servo-to-ARX position mapping.

Usage:
    python test_arx_calibration.py [--test TEST_NAME]
"""

import argparse
import json
import logging
import sys
import time
from typing import Dict, List, Optional

import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    class Fore:
        RED = GREEN = YELLOW = CYAN = MAGENTA = BLUE = ""
    class Style:
        RESET_ALL = BRIGHT = ""

from single_arx_leader_calib import LeaderArmCalibrator, auto_detect_port, CALIBRATION_FILE


class CalibrationTester:
    """Test suite for ARX calibration system."""
    
    def __init__(self):
        self.calibrator: Optional[LeaderArmCalibrator] = None
        
    def setup_calibrator(self, port: str = None, motor_ids: List[int] = None) -> bool:
        """Setup the calibrator for testing."""
        if port is None:
            try:
                port = auto_detect_port()
            except RuntimeError as e:
                logger.error(f"Port detection failed: {e}")
                return False
                
        if motor_ids is None:
            motor_ids = [1, 2, 3, 4, 5, 6, 7]  # Default 7-joint arm
            
        self.calibrator = LeaderArmCalibrator(port, motor_ids)
        
        if not self.calibrator.connect():
            logger.error("Failed to connect to leader arm")
            return False
            
        logger.info(f"✓ Connected to leader arm on {port}")
        return True
        
    def cleanup(self):
        """Cleanup calibrator connection."""
        if self.calibrator:
            self.calibrator.disconnect()
            
    def test_servo_communication(self) -> bool:
        """Test 1: Basic servo communication and position reading."""
        print(f"\n{Fore.BLUE}=== Test 1: Servo Communication ==={Style.RESET_ALL}")
        
        if not self.calibrator:
            logger.error("Calibrator not initialized")
            return False
            
        try:
            # Read positions multiple times to test consistency
            positions_list = []
            for i in range(5):
                positions = self.calibrator.read_servo_positions()
                positions_list.append(positions)
                print(f"Reading {i+1}: {positions}")
                time.sleep(0.1)
                
            # Check consistency
            if len(positions_list) < 5:
                logger.error("Failed to get consistent readings")
                return False
                
            # Check if all motors respond
            expected_motors = set(self.calibrator.motor_ids)
            actual_motors = set(positions_list[0].keys())
            
            if expected_motors != actual_motors:
                missing = expected_motors - actual_motors
                extra = actual_motors - expected_motors
                logger.warning(f"Motor ID mismatch - Missing: {missing}, Extra: {extra}")
                
            # Check position stability (should be very similar across readings)
            for motor_id in actual_motors:
                positions = [reading[motor_id] for reading in positions_list]
                max_diff = max(positions) - min(positions)
                if max_diff > 5:  # Allow small drift
                    logger.warning(f"Motor {motor_id} position unstable: range {max_diff}")
                else:
                    logger.info(f"Motor {motor_id}: stable (range: {max_diff})")
                    
            print(f"{Fore.GREEN}✓ Servo communication test passed{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            logger.error(f"Servo communication test failed: {e}")
            return False
            
    def test_position_range_mapping(self) -> bool:
        """Test 2: Position range and conversion formulas."""
        print(f"\n{Fore.BLUE}=== Test 2: Position Range Mapping ==={Style.RESET_ALL}")
        
        if not self.calibrator:
            logger.error("Calibrator not initialized")
            return False
            
        try:
            current_positions = self.calibrator.read_servo_positions()
            
            print(f"Servo resolution: {self.calibrator.resolution}")
            print(f"Position range: 0 to {self.calibrator.max_position}")
            print()
            
            # Test conversion formulas
            print("Position conversion analysis:")
            print(f"{'Motor':<8} | {'Current':>8} | {'Middle':>8} | {'Degrees':>8} | {'Radians':>10}")
            print("-" * 60)
            
            for motor_id in sorted(current_positions.keys()):
                pos = current_positions[motor_id]
                middle_offset = pos - 2048  # Offset from theoretical middle
                degrees = (pos / self.calibrator.resolution) * 360
                radians = (pos / self.calibrator.resolution) * 2 * np.pi
                
                print(f"{motor_id:<8} | {pos:>8} | {middle_offset:>8} | {degrees:>7.1f}° | {radians:>9.3f}")
                
            # Show ARX-style conversion (what teleoperation uses)
            print(f"\nARX conversion (current formula):")
            print("  Formula: (tic_pos - servo_center) * (2π / 4095)")
            print("  servo_center = 2048 (current hardcoded value)")
            print()
            
            for motor_id in sorted(current_positions.keys()):
                pos = current_positions[motor_id]
                # Current conversion formula
                arx_radians = (pos - 2048) * (2 * np.pi) / 4095.0
                print(f"  Motor {motor_id}: {pos} → {arx_radians:.3f} rad ({np.degrees(arx_radians):.1f}°)")
                
            print(f"{Fore.GREEN}✓ Position range mapping test completed{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            logger.error(f"Position range mapping test failed: {e}")
            return False
            
    def test_calibration_file_io(self, calibration_file: str = CALIBRATION_FILE) -> bool:
        """Test 3: Calibration file save/load functionality."""
        print(f"\n{Fore.BLUE}=== Test 3: Calibration File I/O ==={Style.RESET_ALL}")
        
        if not self.calibrator:
            logger.error("Calibrator not initialized")
            return False
            
        try:
            # Create test calibration data
            test_positions = self.calibrator.read_servo_positions()
            
            # Save calibration
            test_file = f"test_{calibration_file}"
            if not self.calibrator.save_calibration(test_positions, test_file):
                logger.error("Failed to save test calibration")
                return False
                
            # Load and verify
            loaded_data = self.calibrator.load_calibration(test_file)
            if not loaded_data:
                logger.error("Failed to load test calibration")
                return False
                
            # Verify data integrity
            loaded_positions = loaded_data["home_positions"]
            
            for motor_id, original_pos in test_positions.items():
                loaded_pos = loaded_positions.get(str(motor_id))  # JSON keys are strings
                if loaded_pos != original_pos:
                    logger.error(f"Position mismatch for motor {motor_id}: {original_pos} != {loaded_pos}")
                    return False
                    
            # Cleanup test file
            import os
            try:
                os.remove(test_file)
            except:
                pass
                
            print(f"{Fore.GREEN}✓ Calibration file I/O test passed{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            logger.error(f"Calibration file I/O test failed: {e}")
            return False
            
    def test_voltage_detection(self) -> bool:
        """Test 4: Voltage detection for leader/follower identification."""
        print(f"\n{Fore.BLUE}=== Test 4: Voltage Detection ==={Style.RESET_ALL}")
        
        if not self.calibrator:
            logger.error("Calibrator not initialized")
            return False
            
        try:
            voltage = self.calibrator.read_servo_voltage()
            is_leader = 4.5 <= voltage <= 5.5
            
            print(f"Detected voltage: {voltage:.2f}V")
            print(f"Robot type: {'LEADER' if is_leader else 'FOLLOWER'}")
            
            # Expected ranges
            print(f"\nExpected ranges:")
            print(f"  Leader (5V supply): 4.5V - 5.5V")
            print(f"  Follower (12V supply): 11.0V - 13.0V")
            
            if voltage < 4.0:
                logger.warning("Voltage very low - check power supply")
            elif 5.5 < voltage < 11.0:
                logger.warning("Voltage in unexpected range - check wiring")
                
            print(f"{Fore.GREEN}✓ Voltage detection test completed{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            logger.error(f"Voltage detection test failed: {e}")
            return False
            
    def test_live_calibration_preview(self, calibration_file: str = CALIBRATION_FILE) -> bool:
        """Test 5: Live preview of calibration accuracy."""
        print(f"\n{Fore.BLUE}=== Test 5: Live Calibration Preview ==={Style.RESET_ALL}")
        
        # Load existing calibration
        calibration_data = self.calibrator.load_calibration(calibration_file)
        if not calibration_data:
            print(f"{Fore.YELLOW}No existing calibration found. Create one first.{Style.RESET_ALL}")
            return True
            
        home_positions = calibration_data["home_positions"]
        
        print("Live calibration preview - move the arm and see the ARX equivalent positions")
        print("Press Ctrl+C to stop")
        print()
        
        try:
            while True:
                current_positions = self.calibrator.read_servo_positions()
                
                print(f"\r{Fore.CYAN}ARX Joint Positions (radians):{Style.RESET_ALL}")
                arx_positions = []
                
                for motor_id in sorted(current_positions.keys()):
                    current_pos = current_positions[motor_id]
                    home_pos = int(home_positions.get(str(motor_id), 2048))
                    
                    # Apply calibration formula
                    arx_radians = (current_pos - home_pos) * (2 * np.pi) / 4095.0
                    arx_positions.append(arx_radians)
                    
                    print(f"  Joint {motor_id}: {arx_radians:+7.3f} rad ({np.degrees(arx_radians):+7.1f}°)")
                    
                print(f"  Combined: {arx_positions}")
                print("\033[8A", end="")  # Move cursor up to overwrite
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n" * 8)  # Clear the overwritten lines
            print(f"{Fore.GREEN}✓ Live calibration preview completed{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            logger.error(f"Live calibration preview failed: {e}")
            return False
            
    def run_all_tests(self, calibration_file: str = CALIBRATION_FILE) -> bool:
        """Run all calibration tests."""
        print(f"\n{Fore.MAGENTA}=== ARX Calibration Test Suite ==={Style.RESET_ALL}")
        
        tests = [
            ("Servo Communication", self.test_servo_communication),
            ("Position Range Mapping", self.test_position_range_mapping),
            ("Calibration File I/O", lambda: self.test_calibration_file_io(calibration_file)),
            ("Voltage Detection", self.test_voltage_detection),
            ("Live Calibration Preview", lambda: self.test_live_calibration_preview(calibration_file)),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
                if result:
                    logger.info(f"✓ {test_name}: PASSED")
                else:
                    logger.error(f"✗ {test_name}: FAILED")
            except Exception as e:
                logger.error(f"✗ {test_name}: ERROR - {e}")
                results.append((test_name, False))
                
        # Summary
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        print(f"\n{Fore.CYAN}=== Test Summary ==={Style.RESET_ALL}")
        for test_name, result in results:
            status = f"{Fore.GREEN}PASSED{Style.RESET_ALL}" if result else f"{Fore.RED}FAILED{Style.RESET_ALL}"
            print(f"  {test_name}: {status}")
            
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print(f"{Fore.GREEN}🎉 All tests passed! Calibration system is working correctly.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠️  Some tests failed. Check the issues above.{Style.RESET_ALL}")
            
        return passed == total


def main():
    parser = argparse.ArgumentParser(description="Test ARX calibration system")
    parser.add_argument("--test", type=str, choices=[
        "communication", "mapping", "file_io", "voltage", "live_preview", "all"
    ], default="all", help="Specific test to run (default: all)")
    parser.add_argument("--port", type=str, help="Serial port (auto-detect if not specified)")
    parser.add_argument("--motor_ids", type=str, default="1,2,3,4,5,6,7",
                       help="Comma-separated motor IDs (default: 1,2,3,4,5,6,7)")
    parser.add_argument("--calibration_file", type=str, default=CALIBRATION_FILE,
                       help=f"Calibration file to test (default: {CALIBRATION_FILE})")
    
    args = parser.parse_args()
    
    # Parse motor IDs
    motor_ids = [int(id.strip()) for id in args.motor_ids.split(",")]
    
    # Create tester
    tester = CalibrationTester()
    
    try:
        # Setup calibrator
        if not tester.setup_calibrator(args.port, motor_ids):
            return 1
            
        # Run requested test
        if args.test == "all":
            success = tester.run_all_tests(args.calibration_file)
        elif args.test == "communication":
            success = tester.test_servo_communication()
        elif args.test == "mapping":
            success = tester.test_position_range_mapping()
        elif args.test == "file_io":
            success = tester.test_calibration_file_io(args.calibration_file)
        elif args.test == "voltage":
            success = tester.test_voltage_detection()
        elif args.test == "live_preview":
            success = tester.test_live_calibration_preview(args.calibration_file)
        else:
            logger.error(f"Unknown test: {args.test}")
            return 1
            
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Testing interrupted by user{Style.RESET_ALL}")
        return 1
    except Exception as e:
        logger.error(f"Testing error: {e}")
        return 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())