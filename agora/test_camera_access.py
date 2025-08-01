#!/usr/bin/env python3
"""
Simple camera access test for macOS
"""

import cv2
import sys

def test_camera_access():
    """Test camera access using OpenCV"""
    print("Testing camera access...")
    
    # Try cameras 0-3
    for camera_index in range(4):
        print(f"\nTesting camera {camera_index}...")
        cap = cv2.VideoCapture(camera_index)
        
        if cap.isOpened():
            print(f"✓ Camera {camera_index} is available")
            
            # Try to read a frame
            ret, frame = cap.read()
            if ret:
                print(f"✓ Camera {camera_index} can capture frames")
                print(f"  Frame size: {frame.shape}")
            else:
                print(f"✗ Camera {camera_index} cannot capture frames")
            
            cap.release()
        else:
            print(f"✗ Camera {camera_index} is not available")
    
    print("\nCamera test completed!")

if __name__ == "__main__":
    test_camera_access() 