# Headless Browser Streaming for Agora on Orange Pi

This solution uses a headless Chromium browser with Selenium to stream video from Orange Pi to Agora channels, bypassing the need for ARM-specific native libraries.

## Overview

Since Agora doesn't provide IoT SDK libraries for ARM Linux, this approach:
- Runs a headless Chromium browser on Orange Pi
- Uses Agora Web SDK (which works in any browser)
- Accesses cameras through WebRTC
- Streams video without requiring a display

## Quick Start

### 1. Install Dependencies

Run the installation script on your Orange Pi:

```bash
cd agora
chmod +x install_headless_deps.sh
./install_headless_deps.sh
```

This installs:
- Chromium browser (headless capable)
- ChromeDriver for Selenium
- Python Selenium library
- Required system libraries

### 2. Configure Agora Settings

Edit `agora_config.py` with your settings:

```python
# Your Agora App ID
APP_ID = "your_app_id_here"

# Channel configuration (optional)
VIDEO_CHANNELS = {
    'camera_0': 'robot-video-1',
    'camera_1': 'robot-video-2',
}

# Token configuration (if using authentication)
USE_TOKEN = True
TOKEN = "your_token_here"
```

### 3. Run the Streamer

```bash
python3 headless_agora_streamer.py
```

The script will:
1. Launch a headless Chrome browser
2. Load Agora Web SDK
3. Detect available cameras
4. Start streaming to configured channel

## Features

- **Automatic camera detection** via WebRTC
- **Headless operation** - no display required
- **Real-time monitoring** of stream status
- **Graceful shutdown** with Ctrl+C
- **Error handling** and recovery
- **Performance optimized** Chrome settings

## System Requirements

- **OS**: Debian-based Linux (tested on Orange Pi)
- **RAM**: Minimum 512MB, recommended 1GB+
- **Storage**: ~200MB for Chromium + dependencies
- **Network**: Stable internet connection

## Performance Considerations

### Memory Usage
- Chromium: ~200-400MB
- Python + Selenium: ~50MB
- Total: ~250-450MB

### CPU Usage
- Startup: High for 5-10 seconds
- Streaming: ~10-20% (depends on resolution)

### Optimization Tips

1. **Lower resolution for less CPU/bandwidth**:
   Edit line 145 in `headless_agora_streamer.py`:
   ```javascript
   width: 320,   // was 640
   height: 240,  // was 480
   frameRate: 15 // was 30
   ```

2. **Add swap space if low on RAM**:
   ```bash
   sudo fallocate -l 1G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

## Troubleshooting

### Camera Not Detected

1. Check camera permissions:
   ```bash
   ls -la /dev/video*
   sudo usermod -a -G video $USER
   # Logout and login again
   ```

2. Test camera with Chromium:
   ```bash
   chromium-browser --use-fake-ui-for-media-stream
   ```

### Chromium Crashes

1. Check system resources:
   ```bash
   free -h
   htop
   ```

2. Try with more aggressive options:
   ```python
   # Add to setup_chrome_options() in the script
   options.add_argument('--disable-web-security')
   options.add_argument('--disable-features=VizDisplayCompositor')
   ```

### High CPU Usage

1. Monitor which process uses CPU:
   ```bash
   top -p $(pgrep -f chromium)
   ```

2. Reduce video quality (see Optimization Tips above)

### Stream Not Starting

1. Check logs for errors:
   ```bash
   python3 headless_agora_streamer.py 2>&1 | tee debug.log
   ```

2. Verify network connectivity:
   ```bash
   ping www.agora.io
   ```

3. Test with a simple webpage first:
   ```python
   # Test script
   from selenium import webdriver
   from selenium.webdriver.chrome.options import Options
   
   options = Options()
   options.add_argument('--headless')
   options.add_argument('--no-sandbox')
   
   driver = webdriver.Chrome(options=options)
   driver.get('https://www.google.com')
   print(driver.title)
   driver.quit()
   ```

## Running as a Service

Create `/etc/systemd/system/agora-headless-stream.service`:

```ini
[Unit]
Description=Agora Headless Video Streaming
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/agora
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 /home/pi/agora/headless_agora_streamer.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable agora-headless-stream.service
sudo systemctl start agora-headless-stream.service
sudo systemctl status agora-headless-stream.service
```

## Multi-Camera Support

To stream from multiple cameras simultaneously, modify the main() function:

```python
# In headless_agora_streamer.py
def main():
    # ... existing code ...
    
    # Start multiple streamers
    streamers = []
    for i in range(2):  # For 2 cameras
        streamer = HeadlessAgoraStreamer()
        streamers.append(streamer)
        
        # Run in thread
        thread = threading.Thread(
            target=streamer.start_streaming,
            args=(i,)  # camera index
        )
        thread.start()
```

## Advantages vs Native SDK

✅ **Pros**:
- No ARM library compilation needed
- Works on any Linux with Chrome
- Easy to debug (browser DevTools)
- Uses standard WebRTC

❌ **Cons**:
- Higher resource usage
- Additional latency (~50-100ms)
- Requires more dependencies

## Conclusion

While not as efficient as native SDK, this headless browser approach provides a working solution for streaming from ARM devices when native libraries are unavailable. It's particularly useful for prototyping and scenarios where the device has sufficient resources. 