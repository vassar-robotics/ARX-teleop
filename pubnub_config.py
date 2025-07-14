"""
PubNub configuration for robot teleoperation.

Replace the demo keys with your own PubNub keys from:
https://dashboard.pubnub.com/
"""

# PubNub Keys (using demo keys for testing)
PUBLISH_KEY = "pub-c-ace45006-4331-485b-a7d0-7f24c716ba33"
SUBSCRIBE_KEY = "sub-c-885f70c4-44de-4f6b-ac8f-7452e86ee781"

# For production, use your own keys:
# PUBLISH_KEY = "your-publish-key"
# SUBSCRIBE_KEY = "your-subscribe-key"

# Channel names
TELEMETRY_CHANNEL = "robot-telemetry"
CONTROL_CHANNEL = "robot-control"
STATUS_CHANNEL = "robot-status"

# Teleoperation settings
TARGET_FPS = 60  # Target update rate
MAX_LATENCY_MS = 200  # Maximum acceptable latency before safety stop
RECONNECT_DELAY_S = 2  # Delay before reconnection attempts

# Safety settings
MAX_POSITION_CHANGE = 200  # Maximum position change per update
POSITION_SMOOTHING = 0.8  # Smoothing factor (0-1, higher = smoother)

# Monitoring settings
LATENCY_WARNING_MS = 100  # Warn if latency exceeds this
PACKET_LOSS_WARNING = 0.05  # Warn if packet loss exceeds 5% 