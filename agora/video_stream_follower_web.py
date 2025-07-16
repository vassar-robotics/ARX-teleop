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
        logger.info("Trying camera indices 0-9...")
        # This would require OpenCV or another library to actually test
        # For now, assume cameras 0-3 might be available
        cameras = list(range(4))
    
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
    """Get Agora configuration with dynamic camera support."""
    # Get available cameras
    cameras = get_available_cameras()
    num_cameras = len(cameras)
    
    # Create dynamic channels for the number of cameras found
    channels = []
    camera_uids = []
    
    # Use existing channels if defined, otherwise create new ones
    if hasattr(agora_config, 'VIDEO_CHANNELS'):
        channel_list = list(agora_config.VIDEO_CHANNELS.values())
        for i in range(num_cameras):
            if i < len(channel_list):
                channels.append(channel_list[i])
            else:
                channels.append(f"robot-video-{i+1}")
    else:
        channels = [f"robot-video-{i+1}" for i in range(num_cameras)]
    
    config_data = {
        'appId': agora_config.APP_ID,
        'channels': channels,
        'videoProfile': agora_config.VIDEO_PROFILE,
        'cameraIndices': cameras,
        'numCameras': num_cameras
    }
    
    # Include token if configured
    if hasattr(agora_config, 'USE_TOKEN') and agora_config.USE_TOKEN:
        config_data['useToken'] = True
        config_data['token'] = agora_config.TOKEN
        
        # Create UIDs for each camera
        if hasattr(agora_config, 'CAMERA_UIDS'):
            uid_list = list(agora_config.CAMERA_UIDS.values())
            for i in range(num_cameras):
                if i < len(uid_list):
                    camera_uids.append(uid_list[i])
                else:
                    camera_uids.append(1000 + i)
        else:
            camera_uids = [1000 + i for i in range(num_cameras)]
        
        config_data['cameraUids'] = camera_uids
    else:
        config_data['useToken'] = False
        config_data['cameraUids'] = [None] * num_cameras
        
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
    
    # Create the HTML template with dynamic camera support
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Robot Video Streaming - Follower</title>
    <script src="https://cdn.agora.io/sdk/release/AgoraRTC_N-4.20.0.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f0f0f0;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #333;
        }
        .video-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin: 20px 0;
        }
        .video-container {
            background-color: #000;
            border-radius: 8px;
            overflow: hidden;
            position: relative;
            aspect-ratio: 4/3;
        }
        .video-container video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .video-label {
            position: absolute;
            top: 10px;
            left: 10px;
            background-color: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 14px;
            z-index: 10;
        }
        .camera-info {
            position: absolute;
            bottom: 10px;
            left: 10px;
            background-color: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 10;
        }
        .no-signal {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #666;
            font-size: 18px;
            background-color: #222;
        }
        .controls {
            text-align: center;
            margin: 20px 0;
        }
        button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
            border-radius: 4px;
            cursor: pointer;
            margin: 0 5px;
        }
        button:hover {
            background-color: #45a049;
        }
        button:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        .status {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .status-item {
            margin: 5px 0;
            font-size: 14px;
        }
        .status-ok { color: #4CAF50; }
        .status-error { color: #f44336; }
        .status-warning { color: #ff9800; }
        .info-panel {
            background-color: #e3f2fd;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
            border: 1px solid #2196f3;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Robot Video Streaming - Follower</h1>
        
        <div class="info-panel">
            <h3>Camera Information</h3>
            <div id="camera-info">Detecting cameras...</div>
        </div>
        
        <div class="controls">
            <button id="startBtn" onclick="startStreaming()">Start Streaming</button>
            <button id="stopBtn" onclick="stopStreaming()" disabled>Stop Streaming</button>
            <button id="refreshBtn" onclick="refreshCameras()">Refresh Cameras</button>
        </div>
        
        <div class="video-grid" id="video-grid">
            <!-- Video containers will be dynamically created -->
        </div>
        
        <div class="status">
            <h3>Status</h3>
            <div id="status-messages"></div>
        </div>
    </div>

    <script>
        // Initialize Agora
        AgoraRTC.setLogLevel(1);
        
        let config = null;
        let clients = [];
        let localTracks = [];
        let isStreaming = false;
        
        // Load configuration and setup UI
        async function loadConfig() {
            try {
                const response = await fetch('/api/config');
                config = await response.json();
                
                // Update camera info
                const infoDiv = document.getElementById('camera-info');
                if (config.numCameras === 0) {
                    infoDiv.innerHTML = '<span style="color: red;">No cameras detected!</span>';
                    document.getElementById('startBtn').disabled = true;
                } else {
                    infoDiv.innerHTML = `Detected ${config.numCameras} camera(s): ` +
                        config.cameraIndices.map(idx => `Camera ${idx}`).join(', ');
                }
                
                // Create video containers dynamically
                const videoGrid = document.getElementById('video-grid');
                videoGrid.innerHTML = '';
                
                for (let i = 0; i < config.numCameras; i++) {
                    const container = document.createElement('div');
                    container.className = 'video-container';
                    container.id = `video-container-${i}`;
                    container.innerHTML = `
                        <div class="video-label">Camera ${config.cameraIndices[i]}</div>
                        <div class="camera-info">Channel: ${config.channels[i]}</div>
                        <div class="no-signal">NO CAMERA</div>
                    `;
                    videoGrid.appendChild(container);
                }
                
                addStatus('Configuration loaded', 'ok');
                addStatus(`Found ${config.numCameras} camera(s)`, 'ok');
            } catch (error) {
                addStatus('Failed to load configuration: ' + error.message, 'error');
            }
        }
        
        function addStatus(message, type = 'info') {
            const statusDiv = document.getElementById('status-messages');
            const timestamp = new Date().toLocaleTimeString();
            const statusClass = type === 'ok' ? 'status-ok' : 
                               type === 'error' ? 'status-error' : 
                               'status-warning';
            
            const entry = document.createElement('div');
            entry.className = 'status-item ' + statusClass;
            entry.textContent = `[${timestamp}] ${message}`;
            statusDiv.appendChild(entry);
            
            // Keep only last 10 messages
            while (statusDiv.children.length > 10) {
                statusDiv.removeChild(statusDiv.firstChild);
            }
            
            // Auto-scroll to bottom
            statusDiv.scrollTop = statusDiv.scrollHeight;
        }
        
        async function startStreaming() {
            if (!config || config.numCameras === 0) {
                addStatus('No cameras available to stream', 'error');
                return;
            }
            
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('refreshBtn').disabled = true;
            
            isStreaming = true;
            addStatus('Starting video streaming...', 'info');
            
            // Try to get camera permissions
            try {
                await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            } catch (error) {
                addStatus('Camera permission denied: ' + error.message, 'error');
                stopStreaming();
                return;
            }
            
            // Get available devices
            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter(device => device.kind === 'videoinput');
            addStatus(`Browser detected ${videoDevices.length} video device(s)`, 'info');
            
            // Create a client for each camera
            for (let i = 0; i < config.numCameras; i++) {
                const client = AgoraRTC.createClient({ mode: 'live', codec: 'vp8' });
                clients.push(client);
                
                try {
                    // Set client role to host
                    await client.setClientRole('host');
                    
                    // Join channel with token if available
                    const token = config.useToken ? config.token : null;
                    const uid = config.cameraUids ? config.cameraUids[i] : null;
                    await client.join(config.appId, config.channels[i], token, uid);
                    addStatus(`Joined channel: ${config.channels[i]}${uid ? ' with UID: ' + uid : ''}`, 'ok');
                    
                    // Create video track - try to use specific device if available
                    let videoTrack;
                    try {
                        if (i < videoDevices.length) {
                            // Use specific device
                            videoTrack = await AgoraRTC.createCameraVideoTrack({
                                cameraId: videoDevices[i].deviceId,
                                encoderConfig: {
                                    width: config.videoProfile.width,
                                    height: config.videoProfile.height,
                                    frameRate: config.videoProfile.fps,
                                    bitrateMax: config.videoProfile.bitrate
                                }
                            });
                            addStatus(`Using device: ${videoDevices[i].label || 'Camera ' + i}`, 'ok');
                        } else {
                            // Fallback to default camera
                            videoTrack = await AgoraRTC.createCameraVideoTrack({
                                encoderConfig: {
                                    width: config.videoProfile.width,
                                    height: config.videoProfile.height,
                                    frameRate: config.videoProfile.fps,
                                    bitrateMax: config.videoProfile.bitrate
                                }
                            });
                            addStatus(`Using default camera for stream ${i}`, 'warning');
                        }
                    } catch (trackError) {
                        addStatus(`Failed to create video track ${i}: ${trackError.message}`, 'error');
                        continue;
                    }
                    
                    localTracks.push(videoTrack);
                    
                    // Display local video
                    const container = document.getElementById(`video-container-${i}`);
                    const noSignal = container.querySelector('.no-signal');
                    if (noSignal) {
                        noSignal.remove();
                    }
                    videoTrack.play(container);
                    
                    // Publish video track
                    await client.publish([videoTrack]);
                    addStatus(`Streaming camera ${config.cameraIndices[i]} to channel ${config.channels[i]}`, 'ok');
                    
                } catch (error) {
                    addStatus(`Failed to stream Camera ${config.cameraIndices[i]}: ${error.message}`, 'error');
                }
            }
            
            if (localTracks.length === 0) {
                addStatus('No cameras could be streamed', 'error');
                stopStreaming();
            }
        }
        
        async function stopStreaming() {
            isStreaming = false;
            
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('refreshBtn').disabled = false;
            
            addStatus('Stopping video streaming...', 'info');
            
            // Stop and close all tracks
            for (let track of localTracks) {
                track.stop();
                track.close();
            }
            localTracks = [];
            
            // Leave all channels
            for (let i = 0; i < clients.length; i++) {
                try {
                    await clients[i].leave();
                    const container = document.getElementById(`video-container-${i}`);
                    if (container) {
                        container.innerHTML = `
                            <div class="video-label">Camera ${config.cameraIndices[i]}</div>
                            <div class="camera-info">Channel: ${config.channels[i]}</div>
                            <div class="no-signal">NO CAMERA</div>
                        `;
                    }
                } catch (error) {
                    console.error('Error leaving channel:', error);
                }
            }
            
            clients = [];
            addStatus('Video streaming stopped', 'ok');
        }
        
        async function refreshCameras() {
            addStatus('Refreshing camera list...', 'info');
            await loadConfig();
        }
        
        // Initialize on page load
        window.addEventListener('load', async () => {
            await loadConfig();
        });
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (isStreaming) {
                stopStreaming();
            }
        });
        
        // Handle device changes
        navigator.mediaDevices.addEventListener('devicechange', async () => {
            if (!isStreaming) {
                addStatus('Camera configuration changed, refreshing...', 'info');
                await loadConfig();
            }
        });
    </script>
</body>
</html>'''
    
    # Write HTML template
    template_path = os.path.join(template_dir, 'follower.html')
    with open(template_path, 'w') as f:
        f.write(html_content)
    
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