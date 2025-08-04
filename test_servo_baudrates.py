#!/usr/bin/env python3
"""
Quick test script to try different baudrates and protocols with your servo setup.
"""

import serial
import time

def test_baudrate(port, baudrate, motor_id=1):
    """Test a specific baudrate with Feetech protocol."""
    try:
        ser = serial.Serial(port, baudrate, timeout=0.5)
        print(f"\n📡 Testing baudrate {baudrate}...")
        
        # Feetech STS3215 ping packet format
        # [0xFF, 0xFF, ID, Length, Instruction, Checksum]
        ping_packet = bytes([0xFF, 0xFF, motor_id, 0x02, 0x01])
        checksum = (~(motor_id + 0x02 + 0x01)) & 0xFF
        ping_packet += bytes([checksum])
        
        print(f"  Sending: {ping_packet.hex()}")
        
        ser.reset_input_buffer()
        ser.write(ping_packet)
        time.sleep(0.05)  # Wait for response
        
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"  ✓ Response: {response.hex()} (len={len(response)})")
            
            # Check if it looks like valid Feetech response
            if len(response) >= 4 and response[0] == 0xFF and response[1] == 0xFF:
                print(f"  🎯 VALID Feetech response detected!")
                return True, response
            else:
                print(f"  ⚠️  Response format doesn't match Feetech protocol")
                return False, response
        else:
            print(f"  ❌ No response")
            return False, None
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False, None
    finally:
        try:
            ser.close()
        except:
            pass

def test_common_protocols(port, baudrate=1000000):
    """Test other common servo protocols."""
    try:
        ser = serial.Serial(port, baudrate, timeout=0.5)
        print(f"\n🔍 Testing other protocols at {baudrate} baud...")
        
        # Test different servo protocols
        tests = [
            # LewanSoul LX-16A protocol
            (bytes([0x55, 0x55, 0x01, 0x02, 0x01, 0xFB]), "LewanSoul LX-16A ping"),
            
            # Dynamixel protocol 
            (bytes([0xFF, 0xFF, 0x01, 0x02, 0x01, 0xFB]), "Dynamixel ping"),
            
            # Simple ASCII test
            (b"#1P1500\r", "ASCII servo command"),
            
            # SC15 protocol (common with Waveshare)
            (bytes([0xFF, 0xFF, 0x01, 0x03, 0x01, 0x00, 0xFB]), "SC15-style ping"),
        ]
        
        for packet, description in tests:
            print(f"  Testing {description}...")
            print(f"    Sending: {packet.hex()}")
            
            ser.reset_input_buffer()
            ser.write(packet)
            time.sleep(0.05)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"    ✓ Response: {response.hex()}")
                
                # Try to decode as ASCII too
                try:
                    ascii_resp = response.decode('ascii', errors='ignore').strip()
                    if ascii_resp:
                        print(f"    ASCII: '{ascii_resp}'")
                except:
                    pass
            else:
                print(f"    ❌ No response")
                
    except Exception as e:
        print(f"❌ Protocol test error: {e}")
    finally:
        try:
            ser.close()
        except:
            pass

def main():
    port = "/dev/tty.usbmodem5A460813891"  # Your port
    
    print("🔧 SERVO COMMUNICATION DIAGNOSTIC")
    print("=" * 50)
    
    # Test common baudrates
    common_baudrates = [1000000, 115200, 57600, 38400, 19200, 9600]
    
    working_baudrates = []
    
    for baudrate in common_baudrates:
        success, response = test_baudrate(port, baudrate)
        if success:
            working_baudrates.append(baudrate)
    
    if working_baudrates:
        print(f"\n🎉 SUCCESS! Working baudrates: {working_baudrates}")
        print(f"Use baudrate {working_baudrates[0]} in your main script")
    else:
        print(f"\n❌ No Feetech responses found. Testing other protocols...")
        # Test with most common baudrate
        test_common_protocols(port, 115200)
        test_common_protocols(port, 1000000)
    
    print(f"\n" + "=" * 50)
    print(f"💡 NEXT STEPS:")
    print(f"1. Check your servo model numbers physically")
    print(f"2. Look up Waveshare board documentation for protocol details")
    print(f"3. If using different servos, you'll need different control code")

if __name__ == "__main__":
    main()