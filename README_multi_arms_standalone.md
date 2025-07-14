# Multi-Arm SO101 Teleoperation Script

This is a standalone teleoperation script for multiple SO101 robots with Feetech STS3215 servos. It supports **2 leader robots (5V)** and **2 follower robots (12V)** with dynamic mapping that can be switched during operation.

## Features

- **No lerobot dependencies** - Only requires the Feetech SDK and pyserial
- **4-robot support** - 2 leaders + 2 followers simultaneously
- **Automatic voltage-based identification** - Distinguishes leaders from followers
- **Dynamic mapping** - Switch which leader controls which follower with 's' key
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

1. **Set middle positions** on all 4 robots using `set_middle_position_standalone.py`
2. **Ensure proper voltages** - 2 leaders at 5V, 2 followers at 12V
3. **Connect all 4 robots** via USB to the same computer

## Usage

### Basic Usage (Auto-detect all 4 robots)
```bash
python teleoperate_multi_arms_standalone.py
```

### Custom Motor Configuration
```bash
python teleoperate_multi_arms_standalone.py --motor_ids=1,2,3,4,5,6,7 --fps=30
```

### Silent Mode (No Display)
```bash
python teleoperate_multi_arms_standalone.py --no_display
```

### Timed Session
```bash
python teleoperate_multi_arms_standalone.py --duration=120  # Run for 2 minutes
```

## Command Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--motor_ids` | `1,2,3,4,5,6,7` | Comma-separated list of motor IDs |
| `--baudrate` | `1000000` | Serial communication baudrate |
| `--fps` | `60` | Target loop frequency (Hz) |
| `--duration` | Infinite | Session duration in seconds |
| `--no_display` | False | Disable real-time data display |

## How It Works

### 1. Robot Detection and Identification
```
Step 1: Scan for 4 USB ports
Step 2: Connect to each port and read motor voltage
Step 3: Classify robots:
  - 5V robots → Leaders
  - 12V robots → Followers
Step 4: Verify exactly 2 leaders and 2 followers found
```

### 2. Initial Random Mapping
The script creates a random initial mapping between leaders and followers:
```
Example:
  Leader1 → Follower2
  Leader2 → Follower1
```

### 3. Dynamic Mapping Control
- **Press 's'** to switch the mapping (swap assignments)
- **Press Ctrl+C** to stop the program

### 4. Real-Time Teleoperation
- Reads positions from both leaders simultaneously
- Sends positions to mapped followers in real-time
- Maintains specified loop rate (default: 60 Hz)

## Real-Time Display

When display is enabled (default), the script shows:

```
======================================================================
CURRENT MAPPING:
  Leader1 → Follower2
  Leader2 → Follower1
======================================================================

Leader1 → Follower2:
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

Leader2 → Follower1:
--------------------------------------------------
MOTOR ID   |  RAW VALUE |     %
--------------------------------------------------
1          |       1800 |  44.0%
2          |       2200 |  53.7%
3          |       2500 |  61.0%
4          |       1900 |  46.4%
5          |       2100 |  51.2%
6          |       1950 |  47.6%
7          |       2000 |  48.8%

Loop time: 16.67ms (60 Hz)
Press 's' to switch mapping, Ctrl+C to stop
```

## Examples

### Example 1: Basic Multi-Arm Teleoperation
```bash
python teleoperate_multi_arms_standalone.py
```

### Example 2: High-Speed Mode with Custom Motors
```bash
python teleoperate_multi_arms_standalone.py --motor_ids=1,2,3,4,5,6 --fps=120 --no_display
```

### Example 3: Demo Mode (Short Duration)
```bash
python teleoperate_multi_arms_standalone.py --duration=60 --fps=30
```

## Mapping Control

### Switching Mapping
1. **During operation**, press the **'s' key** to switch mapping
2. The display will update to show the new mapping:
   ```
   🔄 Mapping switched:
     Leader1 → Follower1
     Leader2 → Follower2
   ```
3. Continue operating with new mapping
4. Press **'s'** again to switch back

### Mapping Logic
- **Initial**: Random assignment of leaders to followers
- **Switch**: Swaps the two assignments
- **Example**:
  - Before: `Leader1→Follower1, Leader2→Follower2`
  - After: `Leader1→Follower2, Leader2→Follower1`

## Troubleshooting

### Common Issues

1. **"Found X ports, but need 4 robots"**
   - Ensure all 4 robots are connected via USB
   - Check device manager/lsusb for available ports
   - Try different USB cables or ports

2. **"Expected 2 leader robots (5V), found X"**
   - Verify exactly 2 robots have 5V power supply
   - Check power connections and voltage regulators
   - Ensure leaders are not accidentally powered by 12V

3. **"Expected 2 follower robots (12V), found X"**
   - Verify exactly 2 robots have 12V power supply
   - Check that followers are not accidentally powered by 5V
   - Ensure proper power distribution

4. **"Failed to ping motor X"**
   - Verify motor IDs match your robot configuration
   - Check motor power and connections
   - Try lower baudrate if communication is unstable

5. **"Keyboard input not supported"**
   - System doesn't support real-time keyboard input
   - Mapping switching won't work, but teleoperation continues
   - Use Ctrl+C to stop the program

6. **Jerky/inconsistent movement**
   - Lower the FPS to reduce CPU load
   - Check for USB bandwidth limitations with 4 robots
   - Ensure stable power supply to all robots

### Performance Optimization

- **High FPS**: Use `--no_display` for maximum performance
- **Stable operation**: Keep FPS ≤ 60 for most systems
- **USB bandwidth**: Consider using powered USB hubs for 4 robots
- **Latency**: Minimize USB cable lengths

## Workflow Integration

### 1. Setup Phase (All 4 Robots)
```bash
# Set middle positions on each robot individually
python set_middle_position_standalone.py --motor_ids=1,2,3,4,5,6,7 --auto_detect_port
# Repeat 4 times, once per robot
```

### 2. Multi-Arm Teleoperation
```bash
# Start 4-robot teleoperation
python teleoperate_multi_arms_standalone.py
```

### 3. Mapping Control During Operation
- Press **'s'** to switch which leader controls which follower
- Continue switching as needed during operation
- Use **Ctrl+C** to stop when done

## Technical Details

### System Requirements
- **USB ports**: 4 available USB ports (or hub)
- **CPU**: Multi-core recommended for 60+ Hz
- **RAM**: Minimal (each robot uses ~1MB)
- **OS**: Windows, macOS, Linux

### Communication
- **Protocol**: Feetech Protocol 0
- **Baudrate**: 1 Mbps per robot
- **Concurrent connections**: 4 simultaneous serial connections
- **Data rate**: ~240 bytes/s per robot at 60 Hz

### Robot Identification
- **Voltage reading**: Automatic via Present_Voltage register
- **Leader threshold**: 4.5-5.5V
- **Follower threshold**: 11-13V
- **Tolerance**: ±0.5V for reliable identification

## Safety Considerations

- **Power isolation**: Ensure proper voltage separation (5V vs 12V)
- **Emergency stop**: Always be ready to use Ctrl+C
- **Manual override**: Leaders can be moved manually if torque is disabled
- **Collision avoidance**: User responsibility - no automatic collision detection

## Limitations

- **Fixed robot count**: Exactly 4 robots (2+2) required
- **No force feedback**: Position mirroring only
- **Single mapping switch**: Only swaps the two pairs
- **No recording**: Real-time operation only
- **Platform dependent**: Keyboard switching may not work on all systems

## License

This script is based on the original lerobot implementation and maintains compatibility with the Apache 2.0 license. 