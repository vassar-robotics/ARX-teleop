#!/usr/bin/env python3
"""
Agora Video Streaming - Follower Side (Web-based)
Web interface to capture and stream 3 video feeds to Agora channels
"""

import os
import sys
from flask import Flask, render_template, jsonify
import logging
import webbrowser
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

@app.route('/')
def index():
    """Serve the main video capture page."""
    return render_template('follower.html')

@app.route('/api/config')
def get_config():
    """Get Agora configuration."""
    config_data = {
        'appId': agora_config.APP_ID,
        'channels': list(agora_config.VIDEO_CHANNELS.values()),
        'videoProfile': agora_config.VIDEO_PROFILE
    }
    
    # Include token if configured
    if hasattr(agora_config, 'USE_TOKEN') and agora_config.USE_TOKEN:
        config_data['useToken'] = True
        config_data['token'] = agora_config.TOKEN
        config_data['cameraUids'] = list(agora_config.CAMERA_UIDS.values())
    else:
        config_data['useToken'] = False
        config_data['cameraUids'] = [None, None, None]
        
    return jsonify(config_data)

def open_browser():
    """Open web browser after server starts."""
    webbrowser.open('http://127.0.0.1:5002')

def main():
    # Create templates directory if it doesn't exist
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    # Create the HTML template
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
        .camera-select {
            margin: 10px 0;
        }
        .camera-select label {
            display: inline-block;
            width: 100px;
            text-align: right;
            margin-right: 10px;
        }
        select {
            padding: 5px 10px;
            font-size: 14px;
            border-radius: 4px;
            border: 1px solid #ccc;
            min-width: 200px;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>Robot Video Streaming - Follower</h1>
        
        <div class="controls">
            <div class="camera-select">
                <label>Camera 1:</label>
                <select id="camera1-select">
                    <option value="">Select Camera</option>
                </select>
            </div>
            <div class="camera-select">
                <label>Camera 2:</label>
                <select id="camera2-select">
                    <option value="">Select Camera</option>
                </select>
            </div>
            <div class="camera-select">
                <label>Camera 3:</label>
                <select id="camera3-select">
                    <option value="">Select Camera</option>
                </select>
            </div>
            
            <button id="startBtn" onclick="startStreaming()">Start Streaming</button>
            <button id="stopBtn" onclick="stopStreaming()" disabled>Stop Streaming</button>
        </div>
        
        <div class="video-grid">
            <div class="video-container" id="video-container-1">
                <div class="video-label">Camera 1</div>
                <div class="no-signal">NO CAMERA</div>
            </div>
            <div class="video-container" id="video-container-2">
                <div class="video-label">Camera 2</div>
                <div class="no-signal">NO CAMERA</div>
            </div>
            <div class="video-container" id="video-container-3">
                <div class="video-label">Camera 3</div>
                <div class="no-signal">NO CAMERA</div>
            </div>
            <div class="video-container">
                <!-- Empty slot -->
            </div>
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
        let availableDevices = [];
        
        // Load configuration
        async function loadConfig() {
            try {
                const response = await fetch('/api/config');
                config = await response.json();
                addStatus('Configuration loaded', 'ok');
            } catch (error) {
                addStatus('Failed to load configuration: ' + error.message, 'error');
            }
        }
        
        // Get available camera devices
        async function getCameraDevices() {
            try {
                // Request camera permissions first
                await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
                    .then(stream => stream.getTracks().forEach(track => track.stop()));
                
                const devices = await navigator.mediaDevices.enumerateDevices();
                availableDevices = devices.filter(device => device.kind === 'videoinput');
                
                // Populate camera selectors
                for (let i = 1; i <= 3; i++) {
                    const select = document.getElementById(`camera${i}-select`);
                    select.innerHTML = '<option value="">Select Camera</option>';
                    
                    availableDevices.forEach((device, index) => {
                        const option = document.createElement('option');
                        option.value = device.deviceId;
                        option.text = device.label || `Camera ${index + 1}`;
                        select.appendChild(option);
                        
                        // Auto-select if matches index
                        if (index === i - 1) {
                            select.value = device.deviceId;
                        }
                    });
                }
                
                addStatus(`Found ${availableDevices.length} camera(s)`, 'ok');
            } catch (error) {
                addStatus('Failed to get camera devices: ' + error.message, 'error');
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
            if (!config) {
                await loadConfig();
            }
            
            if (!config || !config.appId) {
                addStatus('Invalid configuration', 'error');
                return;
            }
            
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            
            // Disable camera selectors
            for (let i = 1; i <= 3; i++) {
                document.getElementById(`camera${i}-select`).disabled = true;
            }
            
            isStreaming = true;
            addStatus('Starting video streaming...', 'info');
            
            // Create a client for each camera
            for (let i = 0; i < 3; i++) {
                const cameraSelect = document.getElementById(`camera${i + 1}-select`);
                const deviceId = cameraSelect.value;
                
                if (!deviceId) {
                    addStatus(`No camera selected for Camera ${i + 1}`, 'warning');
                    continue;
                }
                
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
                    
                    // Create video track
                    const videoTrack = await AgoraRTC.createCameraVideoTrack({
                        cameraId: deviceId,
                        encoderConfig: {
                            width: config.videoProfile.width,
                            height: config.videoProfile.height,
                            frameRate: config.videoProfile.fps,
                            bitrateMax: config.videoProfile.bitrate
                        }
                    });
                    
                    localTracks.push(videoTrack);
                    
                    // Display local video
                    const container = document.getElementById(`video-container-${i + 1}`);
                    const noSignal = container.querySelector('.no-signal');
                    if (noSignal) {
                        noSignal.remove();
                    }
                    videoTrack.play(container);
                    
                    // Publish video track
                    await client.publish([videoTrack]);
                    addStatus(`Streaming Camera ${i + 1} to channel ${config.channels[i]}`, 'ok');
                    
                } catch (error) {
                    addStatus(`Failed to stream Camera ${i + 1}: ${error.message}`, 'error');
                }
            }
        }
        
        async function stopStreaming() {
            isStreaming = false;
            
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            
            // Enable camera selectors
            for (let i = 1; i <= 3; i++) {
                document.getElementById(`camera${i}-select`).disabled = false;
            }
            
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
                    const container = document.getElementById(`video-container-${i + 1}`);
                    container.innerHTML = '<div class="video-label">Camera ' + (i + 1) + '</div><div class="no-signal">NO CAMERA</div>';
                } catch (error) {
                    console.error('Error leaving channel:', error);
                }
            }
            
            clients = [];
            addStatus('Video streaming stopped', 'ok');
        }
        
        // Initialize on page load
        window.addEventListener('load', async () => {
            await loadConfig();
            await getCameraDevices();
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
                await getCameraDevices();
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
    
    # Open browser after a short delay
    Timer(1.5, open_browser).start()
    
    # Run Flask app on different port than leader
    app.run(host='127.0.0.1', port=5002, debug=False)

if __name__ == "__main__":
    main() 