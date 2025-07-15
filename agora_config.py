"""
Agora Video Streaming Configuration
"""

# Agora Credentials (Get these from https://console.agora.io)
APP_ID = "YOUR_AGORA_APP_ID"  # Replace with your Agora App ID
APP_CERTIFICATE = None  # Optional - for token authentication

# Channel Configuration
CHANNEL_PREFIX = "robot_cam_"  # Prefix for video channels
VIDEO_CHANNELS = {
    "camera1": f"{CHANNEL_PREFIX}1",
    "camera2": f"{CHANNEL_PREFIX}2", 
    "camera3": f"{CHANNEL_PREFIX}3"
}

# Video Configuration
VIDEO_PROFILE = {
    "width": 640,
    "height": 480,
    "frameRate": 30,
    "bitrate": 1000
}

# Audio Configuration (disabled for video-only streaming)
ENABLE_AUDIO = False

# Network Configuration
ENABLE_DUAL_STREAM = True  # Enable dual stream for bandwidth adaptation
LOW_STREAM_PARAMETER = {
    "width": 320,
    "height": 240,
    "frameRate": 15,
    "bitrate": 200
}

# Recording Configuration
ENABLE_CLOUD_RECORDING = False  # Set to True to enable cloud recording
RECORDING_BUCKET = ""  # S3 bucket name if using cloud recording
RECORDING_REGION = ""  # AWS region for recording

# UI Configuration
WINDOW_TITLE_LEADER = "Robot Video Feeds - Leader"
WINDOW_TITLE_FOLLOWER = "Robot Video Feeds - Follower"
GRID_ROWS = 2
GRID_COLS = 2  # 2x2 grid for 3 cameras + 1 empty slot 