# Agora Video Streaming Solution

This solution provides low-latency video streaming of 3 camera feeds from a follower client to a leader client using Agora's Video SDK. Perfect for robotic teleoperation over the internet with recording capabilities.

## Features

- **Ultra-low latency**: 200-400ms between Asia and US
- **3 simultaneous video streams**: Each camera gets its own channel
- **Cross-platform GUI**: Works on both macOS and Ubuntu
- **Simple setup**: Just need an Agora App ID
- **Recording ready**: Built-in support for cloud recording
- **Bandwidth adaptive**: Dual stream support for network adaptation

## Prerequisites

1. **Python 3.8+** installed
2. **Agora Account**: Sign up at [console.agora.io](https://console.agora.io)
3. **Cameras**: 3 USB cameras or webcams connected to the follower computer

## Installation

1. Install the required packages:
```bash
pip install -r requirements_agora.txt
```

2. Get your Agora App ID:
   - Log in to [Agora Console](https://console.agora.io)
   - Create a new project
   - Copy the App ID from the project settings

## Configuration

Edit `agora_config.py` and replace `YOUR_AGORA_APP_ID` with your actual App ID:

```python
APP_ID = "your-actual-app-id-here"
```

## Usage

### On the Follower Computer (Robot side):

1. Connect 3 cameras to your computer
2. Run the follower script:
```bash
python video_stream_follower.py
```
3. Enter your Agora App ID if not already configured
4. Adjust camera indices if needed (default: 0, 1, 2)
5. Click "Start Streaming"

### On the Leader Computer (Operator side):

1. Run the leader script:
```bash
python video_stream_leader.py
```
2. Enter the same Agora App ID
3. Click "Start Receiving"
4. You should see 3 video feeds from the follower

## Camera Configuration

If your cameras are not at indices 0, 1, 2, you can change them in the GUI or find the correct indices:

### Linux:
```bash
v4l2-ctl --list-devices
```

### macOS:
```bash
system_profiler SPCameraDataType
```

### Windows:
Check Device Manager under "Imaging devices"

## Network Requirements

- **Bandwidth**: ~3-5 Mbps upload (follower) and download (leader)
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

### "No cameras could be initialized"
- Check camera connections
- Verify camera indices in the GUI
- On Linux, ensure you have permissions: `sudo usermod -a -G video $USER`

### "Failed to initialize RTC engine"
- Verify your App ID is correct
- Check internet connection
- Ensure firewall allows Agora connections

### High latency
- Check network bandwidth
- Try reducing video resolution in `agora_config.py`
- Enable dual stream mode for adaptive quality

### Black screen / No video
- Ensure follower is streaming first
- Check that both use the same App ID
- Verify firewall settings

## Advanced Configuration

### Video Quality Settings

Edit `agora_config.py` to adjust video quality:

```python
VIDEO_PROFILE = {
    "width": 640,      # Reduce for lower bandwidth
    "height": 480,     
    "frameRate": 30,   # Reduce to 15 for lower bandwidth
    "bitrate": 1000    # Reduce for lower bandwidth
}
```

### Channel Names

By default, channels are named `robot_cam_1`, `robot_cam_2`, `robot_cam_3`. 
You can change the prefix in `agora_config.py`:

```python
CHANNEL_PREFIX = "my_robot_"
```

## Performance Tips

1. **Use wired ethernet** when possible for best stability
2. **Close unnecessary applications** to free up bandwidth
3. **Adjust video quality** based on your network conditions
4. **Use dual stream mode** for automatic quality adaptation

## Security Notes

- The App ID is visible to clients, use token authentication for production
- Channels are public by default, implement authentication for private streams
- Consider encrypting streams for sensitive applications

## Support

- [Agora Documentation](https://docs.agora.io)
- [Agora Community](https://www.agora.io/en/community/)
- Check the status messages in the GUI for debugging information

## License

This implementation is provided as-is for educational and development purposes. 