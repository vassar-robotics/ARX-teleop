#!/usr/bin/env python3
"""
Agora Video Streaming - Leader Side (Web-based)
Web interface to receive and display video feeds from Agora channels
Supports dynamic number of cameras (up to 4)
"""

import os
import sys
from flask import Flask, render_template, jsonify
import logging
import subprocess

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

@app.route('/')
def index():
    """Serve the main video display page."""
    return render_template('leader.html')

@app.route('/api/config')
def get_config():
    """Get Agora configuration for single channel reception."""
    # Use single channel for receiving
    if hasattr(agora_config, 'VIDEO_CHANNELS'):
        channel_list = list(agora_config.VIDEO_CHANNELS.values())
        channel = channel_list[0] if channel_list else "robot-video-1"
    else:
        channel = "robot-video-1"
    
    config_data = {
        'appId': agora_config.APP_ID,
        'channels': [channel],  # Single channel
        'videoProfile': agora_config.VIDEO_PROFILE,
        'numChannels': 1
    }
    
    # Include token if configured
    if hasattr(agora_config, 'USE_TOKEN') and agora_config.USE_TOKEN:
        config_data['useToken'] = True
        config_data['token'] = agora_config.TOKEN
        
        # Use single UID for receiving
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
            webbrowser.open('http://127.0.0.1:5001')
        except Exception as e:
            logger.warning(f"Could not open browser: {e}")

def main():
    # Check if running headless
    check_headless()
    
    # Create templates directory if it doesn't exist
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    logger.info("Video Stream Leader (Web) ready")
    logger.info(f"Using Agora App ID: {agora_config.APP_ID[:8]}...")
    
    if HEADLESS_MODE:
        logger.info("Running in headless mode - browser will not open automatically")
        logger.info("Please open http://127.0.0.1:5001 in a web browser")
    else:
        # Only import and use webbrowser if not headless
        from threading import Timer
        Timer(1.5, open_browser).start()
    
    # Run Flask app
    app.run(host='127.0.0.1', port=5001, debug=False)

if __name__ == "__main__":
    main() 