# SO101 Robot Teleoperation Suite

A collection of standalone teleoperation scripts for SO101 robots with Feetech STS3215 servos.

## 🚀 Available Systems

### 1. **Local Teleoperation** (USB-connected robots on same computer)
- **Single Pair**: `teleoperate_no_calib_standalone.py` - Control one follower with one leader
- **Multi-Arm**: `teleoperate_multi_arms_standalone.py` - Control 2 followers with 2 leaders, dynamic mapping

### 2. **Internet Teleoperation** (Robots on different computers)
- **PubNub-based**: Real-time control over the internet with <50ms latency
  - `teleoperate_leader_remote.py` - Run on computer with leader robots
  - `teleoperate_follower_remote.py` - Run on computer with follower robots

### 3. **Calibration**
- `set_middle_position_standalone.py` - Set middle positions for all motors

## 📋 Prerequisites

- Python 3.7+
- Feetech SDK (`scservo_sdk`)
- For internet teleoperation: PubNub account (free tier available)

## 🎯 Quick Start

### Local Teleoperation
```bash
# Calibrate robots first
python set_middle_position_standalone.py

# Run teleoperation
python teleoperate_multi_arms_standalone.py
```

### Internet Teleoperation
```bash
# Install dependencies
pip install -r requirements_pubnub.txt

# On leader computer:
python teleoperate_leader_remote.py

# On follower computer:
python teleoperate_follower_remote.py
```

## 📚 Documentation

- `README_standalone.md` - Single robot pair teleoperation
- `README_multi_arms_standalone.md` - Multi-arm teleoperation
- `README_teleoperate_standalone.md` - General teleoperation guide  
- `README_pubnub_teleoperation.md` - Internet teleoperation guide

## 🗂️ Project Structure

```
.
├── Standalone Scripts (Local Control)
│   ├── set_middle_position_standalone.py
│   ├── teleoperate_no_calib_standalone.py
│   └── teleoperate_multi_arms_standalone.py
│
├── Remote Scripts (Internet Control)
│   ├── teleoperate_leader_remote.py
│   ├── teleoperate_follower_remote.py
│   ├── pubnub_config.py
│   └── test_pubnub_connection.py
│
├── Documentation
│   ├── README_*.md files
│   └── requirements_pubnub.txt
│
└── archived/
    └── (Original LeRobot framework files)
```

## 🔧 Hardware Setup

- **Leaders**: SO101 robots powered at 5V (connected via USB)
- **Followers**: SO101 robots powered at 12V (connected via USB)
- All robots use Feetech STS3215 servos with IDs 1-7

## 📝 Notes

- Original LeRobot framework files have been moved to `archived/` folder
- These standalone scripts work without the LeRobot dependencies
- Internet teleoperation uses PubNub for low-latency communication

## 📄 License

Based on the original LeRobot implementation (Apache 2.0) 