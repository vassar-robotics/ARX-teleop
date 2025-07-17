#!/bin/bash

# Fix APT Sources Script
# This script replaces problematic APT mirrors with official Debian/Ubuntu repositories

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}APT Sources Fix Script${NC}"
echo "======================="

# Function to detect distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

# Function to get codename
get_codename() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [ -n "$VERSION_CODENAME" ]; then
            echo "$VERSION_CODENAME"
        else
            # Fallback for systems without VERSION_CODENAME
            lsb_release -cs 2>/dev/null || echo "stable"
        fi
    else
        echo "stable"
    fi
}

# Detect distribution and codename
DISTRO=$(detect_distro)
CODENAME=$(get_codename)

echo -e "Detected: ${YELLOW}$DISTRO${NC} (${YELLOW}$CODENAME${NC})"

# Backup current sources.list
if [ -f /etc/apt/sources.list ]; then
    echo -e "\n${GREEN}Backing up current sources.list...${NC}"
    sudo cp /etc/apt/sources.list "/etc/apt/sources.list.bak.$(date +%Y%m%d_%H%M%S)"
    echo "Backup created"
else
    echo -e "${RED}Warning: /etc/apt/sources.list not found${NC}"
fi

# Create new sources.list content based on distribution
case "$DISTRO" in
    debian)
        echo -e "\n${GREEN}Creating Debian sources.list...${NC}"
        cat > /tmp/sources.list << EOF
# Official Debian repositories
deb http://deb.debian.org/debian $CODENAME main contrib non-free
deb-src http://deb.debian.org/debian $CODENAME main contrib non-free

# Security updates
deb http://security.debian.org/debian-security $CODENAME-security main contrib non-free
deb-src http://security.debian.org/debian-security $CODENAME-security main contrib non-free

# Point release updates
deb http://deb.debian.org/debian $CODENAME-updates main contrib non-free
deb-src http://deb.debian.org/debian $CODENAME-updates main contrib non-free
EOF
        ;;
    
    ubuntu)
        echo -e "\n${GREEN}Creating Ubuntu sources.list...${NC}"
        cat > /tmp/sources.list << EOF
# Official Ubuntu repositories
deb http://archive.ubuntu.com/ubuntu/ $CODENAME main restricted universe multiverse
deb-src http://archive.ubuntu.com/ubuntu/ $CODENAME main restricted universe multiverse

# Updates
deb http://archive.ubuntu.com/ubuntu/ $CODENAME-updates main restricted universe multiverse
deb-src http://archive.ubuntu.com/ubuntu/ $CODENAME-updates main restricted universe multiverse

# Security updates
deb http://security.ubuntu.com/ubuntu/ $CODENAME-security main restricted universe multiverse
deb-src http://security.ubuntu.com/ubuntu/ $CODENAME-security main restricted universe multiverse

# Backports (optional, commented out by default)
# deb http://archive.ubuntu.com/ubuntu/ $CODENAME-backports main restricted universe multiverse
# deb-src http://archive.ubuntu.com/ubuntu/ $CODENAME-backports main restricted universe multiverse
EOF
        ;;
    
    raspbian)
        echo -e "\n${GREEN}Creating Raspbian sources.list...${NC}"
        cat > /tmp/sources.list << EOF
# Official Raspbian repositories
deb http://raspbian.raspberrypi.org/raspbian/ $CODENAME main contrib non-free rpi
deb-src http://raspbian.raspberrypi.org/raspbian/ $CODENAME main contrib non-free rpi

# Raspberry Pi Foundation repository
deb http://archive.raspberrypi.org/debian/ $CODENAME main
EOF
        ;;
    
    *)
        echo -e "${RED}Unknown distribution: $DISTRO${NC}"
        echo "Please manually configure your sources.list"
        exit 1
        ;;
esac

# Show proposed changes
echo -e "\n${YELLOW}Proposed sources.list:${NC}"
cat /tmp/sources.list

# Ask for confirmation
read -p "Do you want to apply these changes? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Cancelled. No changes made.${NC}"
    rm /tmp/sources.list
    exit 0
fi

# Apply changes
echo -e "\n${GREEN}Applying changes...${NC}"
sudo cp /tmp/sources.list /etc/apt/sources.list
rm /tmp/sources.list

# Install HTTPS transport if needed
echo -e "\n${GREEN}Ensuring HTTPS transport is available...${NC}"
sudo apt-get update || true
sudo apt-get install -y apt-transport-https ca-certificates || true

# Update package lists
echo -e "\n${GREEN}Updating package lists...${NC}"
sudo apt-get update

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Success! APT sources have been fixed.${NC}"
    echo -e "Your old sources.list has been backed up with timestamp."
else
    echo -e "\n${RED}Warning: apt-get update encountered errors.${NC}"
    echo "You may need to check the configuration manually."
fi

# Optional: List available mirrors
echo -e "\n${YELLOW}Alternative mirrors:${NC}"
case "$DISTRO" in
    debian)
        echo "For faster downloads, see: https://www.debian.org/mirror/list"
        echo "Example mirrors:"
        echo "  - US: http://ftp.us.debian.org/debian/"
        echo "  - EU: http://ftp.de.debian.org/debian/"
        echo "  - Asia: http://ftp.jp.debian.org/debian/"
        ;;
    ubuntu)
        echo "For faster downloads, see: https://launchpad.net/ubuntu/+archivemirrors"
        echo "Example mirrors:"
        echo "  - US: http://us.archive.ubuntu.com/ubuntu/"
        echo "  - EU: http://de.archive.ubuntu.com/ubuntu/"
        echo "  - Asia: http://jp.archive.ubuntu.com/ubuntu/"
        ;;
esac

echo -e "\n${GREEN}Done!${NC}" 