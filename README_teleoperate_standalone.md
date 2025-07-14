# Standalone SO101 Teleoperation Script

This is a standalone teleoperation script for SO101 robots with Feetech STS3215 servos. It removes dependencies on the lerobot repository and performs teleoperation using raw encoder values without calibration files.

## Features

- **No lerobot dependencies** - Only requires the Feetech SDK and pyserial
- **Automatic voltage-based identification** - Distinguishes leader (5V) from follower (12V) robots
- **Auto-detects serial ports**
- **Real-time position mirroring** using raw encoder values (0-4095)
- **Configurable loop rate** and display options

## Requirements

### Base Dependencies
```bash
pip install pyserial
```

### Feetech SDK
Install the Feetech SDK from their official website:
- Download from: https://www.feetechrc.com/software
- Follow their installation instructions for `scservo_sdk`

## Prerequisites

Before using this script, you must:

1. **Set middle positions** on both robots using the `set_middle_position_standalone.py` script
2. **Ensure proper voltage** - Leader should be 5V, follower should be 12V
3. **Connect both robots** via USB

## Usage

### Basic Usage (Auto-detect)
```bash
python teleoperate_no_calib_standalone.py
```

### Specify Ports Manually
```bash
python teleoperate_no_calib_standalone.py --leader_port=/dev/ttyUSB0 --follower_port=/dev/ttyUSB1
```

### Custom Motor Configuration
```bash
python teleoperate_no_calib_standalone.py --motor_ids=1,2,3,4,5,6,7 --fps=30
```

### Silent Mode (No Display)
```bash
python teleoperate_no_calib_standalone.py --no_display
```

### Timed Session
```bash
python teleoperate_no_calib_standalone.py --duration=60  # Run for 60 seconds
```

## Command Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--motor_ids` | `1,2,3,4,5,6,7` | Comma-separated list of motor IDs |
| `--leader_port` | Auto-detect | Serial port for leader robot (5V) |
| `--follower_port` | Auto-detect | Serial port for follower robot (12V) |
| `--baudrate` | `1000000` | Serial communication baudrate |
| `--fps` | `60` | Target loop frequency (Hz) |
| `--duration` | Infinite | Session duration in seconds |
| `--no_display` | False | Disable real-time data display |

## How It Works

### 1. Robot Identification
The script automatically identifies which robot is the leader vs follower by reading their supply voltage:
- **Leader**: 5V supply (tolerance: 4.5-5.5V)
- **Follower**: 12V supply (tolerance: 11-13V)

### 2. Connection Process
1. Detects available USB serial ports
2. Tests each port by connecting and reading voltage
3. Assigns roles based on voltage readings
4. Establishes connections to both robots

### 3. Teleoperation Loop
1. **Read positions** from leader robot (raw values 0-4095)
2. **Send positions** directly to follower robot
3. **Display data** (optional) showing motor positions and percentages
4. **Maintain timing** at specified FPS

### 4. Raw Value Range
- **STS3215 servos**: 4096 positions (0-4095)
- **No normalization** - uses raw encoder values directly
- **Direct mirroring** - leader position → follower position

## Motor Configuration

### Default SO101 Configuration
```
Motor ID 1: Base rotation
Motor ID 2: Shoulder joint
Motor ID 3: Elbow joint
Motor ID 4: Wrist 1
Motor ID 5: Wrist 2
Motor ID 6: Wrist 3
Motor ID 7: Gripper
```

## Real-Time Display

When display is enabled (default), the script shows:

```
--------------------------------------------------
MOTOR ID   |  RAW VALUE |     %
--------------------------------------------------
1          |       2048 |  50.0%
2          |       1024 |  25.0%
3          |       3072 |  75.0%
4          |       2048 |  50.0%
5          |       2048 |  50.0%
6          |       2048 |  50.0%
7          |       2048 |  50.0%

Loop time: 16.67ms (60 Hz)
```

## Examples

### Example 1: Basic Teleoperation
```bash
python teleoperate_no_calib_standalone.py
```

### Example 2: High-Speed Mode
```bash
python teleoperate_no_calib_standalone.py --fps=120 --no_display
```

### Example 3: Custom Motor Configuration
```bash
python teleoperate_no_calib_standalone.py --motor_ids=1,2,3,4,5,6 --fps=30
```

### Example 4: Development Testing
```bash
python teleoperate_no_calib_standalone.py --duration=30 --fps=10
```

## Troubleshooting

### Common Issues

1. **"No robot ports detected"**
   - Ensure both robots are connected via USB
   - Check device manager/lsusb for available ports
   - Try specifying ports manually

2. **"No leader/follower robot detected"**
   - Verify robot supply voltages (5V for leader, 12V for follower)
   - Check power connections and voltage regulators
   - Ensure motors are receiving proper power

3. **"Failed to ping motor X"**
   - Verify motor IDs match your robot configuration
   - Check motor power and connections
   - Try different baudrate if needed

4. **"Connection failed"**
   - Ensure only one script is accessing each port
   - Close other serial connections to the robots
   - Try different USB cables or ports

5. **Jerky/inconsistent movement**
   - Lower the FPS if CPU usage is high
   - Check for loose connections
   - Ensure stable power supply

### Platform-Specific Notes

- **macOS**: Ports appear as `/dev/tty.usbmodem*`
- **Linux**: Ports appear as `/dev/ttyUSB*` or `/dev/ttyACM*`  
- **Windows**: Ports appear as `COM*`

## Technical Details

### Performance
- **Loop rate**: Up to 120 Hz (depending on system)
- **Latency**: <20ms typical (leader read → follower write)
- **Position resolution**: 12-bit (4096 positions)

### Communication
- **Protocol**: Feetech Protocol 0
- **Baudrate**: 1 Mbps (default)
- **Data format**: 16-bit position values
- **Error handling**: Automatic retry on communication failures

### Safety Features
- **Position clamping**: Values kept within 0-4095 range
- **Connection verification**: Pings all motors before starting
- **Graceful shutdown**: Proper disconnection on Ctrl+C
- **Error logging**: Detailed error messages for troubleshooting

## Workflow Integration

### 1. Setup Phase
```bash
# Set middle positions on both robots
python set_middle_position_standalone.py --motor_ids=1,2,3,4,5,6,7 --auto_detect_port

# Repeat for second robot
python set_middle_position_standalone.py --motor_ids=1,2,3,4,5,6,7 --auto_detect_port
```

### 2. Teleoperation Phase
```bash
# Start teleoperation
python teleoperate_no_calib_standalone.py
```

### 3. Production Use
```bash
# Silent mode for manufacturing
python teleoperate_no_calib_standalone.py --no_display --fps=60
```

## Limitations

- **No force feedback** - Only position mirroring
- **No collision detection** - User responsibility
- **Single robot pair** - Cannot handle multiple pairs simultaneously
- **No recording/playback** - Real-time operation only

## License

This script is based on the original lerobot implementation and maintains compatibility with the Apache 2.0 license. 