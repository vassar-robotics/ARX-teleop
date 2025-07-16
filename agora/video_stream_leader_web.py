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
    """Get Agora configuration."""
    # Get channels configuration
    if hasattr(agora_config, 'VIDEO_CHANNELS'):
        channels = list(agora_config.VIDEO_CHANNELS.values())
    else:
        # Default to 4 channels if not specified
        channels = [f"robot-video-{i+1}" for i in range(4)]
    
    config_data = {
        'appId': agora_config.APP_ID,
        'channels': channels,
        'videoProfile': agora_config.VIDEO_PROFILE,
        'numChannels': len(channels)
    }
    
    # Include token if configured
    if hasattr(agora_config, 'USE_TOKEN') and agora_config.USE_TOKEN:
        config_data['useToken'] = True
        config_data['token'] = agora_config.TOKEN
        
        # Get camera UIDs
        if hasattr(agora_config, 'CAMERA_UIDS'):
            camera_uids = list(agora_config.CAMERA_UIDS.values())
        else:
            camera_uids = [1000 + i for i in range(len(channels))]
        
        config_data['cameraUids'] = camera_uids
    else:
        config_data['useToken'] = False
        config_data['cameraUids'] = [None] * len(channels)
        
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
    
    # Create the HTML template
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Robot Video Feeds - Leader</title>
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
        }
        .channel-info {
            position: absolute;
            bottom: 10px;
            left: 10px;
            background-color: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
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
        <h1>Robot Video Feeds - Leader</h1>
        
        <div class="info-panel">
            <h3>Channel Configuration</h3>
            <div id="channel-info">Loading configuration...</div>
        </div>
        
        <div class="controls">
            <button id="startBtn" onclick="startReceiving()">Start Receiving</button>
            <button id="stopBtn" onclick="stopReceiving()" disabled>Stop Receiving</button>
            <button id="recordBtn" onclick="toggleRecording()" disabled>Start Recording</button>
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
        let isReceiving = false;
        let isRecording = false;
        
        // Load configuration
        async function loadConfig() {
            try {
                const response = await fetch('/api/config');
                config = await response.json();
                
                // Update channel info
                const infoDiv = document.getElementById('channel-info');
                infoDiv.innerHTML = `Configured for ${config.numChannels} channel(s): ${config.channels.join(', ')}`;
                
                // Create video containers dynamically
                const videoGrid = document.getElementById('video-grid');
                videoGrid.innerHTML = '';
                
                for (let i = 0; i < config.numChannels; i++) {
                    const container = document.createElement('div');
                    container.className = 'video-container';
                    container.id = `video-container-${i}`;
                    container.innerHTML = `
                        <div class="video-label">Camera ${i + 1}</div>
                        <div class="channel-info">Channel: ${config.channels[i]}</div>
                        <div class="no-signal">NO SIGNAL</div>
                    `;
                    videoGrid.appendChild(container);
                }
                
                addStatus('Configuration loaded', 'ok');
                addStatus(`Ready to receive from ${config.numChannels} channel(s)`, 'ok');
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
        
        async function startReceiving() {
            if (!config) {
                await loadConfig();
            }
            
            if (!config || !config.appId) {
                addStatus('Invalid configuration', 'error');
                return;
            }
            
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('recordBtn').disabled = false;
            
            isReceiving = true;
            addStatus('Starting video reception...', 'info');
            
            // Check if all cameras use the same channel (token mode)
            const usesSameChannel = config.channels.every(ch => ch === config.channels[0]);
            
            if (usesSameChannel && config.useToken) {
                // Single channel mode with multiple UIDs
                const client = AgoraRTC.createClient({ mode: 'live', codec: 'vp8' });
                clients.push(client);
                
                try {
                    // Set client role to audience
                    await client.setClientRole('audience');
                    
                    // Join channel with token
                    await client.join(config.appId, config.channels[0], config.token, null);
                    addStatus(`Joined channel: ${config.channels[0]}`, 'ok');
                    
                    // Track which camera UIDs we've received
                    const uidToCameraMap = {};
                    config.cameraUids.forEach((uid, index) => {
                        if (uid !== null) {
                            uidToCameraMap[uid] = index;
                        }
                    });
                    
                    // Subscribe to remote users
                    client.on('user-published', async (user, mediaType) => {
                        await client.subscribe(user, mediaType);
                        
                        if (mediaType === 'video') {
                            const cameraNum = uidToCameraMap[user.uid];
                            if (cameraNum !== undefined) {
                                const container = document.getElementById(`video-container-${cameraNum}`);
                                
                                // Remove no signal message
                                const noSignal = container.querySelector('.no-signal');
                                if (noSignal) {
                                    noSignal.remove();
                                }
                                
                                // Play video
                                user.videoTrack.play(container);
                                addStatus(`Receiving video from Camera ${cameraNum + 1} (UID: ${user.uid})`, 'ok');
                            } else {
                                // Unknown UID, try to find an empty slot
                                for (let i = 0; i < config.numChannels; i++) {
                                    const container = document.getElementById(`video-container-${i}`);
                                    if (container && container.querySelector('.no-signal')) {
                                        const noSignal = container.querySelector('.no-signal');
                                        if (noSignal) {
                                            noSignal.remove();
                                        }
                                        user.videoTrack.play(container);
                                        addStatus(`Receiving video from unknown UID ${user.uid} in slot ${i + 1}`, 'warning');
                                        uidToCameraMap[user.uid] = i;
                                        break;
                                    }
                                }
                            }
                        }
                    });
                    
                    client.on('user-unpublished', (user, mediaType) => {
                        if (mediaType === 'video') {
                            const cameraNum = uidToCameraMap[user.uid];
                            if (cameraNum !== undefined) {
                                const container = document.getElementById(`video-container-${cameraNum}`);
                                container.innerHTML = `
                                    <div class="video-label">Camera ${cameraNum + 1}</div>
                                    <div class="channel-info">Channel: ${config.channels[0]}</div>
                                    <div class="no-signal">NO SIGNAL</div>
                                `;
                                addStatus(`Lost video from Camera ${cameraNum + 1}`, 'warning');
                            }
                        }
                    });
                    
                } catch (error) {
                    addStatus(`Failed to join channel: ${error.message}`, 'error');
                }
            } else {
                // Multi-channel mode (original behavior)
                for (let i = 0; i < config.numChannels; i++) {
                    const client = AgoraRTC.createClient({ mode: 'live', codec: 'vp8' });
                    clients.push(client);
                    
                    try {
                        // Set client role to audience
                        await client.setClientRole('audience');
                        
                        // Join channel with token if available
                        const token = config.useToken ? config.token : null;
                        await client.join(config.appId, config.channels[i], token, null);
                        addStatus(`Joined channel: ${config.channels[i]}`, 'ok');
                        
                        // Subscribe to remote users
                        client.on('user-published', async (user, mediaType) => {
                            await client.subscribe(user, mediaType);
                            
                            if (mediaType === 'video') {
                                const container = document.getElementById(`video-container-${i}`);
                                
                                // Remove no signal message
                                const noSignal = container.querySelector('.no-signal');
                                if (noSignal) {
                                    noSignal.remove();
                                }
                                
                                // Play video
                                user.videoTrack.play(container);
                                addStatus(`Receiving video in channel ${config.channels[i]}`, 'ok');
                            }
                        });
                        
                        client.on('user-unpublished', (user, mediaType) => {
                            if (mediaType === 'video') {
                                const container = document.getElementById(`video-container-${i}`);
                                container.innerHTML = `
                                    <div class="video-label">Camera ${i + 1}</div>
                                    <div class="channel-info">Channel: ${config.channels[i]}</div>
                                    <div class="no-signal">NO SIGNAL</div>
                                `;
                                addStatus(`Lost video in channel ${config.channels[i]}`, 'warning');
                            }
                        });
                        
                    } catch (error) {
                        addStatus(`Failed to join channel ${config.channels[i]}: ${error.message}`, 'error');
                    }
                }
            }
        }
        
        async function stopReceiving() {
            isReceiving = false;
            
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('recordBtn').disabled = true;
            
            if (isRecording) {
                toggleRecording();
            }
            
            addStatus('Stopping video reception...', 'info');
            
            // Leave all channels
            for (let i = 0; i < clients.length; i++) {
                try {
                    await clients[i].leave();
                } catch (error) {
                    console.error('Error leaving channel:', error);
                }
            }
            
            // Reset all video containers
            for (let i = 0; i < config.numChannels; i++) {
                const container = document.getElementById(`video-container-${i}`);
                if (container) {
                    container.innerHTML = `
                        <div class="video-label">Camera ${i + 1}</div>
                        <div class="channel-info">Channel: ${config.channels[i]}</div>
                        <div class="no-signal">NO SIGNAL</div>
                    `;
                }
            }
            
            clients = [];
            addStatus('Video reception stopped', 'ok');
        }
        
        function toggleRecording() {
            isRecording = !isRecording;
            const btn = document.getElementById('recordBtn');
            
            if (isRecording) {
                btn.textContent = 'Stop Recording';
                addStatus('Recording started (feature not implemented)', 'warning');
            } else {
                btn.textContent = 'Start Recording';
                addStatus('Recording stopped', 'info');
            }
        }
        
        // Initialize on page load
        window.addEventListener('load', () => {
            loadConfig();
        });
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (isReceiving) {
                stopReceiving();
            }
        });
    </script>
</body>
</html>'''
    
    # Write HTML template
    template_path = os.path.join(template_dir, 'leader.html')
    with open(template_path, 'w') as f:
        f.write(html_content)
    
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