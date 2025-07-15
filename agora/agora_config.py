"""
Agora Video Streaming Configuration
"""

# Agora Credentials (Get these from https://console.agora.io)
APP_ID = "9b4dab3f30524c12b7e78bff8c83a24d"  # User's Agora App ID
APP_CERTIFICATE = None  # Optional - for token authentication

# Token Configuration for secure channels
USE_TOKEN = True  # Set to True when using tokens
TOKEN = "007eJxTYGC2LdS7n1NsMOMX+/YHlh5M0v9WHmFly9U1Kn23f9+hjC8KDJZJJimJScZpxgamRibJhkZJ5qnmFklpaRbJFsaJRiYpgrxlGQ2BjAx+T3YxMzJAIIjPwZBSmpijm1iUy8AAAHI1H+k="
TOKEN_CHANNEL = "dual-arm"  # Channel name for the token

# Channel Configuration
CHANNEL_PREFIX = "robot_cam_"  # Prefix for video channels
VIDEO_CHANNELS = {
    "camera1": f"{CHANNEL_PREFIX}1",
    "camera2": f"{CHANNEL_PREFIX}2", 
    "camera3": f"{CHANNEL_PREFIX}3"
}

# When using token, use the same channel but different UIDs for each camera
if USE_TOKEN:
    # For token-based auth, we'll use the same channel but different UIDs
    VIDEO_CHANNELS = {
        "camera1": TOKEN_CHANNEL,
        "camera2": TOKEN_CHANNEL,
        "camera3": TOKEN_CHANNEL
    }
    # UIDs for each camera (must be unique per channel)
    CAMERA_UIDS = {
        "camera1": 1001,
        "camera2": 1002,
        "camera3": 1003
    }
else:
    CAMERA_UIDS = {
        "camera1": None,
        "camera2": None,
        "camera3": None
    }

# Video Configuration - 480p @ 30fps
VIDEO_PROFILE = {
    "width": 640,   # 480p width
    "height": 480,  # 480p height
    "frameRate": 30,
    "bitrate": 800  # Reduced bitrate for 480p
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