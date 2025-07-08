# Quick Start Guide - Batch Robot Setup

## 🚀 Running the Pipeline

### Option 1: Using the shell script (Recommended)
```bash
./run_batch_setup.sh
```

### Option 2: Manual activation
```bash
conda activate calib
python batch_robot_setup.py
```

## 📋 Process Overview

For each robot pair:

1. **Connect robots** - Plug in both leader (5V) and follower (12V) via USB
2. **Press SPACE** - When both are connected
3. **Position follower** - Move to middle position, press ENTER
4. **Position leader** - Move to middle position, press ENTER  
5. **Press ENTER** - Confirm to start teleoperation test
6. **Watch test** - 10-second teleoperation verification
7. **Disconnect** - Unplug both robots
8. **Repeat** - Connect next pair

## ⚙️ Common Options

```bash
# Process 10 robot sets instead of 40
./run_batch_setup.sh --max_sets=10

# Skip teleoperation test (faster)
./run_batch_setup.sh --skip_teleoperation_test

# Shorter test duration
./run_batch_setup.sh --teleoperation_test_duration=5.0
```

## 🔍 What's Happening

- **Follower (12V)**: Only middle position is set
- **Leader (5V)**: Middle position + Phase=76 + Lock=0

## ⚡ Tips

- Have all robot pairs ready nearby
- Position arms in neutral, balanced pose
- The script tracks your progress automatically
- Press 'q' instead of SPACE to quit anytime
- Press Ctrl+C for emergency stop 