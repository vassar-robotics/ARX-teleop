#!/bin/bash
# Setup USB permissions for robot arm teleoperation on Linux
# This script creates udev rules to allow non-root access to USB serial devices

set -e  # Exit on error

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "This script is only for Linux systems"
    exit 1
fi

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run this script with sudo:"
    echo "  sudo $0"
    exit 1
fi

RULES_FILE="/etc/udev/rules.d/99-robot-usb-serial.rules"

echo "Setting up USB permissions for robot teleoperation..."
echo

# Create udev rules file
cat > "$RULES_FILE" << 'EOF'
# USB Serial Device Rules for Robot Arms
# This file allows all users to access USB serial devices
# Created by setup_usb_permissions_linux.sh

# For FTDI USB Serial devices (common for robot controllers)
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", MODE="0666"

# For CH340/CH341 USB Serial devices
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0666"

# For CP210x USB Serial devices
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", MODE="0666"

# For Prolific USB Serial devices
SUBSYSTEM=="tty", ATTRS{idVendor}=="067b", MODE="0666"

# For ACM devices (Arduino, etc.)
SUBSYSTEM=="tty", KERNEL=="ttyACM[0-9]*", MODE="0666"

# For USB devices (FTDI, etc.)
SUBSYSTEM=="tty", KERNEL=="ttyUSB[0-9]*", MODE="0666"
EOF

echo "✓ Created udev rules file: $RULES_FILE"

# Reload udev rules
echo "Reloading udev rules..."
udevadm control --reload-rules
udevadm trigger

echo "✓ Udev rules reloaded"

# Add current user to dialout group if not root
if [ -n "$SUDO_USER" ]; then
    if ! groups "$SUDO_USER" | grep -q '\bdialout\b'; then
        usermod -a -G dialout "$SUDO_USER"
        echo "✓ Added user '$SUDO_USER' to dialout group"
        echo
        echo "NOTE: You need to log out and back in for group membership to take effect"
    else
        echo "✓ User '$SUDO_USER' is already in dialout group"
    fi
fi

echo
echo "USB permissions setup complete!"
echo
echo "The following USB serial devices will now be accessible without sudo:"
echo "  - /dev/ttyUSB* (FTDI, CH340, CP210x, Prolific adapters)"
echo "  - /dev/ttyACM* (Arduino-style devices)"
echo
echo "If you still have permission issues:"
echo "  1. Try unplugging and reconnecting your USB devices"
echo "  2. Log out and back in (if user was added to dialout group)"
echo "  3. Reboot if problems persist" 