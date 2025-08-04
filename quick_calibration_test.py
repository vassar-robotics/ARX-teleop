#!/usr/bin/env python3
"""
Quick test script to validate ARX calibration system setup.

This script performs basic checks without requiring hardware connection.
Use this to verify the calibration system is properly installed.

Usage:
    python quick_calibration_test.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import numpy as np
        print("  ✓ numpy")
    except ImportError:
        print("  ✗ numpy - install with: pip install numpy")
        return False
        
    try:
        import serial
        print("  ✓ pyserial")
    except ImportError:
        print("  ✗ pyserial - install with: pip install pyserial")
        return False
        
    try:
        import colorama
        print("  ✓ colorama")
    except ImportError:
        print("  ⚠ colorama - optional, install with: pip install colorama")
        
    try:
        # Test our calibration modules
        from single_arx_leader_calib import LeaderArmCalibrator
        print("  ✓ single_arx_leader_calib")
    except ImportError as e:
        print(f"  ✗ single_arx_leader_calib - {e}")
        return False
        
    try:
        from test_arx_calibration import CalibrationTester
        print("  ✓ test_arx_calibration")
    except ImportError as e:
        print(f"  ✗ test_arx_calibration - {e}")
        return False
        
    return True

def test_calibration_file_format():
    """Test calibration file format handling."""
    print("\nTesting calibration file format...")
    
    # Create test calibration data
    test_calibration = {
        "timestamp": 1699123456.789,
        "timestamp_str": "2023-11-04 14:30:56",
        "motor_ids": [1, 2, 3, 4, 5, 6, 7],
        "home_positions": {
            "1": 2048,
            "2": 1856,
            "3": 2240,
            "4": 2048,
            "5": 2048,
            "6": 1920,
            "7": 2048
        },
        "servo_resolution": 4096,
        "port": "/dev/ttyUSB0",
        "voltage": 5.1,
        "is_leader": True,
        "notes": "Test calibration data"
    }
    
    # Test save/load
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_calibration, f, indent=2)
        test_file = f.name
        
    try:
        # Test loading
        with open(test_file, 'r') as f:
            loaded_data = json.load(f)
            
        # Verify data integrity
        assert loaded_data["motor_ids"] == [1, 2, 3, 4, 5, 6, 7]
        assert loaded_data["home_positions"]["1"] == 2048
        assert loaded_data["servo_resolution"] == 4096
        
        print("  ✓ Calibration file format valid")
        return True
        
    except Exception as e:
        print(f"  ✗ Calibration file format error: {e}")
        return False
        
    finally:
        # Cleanup
        try:
            os.unlink(test_file)
        except:
            pass

def test_position_conversion():
    """Test position conversion formulas."""
    print("\nTesting position conversion...")
    
    try:
        import numpy as np
        
        # Test conversion parameters
        servo_resolution = 4095.0
        servo_to_radian_scale = (2 * np.pi) / servo_resolution
        
        # Test cases: (servo_tics, servo_center, expected_radians)
        test_cases = [
            (2048, 2048, 0.0),  # Center position
            (4095, 2048, np.pi),  # Max positive
            (0, 2048, -np.pi),  # Max negative
            (3071, 2048, np.pi/2),  # Quarter turn positive
            (1025, 2048, -np.pi/2),  # Quarter turn negative
        ]
        
        for servo_tics, servo_center, expected_rad in test_cases:
            calculated_rad = (servo_tics - servo_center) * servo_to_radian_scale
            
            if abs(calculated_rad - expected_rad) < 0.01:  # Allow small floating point error
                print(f"  ✓ {servo_tics} tics → {calculated_rad:.3f} rad (expected {expected_rad:.3f})")
            else:
                print(f"  ✗ {servo_tics} tics → {calculated_rad:.3f} rad (expected {expected_rad:.3f})")
                return False
                
        print("  ✓ Position conversion formulas correct")
        return True
        
    except Exception as e:
        print(f"  ✗ Position conversion error: {e}")
        return False

def test_file_structure():
    """Test that all required files are present."""
    print("\nChecking file structure...")
    
    required_files = [
        "single_arx_leader_calib.py",
        "test_arx_calibration.py", 
        "teleop_single_arx_follower.py",
        "ARX_CALIBRATION_README.md"
    ]
    
    all_present = True
    for filename in required_files:
        if os.path.exists(filename):
            print(f"  ✓ {filename}")
        else:
            print(f"  ✗ {filename} - missing")
            all_present = False
            
    return all_present

def test_scservo_sdk():
    """Test scservo SDK availability."""
    print("\nTesting scservo SDK...")
    
    try:
        import scservo_sdk as scs
        print("  ✓ scservo_sdk imported")
        
        # Test basic SDK components
        if hasattr(scs, 'PortHandler'):
            print("  ✓ PortHandler available")
        else:
            print("  ✗ PortHandler missing")
            return False
            
        if hasattr(scs, 'PacketHandler'):
            print("  ✓ PacketHandler available")
        else:
            print("  ✗ PacketHandler missing")
            return False
            
        return True
        
    except ImportError:
        print("  ✗ scservo_sdk not found")
        print("    This is expected if you don't have Feetech SDK installed")
        print("    Install from the scservo_sdk/ directory in this project")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("ARX Calibration System - Quick Test")
    print("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Python Imports", test_imports),
        ("Position Conversion", test_position_conversion),
        ("Calibration File Format", test_calibration_file_format),
        ("scservo SDK", test_scservo_sdk),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        icon = "✓" if result else "✗"
        print(f"{icon} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The calibration system is ready to use.")
        print("\nNext steps:")
        print("1. Connect your leader servo arm")
        print("2. Run: python single_arx_leader_calib.py")
        print("3. Follow the calibration process")
        print("4. Test with: python test_arx_calibration.py")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix the issues above.")
        print("\nCommon solutions:")
        print("- Install missing Python packages")
        print("- Check file paths and permissions")
        print("- Ensure all calibration files are present")
        
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())