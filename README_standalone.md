# Standalone Feetech Set Middle Position Script

This is a standalone script that sets Feetech servo motors to their middle position by configuring homing offsets. It removes dependencies on the lerobot repository and works directly with Feetech motors.

## Features

- **No lerobot dependencies** - Only requires the Feetech SDK and pyserial
- **Supports Feetech motors** (STS, SMS, SCS series)
- **Auto-detects serial ports**
- **Continuous mode** for processing multiple robots
- **Single robot mode** for one-time setup

## Requirements

### Base Dependencies
```bash
pip install pyserial
```

### Feetech SDK
Install the Feetech SDK from their official website:
- Download from: https://www.feetechrc.com/software
- Follow their installation instructions for `scservo_sdk`

## Usage

### Basic Usage
```bash
python set_middle_position_standalone.py --motor_ids=1,2,3 --auto_detect_port
```

### Specify Motor Model
```bash
python set_middle_position_standalone.py --motor_ids=1,2,3 --motor_model=sts3215 --auto_detect_port
```

### Specifying Port Manually
```bash
python set_middle_position_standalone.py --motor_ids=1,2,3 --port=/dev/ttyUSB0
```

### Continuous Mode (Multiple Robots)
```bash
python set_middle_position_standalone.py --motor_ids=1,2,3 --continuous
```

### Single Robot Mode
```bash
python set_middle_position_standalone.py --motor_ids=1,2,3 --single
```

## Command Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--motor_ids` | Yes | Comma-separated list of motor IDs (e.g., `1,2,3`) |
| `--port` | No | Serial port (e.g., `/dev/ttyUSB0`, `COM3`) |
| `--auto_detect_port` | No | Auto-detect the serial port |
| `--motor_model` | No | Motor model (default: `sts3215`) |
| `--baudrate` | No | Baudrate (default: 1000000) |
| `--continuous` | No | Continuous mode for processing multiple robots |
| `--single` | No | Process one robot and exit |

## Supported Motors

| Motor Model | Resolution | Notes |
|-------------|------------|--------|
| `sts3215` | 4096 | Default model |
| `sts3250` | 4096 | Higher torque version |
| `sm8512bl` | 65536 | High resolution |
| `scs0009` | 1024 | Lower resolution |

All motors use Protocol 0 (default for Feetech).

## How It Works

1. **Connect** to the motor bus via serial port
2. **Disable torque** on all motors to allow manual positioning
3. **Set Phase=76 and Lock=0** for all motors
4. **Set operating mode** to position mode (0)
5. **Wait for user** to manually position the device
6. **Read current positions** from all motors
7. **Calculate homing offsets** to make current position the middle:
   - **Formula**: `offset = current_position - (resolution/2)`
8. **Write homing offsets** to motor memory

## Examples

### Example 1: Single SO100 Follower Robot
```bash
python set_middle_position_standalone.py \
  --motor_ids=1,2,3,4,5,6,7 \
  --motor_model=sts3215 \
  --auto_detect_port \
  --single
```

### Example 2: Multiple Robots in Continuous Mode
```bash
python set_middle_position_standalone.py \
  --motor_ids=1,2,3,4,5,6,7 \
  --motor_model=sts3215 \
  --continuous
```

### Example 3: High Resolution Motors
```bash
python set_middle_position_standalone.py \
  --motor_ids=1,2,3 \
  --motor_model=sm8512bl \
  --auto_detect_port
```

### Example 4: Custom Port and Baudrate
```bash
python set_middle_position_standalone.py \
  --motor_ids=1,2,3 \
  --port=/dev/ttyUSB0 \
  --baudrate=57600
```

## Troubleshooting

### Common Issues

1. **"No robot ports detected"**
   - Ensure your robot is connected via USB
   - Check if the port appears in device manager/lsusb
   - Try specifying the port manually with `--port`

2. **"Failed to ping motor X"**
   - Verify the motor ID is correct
   - Check if the motor is powered on
   - Try a different baudrate
   - Ensure only one robot is connected when using auto-detect

3. **"scservo_sdk not installed"**
   - Download and install from Feetech website
   - Follow their SDK installation guide

4. **"Failed to read position from motor X"**
   - Check motor connection and power
   - Verify the correct motor model is specified
   - Try manually specifying the port

### Platform-Specific Notes

- **macOS**: Ports typically appear as `/dev/tty.usbmodem*` or `/dev/tty.usbserial*`
- **Linux**: Ports typically appear as `/dev/ttyUSB*` or `/dev/ttyACM*`
- **Windows**: Ports appear as `COM*` (e.g., `COM3`)

## Script Details

- **Size**: ~300 lines (simplified from original 500+ lines)
- **Dependencies**: Only `pyserial` and `scservo_sdk`
- **Protocol**: Feetech Protocol 0
- **Memory**: Writes to EEPROM (permanent storage)

## What Gets Set

When the script runs, it configures:

1. **Homing Offset**: Makes current position the middle point
2. **Phase**: Set to 76 (Setting byte)
3. **Lock**: Set to 0 (unlocked)
4. **Operating Mode**: Set to 0 (position mode)
5. **Torque**: Disabled during setup, re-enable manually if needed

## License

This script is based on the original lerobot implementation and maintains compatibility with the Apache 2.0 license. 