#!/usr/bin/env python3
"""
Agora Video Streaming - Follower Side (Web-based)
Web interface to capture and stream video feeds to Agora channels
Supports headless operation and automatic camera detection
"""

import os
import sys
import random
from flask import Flask, render_template, jsonify
import logging
import subprocess
from threading import Timer

# Add parent directory to path to import agora_config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agora_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variable to track if we're in headless mode
HEADLESS_MODE = False

def check_headless():
    """Check if running in headless mode."""
    global HEADLESS_MODE
    # Check for DISPLAY environment variable
    if not os.environ.get('DISPLAY'):
        HEADLESS_MODE = True
        logger.info("Running in headless mode")
        return True
    
    # Check if we can import and use webbrowser
    try:
        import webbrowser
        return False
    except:
        HEADLESS_MODE = True
        logger.info("Running in headless mode (no webbrowser module)")
        return True

def get_available_cameras():
    """Detect available cameras using v4l2 on Linux or system enumeration."""
    cameras = []
    
    # Try Linux v4l2 devices first
    try:
        import glob
        video_devices = glob.glob('/dev/video*')
        for device in sorted(video_devices):
            # Check if it's a real video capture device
            try:
                # Use v4l2-ctl if available
                result = subprocess.run(['v4l2-ctl', '-d', device, '--info'], 
                                      capture_output=True, text=True, timeout=1)
                if result.returncode == 0 and 'Video Capture' in result.stdout:
                    device_num = int(device.replace('/dev/video', ''))
                    cameras.append(device_num)
                    logger.info(f"Found camera at {device} (index {device_num})")
            except (subprocess.SubprocessError, FileNotFoundError, ValueError):
                # Fallback: just assume it's a valid device
                try:
                    device_num = int(device.replace('/dev/video', ''))
                    cameras.append(device_num)
                except ValueError:
                    pass
    except Exception as e:
        logger.warning(f"Could not enumerate v4l2 devices: {e}")
    
    # If no cameras found or not on Linux, try indices 0-9
    if not cameras:
        logger.info("No v4l2 cameras found, using default camera indices...")
        # For macOS and other systems, start with common camera indices
        cameras = [0, 1, 2, 3]  # Common camera indices
    
    # Limit to 4 cameras max
    if len(cameras) > 4:
        logger.info(f"Found {len(cameras)} cameras, randomly selecting 4")
        cameras = random.sample(cameras, 4)
    
    return cameras

@app.route('/')
def index():
    """Serve the main video capture page."""
    return render_template('follower.html')

@app.route('/api/config')
def get_config():
    """Get Agora configuration for single camera streaming."""
    # Get available cameras
    cameras = get_available_cameras()
    num_cameras = len(cameras)
    
    # Use single channel for streaming
    if hasattr(agora_config, 'VIDEO_CHANNELS'):
        channel_list = list(agora_config.VIDEO_CHANNELS.values())
        channel = channel_list[0] if channel_list else "robot-video-1"
    else:
        channel = "robot-video-1"
    
    config_data = {
        'appId': agora_config.APP_ID,
        'channels': [channel],  # Single channel
        'videoProfile': agora_config.VIDEO_PROFILE,
        'cameraIndices': cameras,
        'numCameras': num_cameras
    }
    
    # Include token if configured
    if hasattr(agora_config, 'USE_TOKEN') and agora_config.USE_TOKEN:
        config_data['useToken'] = True
        config_data['token'] = agora_config.TOKEN
        
        # Use single UID for streaming
        if hasattr(agora_config, 'CAMERA_UIDS'):
            uid_list = list(agora_config.CAMERA_UIDS.values())
            camera_uid = uid_list[0] if uid_list else 1001
        else:
            camera_uid = 1001
        
        config_data['cameraUids'] = [camera_uid]
    else:
        config_data['useToken'] = False
        config_data['cameraUids'] = [None]
        
    return jsonify(config_data)

def open_browser():
    """Open web browser after server starts (only if not headless)."""
    if not HEADLESS_MODE:
        try:
            import webbrowser
            webbrowser.open('http://127.0.0.1:5002')
        except Exception as e:
            logger.warning(f"Could not open browser: {e}")

def main():
    # Check if running headless
    check_headless()
    
    # Create templates directory if it doesn't exist
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    logger.info("Video Stream Follower (Web) ready")
    logger.info(f"Using Agora App ID: {agora_config.APP_ID[:8]}...")
    logger.info("Available at: http://127.0.0.1:5002")
    
    if HEADLESS_MODE:
        logger.info("Running in headless mode - browser will not open automatically")
        logger.info("Please open http://127.0.0.1:5002 in a web browser")
    else:
        # Open browser after a short delay
        Timer(1.5, open_browser).start()
    
    # Run Flask app on different port than leader
    app.run(host='127.0.0.1', port=5002, debug=False)

if __name__ == "__main__":
    main() 