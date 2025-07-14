# Set Middle Position Standalone Script

## Overview

The `set_middle_position_standalone.py` script has been completely rewritten to follow the **exact logic** from LeRobot's working `set_middle_position.py`. This ensures it works identically to the original LeRobot implementation.

## What It Does

The script sets the middle position (calibration) for Feetech servo motors by:

1. **Disabling torque** - Allows manual positioning
2. **Detecting voltage and setting Phase accordingly**:
   - Leader arm (5V): Phase=76
   - Follower arm (12V): Phase=12
3. **Setting Lock=0** - Required configuration
4. **Setting operating mode to position mode**
5. **Resetting calibration** - Sets homing offset to 0, position limits to full range
6. **Reading current positions** 
7. **Calculating homing offsets** - Using formula: `offset = current_position - (resolution/2)`
8. **Writing homing offsets** - With proper sign-magnitude encoding

## Voltage-Based Phase Setting

The script automatically detects the robot type based on voltage:
- **Leader arms** (~5V): Sets Phase=76
- **Follower arms** (~12V): Sets Phase=12

This ensures proper servo behavior for each robot type.

## Usage

Basic usage (auto-detect port, motor IDs 1-6):
```bash
python set_middle_position_standalone.py
```

Custom motor IDs:
```bash
python set_middle_position_standalone.py --motor_ids=1,2,3,4,5,6
```

Specify port manually:
```bash
python set_middle_position_standalone.py --port=/dev/ttyUSB0
```

Different motor model:
```bash
python set_middle_position_standalone.py --motor_model=sts3250
```

## Key Implementation Details

- **Exact LeRobot Logic**: The script implements a simplified `FeetechBus` class that follows the exact same logic as LeRobot's `FeetechMotorsBus`
- **Sign-Magnitude Encoding**: Homing offsets are properly encoded using 11-bit sign-magnitude format
- **Motor Models Supported**: sts3215, sts3250, sm8512bl, scs0009
- **Protocol**: Uses Feetech Protocol 0
- **Automatic Voltage Detection**: Reads motor voltage to determine appropriate Phase value

## Important Notes

1. **Power Cycle May Be Required**: Some Feetech motors require a power cycle for the new calibration to take effect
2. **Phase Value**: Automatically set based on voltage (76 for leaders, 12 for followers)
3. **Middle Position**: After calibration, motors will read ~2048 (for 4096 resolution motors) at their calibrated position
4. **Status Packet Warnings**: Warnings about "no status packet" are normal for EEPROM writes on Feetech motors

## Differences from Previous Version

The previous version tried to "improve" on LeRobot's logic but introduced issues. This version:
- Copies LeRobot's exact algorithm
- Adds voltage detection for appropriate Phase values
- Follows the exact order of operations from LeRobot
- Uses the same register addresses and encoding

## Troubleshooting

If calibration doesn't seem to work:
1. Power cycle the motors
2. Run `monitor_positions_standalone.py --diagnostics` to check homing offsets
3. Ensure motors are properly connected and powered
4. Verify the correct Phase value was set (76 for leaders, 12 for followers)

## Source Reference

This script is based on:
- `archived/set_middle_position.py` 
- `archived/lerobot/common/motors/motors_bus.py`
- `archived/lerobot/common/motors/feetech/feetech.py` 