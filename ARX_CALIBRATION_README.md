# ARX Leader-Follower Calibration Guide

This document explains how to calibrate the leader servo arm (Waveshare + SC servos) with the ARX R5 follower arm for accurate teleoperation.

## Overview

The calibration system establishes position correspondence between:
- **Leader arm**: Waveshare servo driver with 7 SC servos (0-4095 tic positions)
- **Follower arm**: ARX R5 robotic arm (radians for joint positions)

## Why Calibration is Needed

The current teleoperation assumes all servos have a center position of 2048 tics, which corresponds to the ARX arm's home position. In reality:

1. **Servo mechanical zero** ≠ **ARX home position**
2. **Each servo** may have different zero offsets
3. **Joint directions** may need reversal or scaling adjustments

Calibration determines the correct servo positions that correspond to the ARX home pose, allowing accurate position mapping during teleoperation.

## Files Created

- `single_arx_leader_calib.py` - Main calibration script
- `test_arx_calibration.py` - Test suite for validation
- `arx_leader_calibration.json` - Saved calibration data
- `ARX_CALIBRATION_README.md` - This documentation

## Quick Start

### 1. Prepare Both Arms

**ARX R5 Follower:**
```bash
# Connect ARX arm and run home command
# (This must be done separately due to OS compatibility)
python -c "
from arx_control import ARXArm
arm = ARXArm({'can_port': 'can0', 'type': 1})
arm.go_home()
print('ARX arm at home position')
"
```

**Leader Servo Arm:**
- Connect Waveshare servo driver via USB
- Ensure all 7 servos are connected and powered

### 2. Run Calibration

```bash
# Basic calibration (auto-detects port)
python single_arx_leader_calib.py

# Specify port and motor IDs
python single_arx_leader_calib.py --port /dev/ttyUSB0 --motor_ids 1,2,3,4,5,6,7
```

### 3. Calibration Process

1. **Position the leader arm** to match the ARX R5 home pose
2. **Verify alignment** - all joints should match ARX home position
3. **Capture calibration** when positions look correct
4. **Save calibration** to `arx_leader_calibration.json`

### 4. Test Calibration

```bash
# Run all tests
python test_arx_calibration.py

# Test specific functionality
python test_arx_calibration.py --test live_preview
```

### 5. Use in Teleoperation

```bash
# Follower side (uses calibration automatically)
python teleop_single_arx_follower.py --calibration_file arx_leader_calibration.json

# Leader side (unchanged)
python teleop_single_arx_leader.py
```

## Detailed Calibration Process

### Understanding the Coordinate Systems

**Leader Servo Positions:**
- Range: 0-4095 tics (4096 resolution)
- Middle: ~2048 tics (theoretical)
- Direction: Varies by servo installation

**ARX Joint Positions:**
- Range: ±π radians (typically)
- Home: All joints at specific predefined angles
- Direction: Right-hand rule coordinate system

### Calibration Formula

The position conversion uses:
```python
# Servo tics → ARX radians
arx_radians = (servo_tics - servo_center) * (2π / 4095)

# Where servo_center is determined by calibration
```

### Manual Positioning Guide

When positioning the leader arm to match ARX home:

1. **Base rotation** (Joint 1): Match base orientation
2. **Shoulder** (Joint 2): Match shoulder angle 
3. **Elbow** (Joint 3): Match elbow bend
4. **Wrist pitch** (Joint 4): Match wrist pitch
5. **Wrist roll** (Joint 5): Match wrist roll
6. **Wrist yaw** (Joint 6): Match wrist yaw
7. **Gripper** (Joint 7): Match gripper rotation

**Tips:**
- Take photos of ARX home position for reference
- Move one joint at a time
- Check alignment from multiple angles
- Fine-tune after initial positioning

## Calibration File Format

```json
{
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
  "is_leader": true,
  "notes": "Leader arm home positions corresponding to ARX R5 home pose"
}
```

## Testing and Validation

### Test Suite

```bash
# Test servo communication
python test_arx_calibration.py --test communication

# Test position mapping
python test_arx_calibration.py --test mapping

# Test calibration file I/O
python test_arx_calibration.py --test file_io

# Live preview of calibration
python test_arx_calibration.py --test live_preview
```

### Validation Checklist

- [ ] All 7 servos respond to commands
- [ ] Voltage detection works (5V for leader)
- [ ] Position readings are stable
- [ ] Calibration file saves/loads correctly
- [ ] Live preview shows reasonable joint angles
- [ ] Teleoperation uses calibration data

## Troubleshooting

### Connection Issues

**"No robot ports detected"**
- Check USB connection
- Verify servo driver power
- Try different USB port
- Check port permissions: `sudo chmod 666 /dev/ttyUSB*`

**"Failed to ping motor X"**
- Check servo power and connections
- Verify motor ID configuration
- Try different baudrate: `--baudrate 115200`

### Calibration Issues

**"Position unstable"**
- Check mechanical connections
- Reduce electrical interference
- Use shielded USB cable

**"Calibration doesn't match ARX"**
- Re-verify ARX home position
- Check joint direction/polarity
- Consider mechanical differences

### Teleoperation Issues

**"Calibration file not found"**
- Run calibration first
- Check file path and permissions
- Use `--calibration_file` parameter

**"Follower arm moves erratically"**
- Verify calibration quality
- Check for servo direction reversal
- Test with small movements first

## Advanced Configuration

### Custom Motor IDs

```bash
# Non-standard motor ID sequence
python single_arx_leader_calib.py --motor_ids 2,4,6,8,10,12,14
```

### Multiple Calibrations

```bash
# Different calibration files for different setups
python single_arx_leader_calib.py --calibration_file setup_a.json
python single_arx_leader_calib.py --calibration_file setup_b.json

# Use specific calibration in teleoperation
python teleop_single_arx_follower.py --calibration_file setup_a.json
```

### Joint Direction Reversal

If a joint moves in the wrong direction, modify the calibration:

```python
# In the calibration file, servo positions can be adjusted
# Or modify the conversion formula in teleop_single_arx_follower.py
rad_pos = -(tic_pos - servo_center) * self.servo_to_radian_scale  # Reverse direction
```

## Safety Considerations

### Before Calibration
- Ensure both arms have sufficient clearance
- Check power supply stability
- Have emergency stop readily available

### During Calibration
- Move joints slowly and carefully
- Stop if any unusual behavior occurs
- Keep hands clear of moving parts

### After Calibration
- Test with small movements first
- Monitor both arms during initial teleoperation
- Be prepared to emergency stop

## Performance Tips

### Optimal Calibration
- Take time to align positions precisely
- Calibrate in good lighting conditions
- Use consistent reference points
- Document any unusual configurations

### Teleoperation Performance
- Use calibration-aware position smoothing
- Monitor for drift over time
- Re-calibrate if performance degrades
- Keep calibration files backed up

## Future Improvements

### Automated Calibration
- Computer vision alignment detection
- Automatic joint direction detection
- Dynamic calibration adjustment

### Enhanced Validation
- Cross-validation with multiple poses
- Accuracy metrics and reporting
- Calibration quality scoring

## Support

For issues or questions:
1. Check this documentation
2. Run the test suite for diagnostics
3. Review log files for error details
4. Test with minimal configurations first

Remember: Good calibration is essential for smooth teleoperation!