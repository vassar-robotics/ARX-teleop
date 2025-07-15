#!/usr/bin/env python3
"""
Test script to verify Agora connectivity
"""

import sys
import time

try:
    import agorartc
except ImportError:
    print("Error: agora-python-sdk not installed")
    print("Please install it with: pip install agora-python-sdk")
    sys.exit(1)

try:
    import agora_config
    DEFAULT_APP_ID = agora_config.APP_ID
except:
    DEFAULT_APP_ID = None


def test_agora_connection(app_id):
    """Test basic Agora connectivity."""
    print("Testing Agora connection...")
    
    # Create RTC engine
    rtc = agorartc.createRtcEngineBridge()
    eventHandler = agorartc.RtcEngineEventHandlerBase()
    
    # Track connection status
    connected = False
    error_occurred = False
    
    def on_join_success(channel, uid, elapsed):
        nonlocal connected
        connected = True
        print(f"✓ Successfully joined channel '{channel}' with UID {uid}")
        
    def on_error(err):
        nonlocal error_occurred
        error_occurred = True
        print(f"✗ Error occurred: {err}")
        
    def on_warning(warn):
        print(f"⚠ Warning: {warn}")
    
    # Set callbacks
    eventHandler.onJoinChannelSuccess = on_join_success
    eventHandler.onError = on_error
    eventHandler.onWarning = on_warning
    
    # Initialize
    rtc.initEventHandler(eventHandler)
    ret = rtc.initialize(app_id, None, agorartc.AREA_CODE_GLOB & 0xFFFFFFFF)
    
    if ret != 0:
        print(f"✗ Failed to initialize RTC engine: {ret}")
        return False
        
    print("✓ RTC engine initialized")
    
    # Enable video
    ret = rtc.enableVideo()
    if ret != 0:
        print(f"✗ Failed to enable video: {ret}")
        return False
        
    print("✓ Video enabled")
    
    # Join test channel
    test_channel = "agora_test_channel"
    print(f"Joining test channel '{test_channel}'...")
    
    ret = rtc.joinChannel("", test_channel, "", 0)
    if ret != 0:
        print(f"✗ Failed to join channel: {ret}")
        return False
        
    # Wait for connection
    timeout = 10  # seconds
    start_time = time.time()
    
    while not connected and not error_occurred and (time.time() - start_time) < timeout:
        time.sleep(0.1)
        
    if connected:
        print("\n✓ Agora connection test PASSED!")
        print(f"Successfully connected to Agora servers")
        
        # Leave channel
        rtc.leaveChannel()
        time.sleep(1)
    else:
        print("\n✗ Agora connection test FAILED!")
        if error_occurred:
            print("An error occurred during connection")
        else:
            print("Connection timed out")
            
    # Cleanup
    rtc.release()
    
    return connected


def main():
    print("=== Agora Connection Test ===\n")
    
    # Get App ID
    if len(sys.argv) > 1:
        app_id = sys.argv[1]
    else:
        if DEFAULT_APP_ID and DEFAULT_APP_ID != "YOUR_AGORA_APP_ID":
            app_id = DEFAULT_APP_ID
            print(f"Using App ID from agora_config.py")
        else:
            app_id = input("Enter your Agora App ID: ").strip()
        
    if not app_id or app_id == "YOUR_AGORA_APP_ID":
        print("Error: Please provide a valid Agora App ID")
        sys.exit(1)
        
    # Run test
    success = test_agora_connection(app_id)
    
    print("\n" + "="*30)
    if success:
        print("✓ Your Agora setup is working correctly!")
        print("You can now run the video streaming scripts.")
    else:
        print("✗ Agora connection failed!")
        print("\nTroubleshooting tips:")
        print("1. Verify your App ID is correct")
        print("2. Check your internet connection")
        print("3. Ensure firewall allows Agora connections")
        print("4. Try creating a new project in Agora Console")
        
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 