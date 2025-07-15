#!/usr/bin/env python3
"""
Agora Video Streaming - Follower Side
Captures video from 3 cameras and streams to Agora channels
"""

import sys
import cv2
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from queue import Queue
import logging

try:
    import agorartc
except ImportError:
    print("Error: agora-python-sdk not installed")
    print("Please install it with: pip install agora-python-sdk")
    sys.exit(1)

import agora_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VideoCapture:
    """Handles video capture from a camera."""
    
    def __init__(self, camera_index, name):
        self.camera_index = camera_index
        self.name = name
        self.cap = None
        self.frame_queue = Queue(maxsize=30)
        self.running = False
        self.thread = None
        
    def start(self):
        """Start capturing video."""
        self.cap = cv2.VideoCapture(self.camera_index)
        
        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, agora_config.VIDEO_PROFILE["width"])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, agora_config.VIDEO_PROFILE["height"])
        self.cap.set(cv2.CAP_PROP_FPS, agora_config.VIDEO_PROFILE["frameRate"])
        
        if not self.cap.isOpened():
            logger.error(f"Failed to open camera {self.camera_index}")
            return False
            
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        logger.info(f"Started capture for {self.name}")
        return True
        
    def _capture_loop(self):
        """Capture loop running in separate thread."""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Drop old frames if queue is full
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except:
                        pass
                self.frame_queue.put(frame)
            else:
                time.sleep(0.01)
                
    def get_frame(self):
        """Get the latest frame."""
        try:
            return self.frame_queue.get_nowait()
        except:
            return None
            
    def stop(self):
        """Stop capturing video."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        if self.cap:
            self.cap.release()
        logger.info(f"Stopped capture for {self.name}")


class AgoraVideoStreamer(agorartc.VideoFrameObserver):
    """Handles streaming video to Agora."""
    
    def __init__(self, channel_name):
        super().__init__()
        self.channel_name = channel_name
        self.rtc = None
        self.joined = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
    def initialize(self):
        """Initialize Agora RTC engine."""
        self.rtc = agorartc.createRtcEngineBridge()
        eventHandler = agorartc.RtcEngineEventHandlerBase()
        
        # Set event callbacks
        eventHandler.onJoinChannelSuccess = self._on_join_channel_success
        eventHandler.onLeaveChannel = self._on_leave_channel
        eventHandler.onError = self._on_error
        
        self.rtc.initEventHandler(eventHandler)
        
        # Initialize the RTC engine
        ret = self.rtc.initialize(agora_config.APP_ID, None, agorartc.AREA_CODE_GLOB & 0xFFFFFFFF)
        if ret != 0:
            logger.error(f"Failed to initialize RTC engine: {ret}")
            return False
            
        # Enable video
        self.rtc.enableVideo()
        
        # Set video encoder configuration
        config = agorartc.VideoEncoderConfiguration()
        config.dimensions.width = agora_config.VIDEO_PROFILE["width"]
        config.dimensions.height = agora_config.VIDEO_PROFILE["height"]
        config.frameRate = agora_config.VIDEO_PROFILE["frameRate"]
        config.bitrate = agora_config.VIDEO_PROFILE["bitrate"]
        self.rtc.setVideoEncoderConfiguration(config)
        
        # Register as video frame observer
        self.rtc.registerVideoFrameObserver(self)
        
        logger.info(f"Initialized Agora streamer for {self.channel_name}")
        return True
        
    def join_channel(self):
        """Join the Agora channel."""
        ret = self.rtc.joinChannel("", self.channel_name, "", 0)
        if ret != 0:
            logger.error(f"Failed to join channel {self.channel_name}: {ret}")
            return False
        return True
        
    def update_frame(self, frame):
        """Update the current frame to be sent."""
        with self.frame_lock:
            self.current_frame = frame
            
    def onCaptureVideoFrame(self, width, height, yBuffer, uBuffer, vBuffer):
        """Called when Agora needs a video frame."""
        with self.frame_lock:
            if self.current_frame is None:
                return True
                
            # Convert BGR to YUV420
            yuv = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2YUV_I420)
            
            # Copy Y, U, V planes
            y_size = width * height
            u_size = v_size = y_size // 4
            
            yBuffer[:y_size] = yuv[:y_size].tobytes()
            uBuffer[:u_size] = yuv[y_size:y_size + u_size].tobytes()
            vBuffer[:v_size] = yuv[y_size + u_size:].tobytes()
            
        return True
        
    def leave_channel(self):
        """Leave the Agora channel."""
        if self.rtc and self.joined:
            self.rtc.leaveChannel()
            
    def release(self):
        """Release resources."""
        if self.rtc:
            self.rtc.unregisterVideoFrameObserver()
            self.rtc.release()
            
    def _on_join_channel_success(self, channel, uid, elapsed):
        """Callback when successfully joined channel."""
        self.joined = True
        logger.info(f"Joined channel {channel} with uid {uid}")
        
    def _on_leave_channel(self, stats):
        """Callback when left channel."""
        self.joined = False
        logger.info(f"Left channel {self.channel_name}")
        
    def _on_error(self, err):
        """Callback when error occurs."""
        logger.error(f"Agora error: {err}")


class VideoStreamFollowerApp:
    """Main application for follower video streaming."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(agora_config.WINDOW_TITLE_FOLLOWER)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.cameras = []
        self.streamers = []
        self.streaming = False
        self.preview_labels = []
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="wens")
        
        # Title
        title_label = ttk.Label(main_frame, text="Robot Camera Streaming", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)
        
        # Camera preview grid
        preview_frame = ttk.LabelFrame(main_frame, text="Camera Previews", padding="10")
        preview_frame.grid(row=1, column=0, columnspan=3, pady=10)
        
        # Create preview labels for 3 cameras
        for i in range(3):
            label = ttk.Label(preview_frame, text=f"Camera {i+1}\nNot Connected",
                            relief=tk.SUNKEN, width=40, anchor=tk.CENTER)
            label.grid(row=i//2, column=i%2, padx=5, pady=5)
            self.preview_labels.append(label)
            
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=2, column=0, columnspan=3, pady=10, sticky="we")
        
        self.status_text = tk.Text(status_frame, height=5, width=60)
        self.status_text.grid(row=0, column=0, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(status_frame, command=self.status_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.status_text['yscrollcommand'] = scrollbar.set
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Streaming",
                                      command=self.start_streaming)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop Streaming",
                                     command=self.stop_streaming, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # Camera selection
        camera_frame = ttk.LabelFrame(main_frame, text="Camera Configuration", padding="10")
        camera_frame.grid(row=4, column=0, columnspan=3, pady=10, sticky="we")
        
        ttk.Label(camera_frame, text="Camera Indices (comma-separated):").grid(row=0, column=0, padx=5)
        self.camera_indices_var = tk.StringVar(value="0,1,2")
        ttk.Entry(camera_frame, textvariable=self.camera_indices_var, width=20).grid(row=0, column=1, padx=5)
        
        # App ID entry
        ttk.Label(camera_frame, text="Agora App ID:").grid(row=1, column=0, padx=5, pady=5)
        self.app_id_var = tk.StringVar(value=agora_config.APP_ID)
        ttk.Entry(camera_frame, textvariable=self.app_id_var, width=40, show="*").grid(row=1, column=1, padx=5)
        
    def log_status(self, message):
        """Log a status message."""
        timestamp = time.strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        self.root.update()
        
    def start_streaming(self):
        """Start streaming video."""
        # Update App ID if changed
        new_app_id = self.app_id_var.get().strip()
        if new_app_id and new_app_id != "YOUR_AGORA_APP_ID":
            agora_config.APP_ID = new_app_id
        else:
            messagebox.showerror("Error", "Please enter a valid Agora App ID")
            return
            
        # Parse camera indices
        try:
            indices = [int(x.strip()) for x in self.camera_indices_var.get().split(',')]
            if len(indices) != 3:
                raise ValueError("Need exactly 3 camera indices")
        except Exception as e:
            messagebox.showerror("Error", f"Invalid camera indices: {e}")
            return
            
        self.log_status("Starting video streaming...")
        
        # Initialize cameras
        for i, idx in enumerate(indices):
            camera = VideoCapture(idx, f"Camera {i+1}")
            if camera.start():
                self.cameras.append(camera)
                self.log_status(f"Initialized camera {i+1} (index {idx})")
            else:
                self.log_status(f"Failed to initialize camera {i+1} (index {idx})")
                
        if not self.cameras:
            messagebox.showerror("Error", "No cameras could be initialized")
            return
            
        # Initialize Agora streamers
        for i, (name, channel) in enumerate(agora_config.VIDEO_CHANNELS.items()):
            streamer = AgoraVideoStreamer(channel)
            if streamer.initialize() and streamer.join_channel():
                self.streamers.append(streamer)
                self.log_status(f"Initialized Agora streamer for {name}")
            else:
                self.log_status(f"Failed to initialize Agora streamer for {name}")
                
        if not self.streamers:
            messagebox.showerror("Error", "Failed to initialize Agora streamers")
            self.cleanup()
            return
            
        self.streaming = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # Start streaming thread
        threading.Thread(target=self.streaming_loop, daemon=True).start()
        
        self.log_status("Streaming started successfully")
        
    def streaming_loop(self):
        """Main streaming loop."""
        while self.streaming:
            try:
                # Get frames from cameras and send to streamers
                for i, (camera, streamer) in enumerate(zip(self.cameras, self.streamers)):
                    frame = camera.get_frame()
                    if frame is not None:
                        # Update streamer
                        streamer.update_frame(frame)
                        
                        # Update preview (downsample for display)
                        preview = cv2.resize(frame, (160, 120))
                        # Convert to RGB for display
                        preview_rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
                        
                        # Update preview in UI (would need PIL for proper display)
                        self.preview_labels[i].config(text=f"Camera {i+1}\nStreaming...")
                        
                time.sleep(1.0 / agora_config.VIDEO_PROFILE["frameRate"])
                
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                
    def stop_streaming(self):
        """Stop streaming video."""
        self.log_status("Stopping video streaming...")
        self.streaming = False
        
        # Stop streamers
        for streamer in self.streamers:
            streamer.leave_channel()
            streamer.release()
        self.streamers.clear()
        
        # Stop cameras
        for camera in self.cameras:
            camera.stop()
        self.cameras.clear()
        
        # Reset UI
        for label in self.preview_labels:
            label.config(text=f"Camera\nNot Connected")
            
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        self.log_status("Streaming stopped")
        
    def cleanup(self):
        """Clean up resources."""
        if self.streaming:
            self.stop_streaming()
            
    def on_closing(self):
        """Handle window closing."""
        self.cleanup()
        self.root.destroy()
        
    def run(self):
        """Run the application."""
        self.log_status("Video Stream Follower ready")
        self.log_status("Enter your Agora App ID and click 'Start Streaming'")
        self.root.mainloop()


def main():
    app = VideoStreamFollowerApp()
    app.run()


if __name__ == "__main__":
    main() 