#!/usr/bin/env python3
"""
Simple test script to verify PubNub connectivity without robots.
Run this to test the internet connection between two computers.
"""

import time
import sys
import argparse
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.callbacks import SubscribeCallback

class TestListener(SubscribeCallback):
    def __init__(self):
        self.received_count = 0
        
    def message(self, pubnub, message):
        self.received_count += 1
        print(f"Received message #{self.received_count}: {message.message}")

def test_publisher():
    """Test publishing messages."""
    print("Starting PUBLISHER test...")
    
    pnconfig = PNConfiguration()
    pnconfig.subscribe_key = "demo"
    pnconfig.publish_key = "demo"
    pnconfig.user_id = "test-publisher"
    
    pubnub = PubNub(pnconfig)
    
    print("Publishing 5 test messages...")
    for i in range(5):
        message = {
            "test": True,
            "sequence": i + 1,
            "timestamp": time.time(),
            "data": f"Hello from publisher! Message {i + 1}"
        }
        
        pubnub.publish().channel("robot-telemetry-test").message(message).sync()
        print(f"Published message {i + 1}")
        time.sleep(1)
        
    print("\nPublisher test complete!")

def test_subscriber():
    """Test subscribing to messages."""
    print("Starting SUBSCRIBER test...")
    print("Waiting for messages (press Ctrl+C to stop)...\n")
    
    pnconfig = PNConfiguration()
    pnconfig.subscribe_key = "demo"
    pnconfig.user_id = "test-subscriber"
    pnconfig.enable_subscribe = True
    
    pubnub = PubNub(pnconfig)
    listener = TestListener()
    pubnub.add_listener(listener)
    
    pubnub.subscribe().channels(["robot-telemetry-test"]).execute()
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"\n\nSubscriber test complete! Received {listener.received_count} messages.")
        pubnub.unsubscribe_all()

def main():
    parser = argparse.ArgumentParser(description="Test PubNub connection")
    parser.add_argument("mode", choices=["pub", "sub"], 
                       help="Run as publisher (pub) or subscriber (sub)")
    
    args = parser.parse_args()
    
    if args.mode == "pub":
        test_publisher()
    else:
        test_subscriber()

if __name__ == "__main__":
    main() 