#!/bin/bash
# Reset Streaming Environment - Simple cleanup script

echo "Killing streaming processes..."
pkill -f "video_stream_follower_web.py"
pkill -f "video_stream_leader_web.py"

echo "Killing port 5001..."
lsof -ti:5001 | xargs kill -9 2>/dev/null || true

echo "Killing port 5002..."
lsof -ti:5002 | xargs kill -9 2>/dev/null || true

echo "Environment reset complete!"