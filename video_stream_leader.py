#!/usr/bin/env python3
"""
Agora Video Streaming - Leader Side
Receives and displays 3 video feeds from Agora channels
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
from PIL import Image, ImageTk

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


class AgoraVideoReceiver(agorartc.VideoFrameObserver):
    """Handles receiving video from Agora."""
    
    def __init__(self, channel_name):
        super().__init__()
        self.channel_name = channel_name
        self.rtc = None
        self.joined = False
        self.frame_queue = Queue(maxsize=30)
        self.remote_users = {}
        
    def initialize(self):
        """Initialize Agora RTC engine."""
        self.rtc = agorartc.createRtcEngineBridge()
        eventHandler = agorartc.RtcEngineEventHandlerBase()
        
        # Set event callbacks
        eventHandler.onJoinChannelSuccess = self._on_join_channel_success
        eventHandler.onUserJoined = self._on_user_joined
        eventHandler.onUserOffline = self._on_user_offline
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
        
        # Set to receive video only (not send)
        self.rtc.setClientRole(agorartc.CLIENT_ROLE_AUDIENCE)
        
        # Register as video frame observer
        self.rtc.registerVideoFrameObserver(self)
        
        logger.info(f"Initialized Agora receiver for {self.channel_name}")
        return True
        
    def join_channel(self):
        """Join the Agora channel."""
        ret = self.rtc.joinChannel("", self.channel_name, "", 0)
        if ret != 0:
            logger.error(f"Failed to join channel {self.channel_name}: {ret}")
            return False
        return True
        
    def onRenderVideoFrame(self, uid, width, height, yBuffer, uBuffer, vBuffer, rotation, timestamp):
        """Called when receiving a video frame from remote user."""
        try:
            # Reconstruct YUV420 frame
            y_size = width * height
            u_size = v_size = y_size // 4
            
            # Create YUV array
            yuv = np.zeros(y_size + u_size + v_size, dtype=np.uint8)
            yuv[:y_size] = np.frombuffer(yBuffer[:y_size], dtype=np.uint8)
            yuv[y_size:y_size + u_size] = np.frombuffer(uBuffer[:u_size], dtype=np.uint8)
            yuv[y_size + u_size:] = np.frombuffer(vBuffer[:v_size], dtype=np.uint8)
            
            # Reshape to YUV420 format
            yuv = yuv.reshape((height * 3 // 2, width))
            
            # Convert to BGR
            bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
            
            # Add to queue
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except:
                    pass
            self.frame_queue.put(bgr)
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            
        return True
        
    def get_frame(self):
        """Get the latest frame."""
        try:
            return self.frame_queue.get_nowait()
        except:
            return None
            
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
        
    def _on_user_joined(self, uid, elapsed):
        """Callback when a remote user joins."""
        self.remote_users[uid] = True
        logger.info(f"User {uid} joined channel {self.channel_name}")
        
    def _on_user_offline(self, uid, reason):
        """Callback when a remote user leaves."""
        if uid in self.remote_users:
            del self.remote_users[uid]
        logger.info(f"User {uid} left channel {self.channel_name}")
        
    def _on_leave_channel(self, stats):
        """Callback when left channel."""
        self.joined = False
        logger.info(f"Left channel {self.channel_name}")
        
    def _on_error(self, err):
        """Callback when error occurs."""
        logger.error(f"Agora error: {err}")


class VideoStreamLeaderApp:
    """Main application for leader video streaming."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(agora_config.WINDOW_TITLE_LEADER)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.receivers = []
        self.receiving = False
        self.video_labels = []
        self.no_signal_image = None
        
        self.setup_ui()
        self.create_no_signal_image()
        
    def create_no_signal_image(self):
        """Create a 'no signal' image."""
        width, height = 320, 240
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img.fill(64)  # Dark gray
        
        # Add text
        font = cv2.FONT_HERSHEY_SIMPLEX
        text = "NO SIGNAL"
        text_size = cv2.getTextSize(text, font, 1, 2)[0]
        text_x = (width - text_size[0]) // 2
        text_y = (height + text_size[1]) // 2
        cv2.putText(img, text, (text_x, text_y), font, 1, (255, 255, 255), 2)
        
        # Convert to PIL Image
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.no_signal_image = Image.fromarray(img_rgb)
        
    def setup_ui(self):
        """Set up the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="wens")
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Robot Video Feeds - Leader", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Video display grid
        video_frame = ttk.LabelFrame(main_frame, text="Video Feeds", padding="10")
        video_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="wens")
        video_frame.columnconfigure(0, weight=1)
        video_frame.columnconfigure(1, weight=1)
        video_frame.rowconfigure(0, weight=1)
        video_frame.rowconfigure(1, weight=1)
        
        # Create video labels in 2x2 grid (3 cameras + 1 empty)
        for i in range(3):
            label = tk.Label(video_frame, bg="black", width=40, height=20)
            label.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="wens")
            self.video_labels.append(label)
            
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="we")
        
        self.status_text = tk.Text(status_frame, height=5, width=60)
        self.status_text.grid(row=0, column=0, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(status_frame, command=self.status_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.status_text['yscrollcommand'] = scrollbar.set
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Receiving",
                                      command=self.start_receiving)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop Receiving",
                                     command=self.stop_receiving, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # Recording button
        self.record_button = ttk.Button(button_frame, text="Start Recording",
                                       command=self.toggle_recording, state=tk.DISABLED)
        self.record_button.grid(row=0, column=2, padx=5)
        
        # Configuration
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky="we")
        
        # App ID entry
        ttk.Label(config_frame, text="Agora App ID:").grid(row=0, column=0, padx=5)
        self.app_id_var = tk.StringVar(value=agora_config.APP_ID)
        ttk.Entry(config_frame, textvariable=self.app_id_var, width=40, show="*").grid(row=0, column=1, padx=5)
        
        # Recording options
        self.recording_enabled = tk.BooleanVar(value=False)
        self.is_recording = False
        
    def log_status(self, message):
        """Log a status message."""
        timestamp = time.strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        self.root.update()
        
    def start_receiving(self):
        """Start receiving video."""
        # Update App ID if changed
        new_app_id = self.app_id_var.get().strip()
        if new_app_id and new_app_id != "YOUR_AGORA_APP_ID":
            agora_config.APP_ID = new_app_id
        else:
            messagebox.showerror("Error", "Please enter a valid Agora App ID")
            return
            
        self.log_status("Starting video reception...")
        
        # Initialize Agora receivers
        for i, (name, channel) in enumerate(agora_config.VIDEO_CHANNELS.items()):
            receiver = AgoraVideoReceiver(channel)
            if receiver.initialize() and receiver.join_channel():
                self.receivers.append(receiver)
                self.log_status(f"Initialized receiver for {name}")
            else:
                self.log_status(f"Failed to initialize receiver for {name}")
                
        if not self.receivers:
            messagebox.showerror("Error", "Failed to initialize receivers")
            return
            
        self.receiving = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.record_button.config(state=tk.NORMAL)
        
        # Start display thread
        threading.Thread(target=self.display_loop, daemon=True).start()
        
        self.log_status("Video reception started successfully")
        
    def display_loop(self):
        """Main display loop."""
        while self.receiving:
            try:
                # Update each video feed
                for i, receiver in enumerate(self.receivers):
                    frame = receiver.get_frame()
                    if frame is not None:
                        # Resize for display
                        display_frame = cv2.resize(frame, (320, 240))
                        
                        # Convert to RGB and PIL Image
                        frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame_rgb)
                        
                        # Convert to PhotoImage and update label
                        photo = ImageTk.PhotoImage(image=img)
                        self.video_labels[i].config(image=photo)
                        self.video_labels[i].image = photo  # Keep reference
                    else:
                        # Show no signal image
                        if self.no_signal_image:
                            photo = ImageTk.PhotoImage(image=self.no_signal_image)
                            self.video_labels[i].config(image=photo)
                            self.video_labels[i].image = photo
                            
                time.sleep(1.0 / 30)  # 30 FPS display update
                
            except Exception as e:
                logger.error(f"Display error: {e}")
                
    def stop_receiving(self):
        """Stop receiving video."""
        self.log_status("Stopping video reception...")
        self.receiving = False
        
        # Stop recording if active
        if self.is_recording:
            self.toggle_recording()
            
        # Stop receivers
        for receiver in self.receivers:
            receiver.leave_channel()
            receiver.release()
        self.receivers.clear()
        
        # Clear displays
        for label in self.video_labels:
            label.config(image='', bg='black')
            
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.record_button.config(state=tk.DISABLED)
        
        self.log_status("Video reception stopped")
        
    def toggle_recording(self):
        """Toggle video recording."""
        if not self.is_recording:
            # Start recording
            self.is_recording = True
            self.record_button.config(text="Stop Recording")
            self.log_status("Recording started (feature not implemented)")
            # TODO: Implement actual recording using Agora Cloud Recording API
        else:
            # Stop recording
            self.is_recording = False
            self.record_button.config(text="Start Recording")
            self.log_status("Recording stopped")
            
    def cleanup(self):
        """Clean up resources."""
        if self.receiving:
            self.stop_receiving()
            
    def on_closing(self):
        """Handle window closing."""
        self.cleanup()
        self.root.destroy()
        
    def run(self):
        """Run the application."""
        self.log_status("Video Stream Leader ready")
        self.log_status("Enter your Agora App ID and click 'Start Receiving'")
        self.root.mainloop()


def main():
    app = VideoStreamLeaderApp()
    app.run()


if __name__ == "__main__":
    main() 