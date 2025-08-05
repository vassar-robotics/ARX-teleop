"""
PubNub configuration for robot teleoperation.

Using testing keys from Nate's PubNub account (nh-test2-pub-250804).
"""

# PubNub Keys (testing keys from Nate's account: nh-test2-pub-250804)
PUBLISH_KEY = "pub-c-48d3877c-4a94-4665-b655-758825b1de82"
SUBSCRIBE_KEY = "sub-c-5c9b3404-aacb-4d9e-aa24-ac47d060cdb9"
SECRET_KEY = "sec-c-NGRjNzNmYjEtMjgwZS00N2Y0LThhMmItNjY4NjA3ZTE1OWNk"

# Channel names
TELEMETRY_CHANNEL = "robot-telemetry"
CONTROL_CHANNEL = "robot-control"
STATUS_CHANNEL = "robot-status"

# Teleoperation settings
TARGET_FPS = 20  # Target update rate (reduced for internet teleoperation)
MAX_LATENCY_MS = 200  # Maximum acceptable latency before safety stop
RECONNECT_DELAY_S = 2  # Delay before reconnection attempts

# Safety settings
MAX_POSITION_CHANGE = 200  # Maximum position change per update
POSITION_SMOOTHING = 0.8  # Smoothing factor (0-1, higher = smoother)

# Monitoring settings
LATENCY_WARNING_MS = 100  # Warn if latency exceeds this
PACKET_LOSS_WARNING = 0.05  # Warn if packet loss exceeds 5% 