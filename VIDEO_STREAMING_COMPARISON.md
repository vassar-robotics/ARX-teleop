# Video Streaming Solution Comparison

## PubNub Teleoperation vs Agora Video Streaming

This repository contains two separate solutions:

### 1. PubNub Teleoperation (Command/Control)
- **Purpose**: Real-time robot arm control over internet
- **Files**: `teleoperate_leader_remote.py`, `teleoperate_follower_remote.py`
- **Latency**: <50ms for control commands
- **Use**: Sending motor position commands

### 2. Agora Video Streaming (Video Feeds)
- **Purpose**: Stream 3 camera feeds with low latency
- **Files**: `video_stream_leader.py`, `video_stream_follower.py`
- **Latency**: 200-400ms for video
- **Use**: Visual feedback from robot cameras

## Quick Start Guide

### For Complete Teleoperation Setup:

1. **Install dependencies:**
```bash
pip install -r requirements_pubnub.txt
pip install -r requirements_agora.txt
```

2. **Configure credentials:**
- Edit `pubnub_config.py` with your PubNub keys
- Edit `agora_config.py` with your Agora App ID

3. **On Follower (Robot) Computer:**
```bash
# Terminal 1 - Robot control
python teleoperate_follower_remote.py

# Terminal 2 - Video streaming
python video_stream_follower.py
```

4. **On Leader (Operator) Computer:**
```bash
# Terminal 1 - Robot control
python teleoperate_leader_remote.py

# Terminal 2 - Video display
python video_stream_leader.py
```

## Why Two Separate Systems?

1. **Different latency requirements**: Control needs <100ms, video can tolerate 200-400ms
2. **Different data types**: Small JSON messages vs large video streams
3. **Different protocols**: PubNub uses WebSockets, Agora uses WebRTC
4. **Scalability**: Can run video on different network if needed
5. **Cost optimization**: PubNub for lightweight control, Agora for heavy video

## Integration Tips

While the systems are separate, they work well together:

- Start video streaming first to see the robot
- Use video feed to guide teleoperation
- Video provides visual confirmation of movements
- Both systems can run simultaneously

## Testing

1. **Test PubNub connection:**
```bash
python test_pubnub_connection.py
```

2. **Test Agora connection:**
```bash
python test_agora_connection.py YOUR_APP_ID
```

## Future Enhancements

Consider integrating both systems:
- Single GUI combining control and video
- Synchronized recording of commands and video
- Augmented reality overlays on video
- Automatic failover between systems 