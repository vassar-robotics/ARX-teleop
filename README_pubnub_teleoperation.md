# PubNub-Based Internet Teleoperation for SO101 Robots

This system enables teleoperation of SO101 robot arms over the internet using PubNub's real-time messaging infrastructure.

## Architecture Overview

```
Location A (Leader Side)              Internet               Location B (Follower Side)
┌─────────────────────┐         ┌─────────────┐         ┌──────────────────────┐
│  2x Leader Arms     │         │   PubNub    │         │  2x Follower Arms    │
│     (5V USB)        │ ──────> │   Cloud     │ ──────> │    (12V USB)         │
│                     │         │   Relay     │         │                      │
│ teleoperate_leader_ │         └─────────────┘         │ teleoperate_follower_│
│    remote.py        │                                  │     remote.py        │
└─────────────────────┘                                  └──────────────────────┘
```

## Features

- **Real-time teleoperation** over the internet with <50ms latency
- **Automatic robot detection** based on voltage (5V leaders, 12V followers)
- **Safety features**: Maximum latency limits, position smoothing, rate limiting
- **Network monitoring**: Real-time latency, packet loss, and connection status
- **Bidirectional communication**: Acknowledgments and status updates
- **Efficient data transfer**: Uses msgpack for binary serialization

## Prerequisites

1. **Hardware Setup**:
   - 2 SO101 leader robots powered at 5V (Location A)
   - 2 SO101 follower robots powered at 12V (Location B)
   - All robots must have middle positions set using `set_middle_position_standalone.py`

2. **Software Dependencies**:
   ```bash
   pip install -r requirements_pubnub.txt
   ```

3. **PubNub Account** (Optional for production):
   - Sign up at https://dashboard.pubnub.com/
   - Get your publish and subscribe keys
   - Update `pubnub_config.py` with your keys

## Quick Start

### 1. Install Dependencies

```bash
# Install required packages
pip install pubnub pyserial msgpack colorama

# Install Feetech SDK (follow manufacturer instructions)
```

### 2. Configure PubNub (Optional)

Edit `pubnub_config.py` to use your own PubNub keys:

```python
# Replace demo keys with your own
PUBLISH_KEY = "your-publish-key"
SUBSCRIBE_KEY = "your-subscribe-key"
```

The demo keys work for testing but have limitations.

### 3. Start Leader Side (Location A)

On the computer with leader robots:

```bash
python teleoperate_leader_remote.py
```

You should see:
```
INFO: Setting up PubNub connection...
INFO: ✓ PubNub connected as leader-Mac.local
INFO: Found 2 serial ports
INFO: ✓ Leader robot found at /dev/tty.usbmodem1234 (5.0V)
INFO: ✓ Leader robot found at /dev/tty.usbmodem5678 (5.1V)
INFO: ✓ Connected to 2 leader robots
INFO: Starting teleoperation at 60 Hz...
```

### 4. Start Follower Side (Location B)

On the computer with follower robots:

```bash
python teleoperate_follower_remote.py
```

You should see:
```
INFO: Setting up PubNub connection...
INFO: ✓ PubNub connected as follower-PC
INFO: ✓ Connected to PubNub channels
INFO: Found 2 serial ports
INFO: ✓ Follower robot found at COM3 (12.0V)
INFO: ✓ Follower robot found at COM4 (12.1V)
INFO: ✓ Connected to 2 follower robots
```

## Real-Time Monitoring

Both sides display real-time statistics:

### Leader Display
```
=== LEADER TELEOPERATION ===
Connected Leaders: 2

Network Statistics:
  Average Latency: 35.2ms
  Max Latency:     48.1ms
  Packet Loss:     0.0%
  Messages Sent:   1523
  Publish Rate:    59.8 Hz

Follower Status:
  follower-PC: Connected, 14 motors active

Press Ctrl+C to stop
```

### Follower Display
```
=== FOLLOWER TELEOPERATION ===
Connected Followers: 2

Current Mapping:
  Leader1 → Follower1
  Leader2 → Follower2

Network Statistics:
  Average Latency: 35.2ms
  Max Latency:     48.1ms
  Received:        1523
  Dropped:         0
  Update Rate:     59.8 Hz
  Status:          Connected (last data 0.0s ago)

Press Ctrl+C to stop
```

## Command Line Options

### Leader Side
```bash
python teleoperate_leader_remote.py --help

Options:
  --motor_ids    Comma-separated motor IDs (default: 1,2,3,4,5,6,7)
  --baudrate     Serial baudrate (default: 1000000)
  --fps          Target update rate in Hz (default: 60)
```

### Follower Side
```bash
python teleoperate_follower_remote.py --help

Options:
  --motor_ids    Comma-separated motor IDs (default: 1,2,3,4,5,6,7)
  --baudrate     Serial baudrate (default: 1000000)
```

## Safety Features

1. **Maximum Latency Protection**: 
   - Rejects commands if latency > 200ms (configurable)
   - Prevents delayed movements that could be dangerous

2. **Position Smoothing**:
   - Exponential smoothing prevents jerky movements
   - Maximum position change per update limited to 200 (configurable)

3. **Connection Monitoring**:
   - Automatic status updates every 2 seconds
   - Visual indicators for connection quality
   - Automatic reconnection on network failures

4. **Graceful Shutdown**:
   - Proper cleanup on Ctrl+C
   - Sends disconnect notification to other side

## Network Requirements

- **Bandwidth**: ~50-100 KB/s per direction at 60Hz
- **Latency**: Best experience with <100ms RTT
- **Ports**: Only outbound HTTPS (443) required
- **Firewall**: Works through most firewalls/NAT

## Troubleshooting

### "PubNub not installed"
```bash
pip install pubnub>=10.4.1
```

### "Found 0 ports, but need 2 robots"
- Check USB connections
- Ensure robots are powered on
- Try `ls /dev/tty.*` (Mac) or `ls /dev/ttyUSB*` (Linux)

### High Latency Warning
- Check internet connection quality
- Try reducing FPS: `--fps=30`
- Consider geographic distance between locations

### "Expected 2 leader robots, found X"
- Verify robot power supplies (5V for leaders, 12V for followers)
- Check voltage regulators
- Use multimeter to confirm voltages

### Connection Lost
- PubNub automatically reconnects
- Check internet connectivity
- Verify PubNub keys are valid

## Performance Tuning

### For Lower Latency
```python
# In pubnub_config.py
TARGET_FPS = 30  # Reduce update rate
POSITION_SMOOTHING = 0.5  # Less smoothing
```

### For Smoother Motion
```python
# In pubnub_config.py
POSITION_SMOOTHING = 0.9  # More smoothing
MAX_POSITION_CHANGE = 100  # Smaller max changes
```

### For Unreliable Networks
```python
# In pubnub_config.py
MAX_LATENCY_MS = 500  # Higher tolerance
RECONNECT_DELAY_S = 5  # Longer reconnect delay
```

## Production Deployment

1. **Get PubNub Production Keys**:
   - Sign up at https://dashboard.pubnub.com/
   - Create a new app and keyset
   - Enable required features (Presence, Message Persistence)

2. **Update Configuration**:
   ```python
   # pubnub_config.py
   PUBLISH_KEY = "pub-c-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
   SUBSCRIBE_KEY = "sub-c-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
   ```

3. **Security Considerations**:
   - Use PubNub Access Manager for authentication
   - Implement encryption for sensitive data
   - Monitor usage and set up alerts

4. **Scaling**:
   - PubNub handles millions of connections
   - Consider channel naming for multiple robot pairs
   - Implement session management for multiple operators

## Advanced Features (Future)

- **Dynamic Mapping**: Switch leader-follower pairs during operation
- **Recording/Playback**: Save and replay teleoperation sessions
- **Multi-site Support**: Connect more than 2 locations
- **Force Feedback**: Add haptic feedback to leaders
- **Web Dashboard**: Monitor all robots from browser
- **Mobile Control**: Control from smartphone app

## Technical Details

### Message Protocol
```python
# Telemetry Message (Leader → Follower)
{
    "type": "telemetry",
    "timestamp": 1234567890.123,
    "sequence": 12345,
    "positions": {
        "Leader1": {1: 2048, 2: 1024, ...},
        "Leader2": {1: 1800, 2: 2200, ...}
    }
}

# Acknowledgment (Follower → Leader)
{
    "type": "ack",
    "sequence": 12345,
    "timestamp": 1234567890.123,
    "follower_id": "follower-hostname"
}

# Status Update (Follower → Leader)
{
    "type": "status",
    "timestamp": 1234567890.123,
    "follower_id": "follower-hostname",
    "motors_active": 14,
    "followers_connected": 2
}
```

### PubNub Channels
- `robot-telemetry`: Position data stream
- `robot-status`: Status updates and acknowledgments
- `robot-control`: Future control commands

## License

This implementation extends the original lerobot teleoperation system with internet capabilities.
Maintains compatibility with Apache 2.0 license. 

# Requirements

- Python 3.8+
- Two computers with internet connection
- USB-to-TTL converters for robot connections
- PubNub account (free tier is sufficient)

## USB Permissions on Linux/Ubuntu

On Linux systems, USB serial devices require special permissions. The follower script will attempt to handle this automatically, but for a permanent solution:

### Quick Setup (Recommended)
```bash
# Run the provided setup script
sudo chmod +x setup_usb_permissions_linux.sh
sudo ./setup_usb_permissions_linux.sh
```

### Manual Setup
If you prefer to set up manually:

1. **Add your user to the dialout group:**
   ```bash
   sudo usermod -a -G dialout $USER
   # Log out and back in for this to take effect
   ```

2. **Or create a udev rule (permanent fix):**
   ```bash
   # Create the rules file
   sudo nano /etc/udev/rules.d/99-robot-usb-serial.rules
   
   # Add these lines:
   SUBSYSTEM=="tty", KERNEL=="ttyUSB[0-9]*", MODE="0666"
   SUBSYSTEM=="tty", KERNEL=="ttyACM[0-9]*", MODE="0666"
   
   # Reload rules
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

The follower script will guide you through this process if needed. 