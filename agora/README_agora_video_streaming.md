# Agora Video Streaming Solution

This solution provides low-latency video streaming of 3 camera feeds from a follower client to a leader client using Agora's Video SDK. Perfect for robotic teleoperation over the internet with recording capabilities.

## Features

- **Ultra-low latency**: 200-400ms between Asia and US
- **3 simultaneous video streams**: Each camera gets its own channel at 480p @ 30fps
- **Cross-platform GUI**: Works on both macOS and Ubuntu
- **Smart camera selection**: Automatically detects all available cameras
- **Simple setup**: Pre-configured with Agora App ID
- **Recording ready**: Built-in support for cloud recording
- **Bandwidth adaptive**: Dual stream support for network adaptation

## Prerequisites

1. **Python 3.8+** installed
2. **Cameras**: 3 or more USB cameras or webcams connected to the follower computer

## Installation

1. Navigate to the agora folder:
```bash
cd agora
```

2. Install the required packages:
```bash
pip install -r requirements_agora.txt
```

## Configuration

The Agora App ID is already configured in `agora_config.py`. If you need to use a different App ID, edit the file:

```python
APP_ID = "your-app-id-here"
```

## Usage

You can use either desktop applications or web-based interfaces:

### Option 1: Desktop Applications

#### On the Follower Computer (Robot side):

1. Connect your cameras to the computer
2. Navigate to the agora folder and run:
```bash
cd agora
python video_stream_follower.py
```
3. Click "Detect Cameras" to find all available cameras
4. Select which 3 cameras you want to use from the dropdown menus
5. Click "Start Streaming"

#### On the Leader Computer (Operator side):

1. Navigate to the agora folder and run:
```bash
cd agora
python video_stream_leader.py
```
2. Click "Start Receiving"
3. You should see 3 video feeds from the follower at 480p resolution

### Option 2: Web-Based Interfaces

#### On the Follower Computer (Robot side):

1. Connect your cameras to the computer
2. Navigate to the agora folder and run:
```bash
cd agora
python video_stream_follower_web.py
```
3. A browser will open at http://127.0.0.1:5002
4. Select your cameras from the dropdown menus
5. Click "Start Streaming"

#### On the Leader Computer (Operator side):

1. Navigate to the agora folder and run:
```bash
cd agora
python video_stream_leader_web.py
```
2. A browser will open at http://127.0.0.1:5001
3. Click "Start Receiving"
4. You should see 3 video feeds from the follower

## Camera Selection

The follower application now features automatic camera detection:
- Click "Detect Cameras" to scan for all available cameras
- Each detected camera shows its resolution and FPS
- Select your preferred 3 cameras from the dropdown menus
- The system remembers your selection for the session

## Network Requirements

- **Bandwidth**: ~2-3 Mbps upload (follower) and download (leader) for 480p
- **Ports**: Agora uses standard web ports (80, 443) and UDP ports
- **Firewall**: Allow outbound connections to Agora's servers

## Recording Videos

The leader interface has a "Start Recording" button. To enable cloud recording:

1. Enable cloud recording in your Agora project settings
2. Set up storage (S3, Azure, etc.) in Agora Console
3. Update `agora_config.py`:
```python
ENABLE_CLOUD_RECORDING = True
RECORDING_BUCKET = "your-s3-bucket"
RECORDING_REGION = "us-west-2"
```

## Troubleshooting

### "No cameras detected!"
- Check all camera connections
- On Linux, ensure you have permissions: `sudo usermod -a -G video $USER`
- Try unplugging and reconnecting cameras
- Some virtual cameras may not be detected

### "Failed to initialize RTC engine"
- Verify your App ID is correct
- Check internet connection
- Ensure firewall allows Agora connections

### Camera shows wrong name/resolution
- The detection shows what OpenCV reports
- Actual streaming will use the configured 480p @ 30fps
- Camera names may vary by OS and driver

### High latency
- Check network bandwidth
- Ensure you're using wired ethernet when possible
- Try reducing the bitrate in `agora_config.py`

### Black screen / No video
- Ensure follower is streaming first
- Check that both use the same App ID
- Verify the selected cameras are not in use by other applications

## Testing Connection

Test your Agora connectivity:
```bash
cd agora
python test_agora_connection.py
```

## Video Quality Settings

All streams are configured for 480p @ 30fps. To modify, edit `agora_config.py`:

```python
VIDEO_PROFILE = {
    "width": 640,      # 480p width
    "height": 480,     # 480p height
    "frameRate": 30,   # 30 fps
    "bitrate": 800     # Adjust for quality/bandwidth
}
```

## Support

- [Agora Documentation](https://docs.agora.io)
- [Agora Community](https://www.agora.io/en/community/)
- Check the status messages in the GUI for debugging information

## License

This implementation is provided as-is for educational and development purposes. 