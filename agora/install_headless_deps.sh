#!/bin/bash
# Install dependencies for headless browser streaming on Orange Pi
# This script installs Chromium browser and Python Selenium for Agora streaming

set -e  # Exit on error

echo "=== Installing Dependencies for Headless Browser Streaming ==="
echo "This will install Chromium browser and Python Selenium"
echo ""

# Update package list
echo "Updating package list..."
sudo apt-get update

# Detect which Chromium package is available
echo ""
echo "Detecting Chromium package..."
CHROMIUM_PACKAGE=""
CHROMEDRIVER_PACKAGE=""

# Try different package names
if apt-cache show chromium-browser >/dev/null 2>&1; then
    CHROMIUM_PACKAGE="chromium-browser"
    CHROMEDRIVER_PACKAGE="chromium-chromedriver"
elif apt-cache show chromium >/dev/null 2>&1; then
    CHROMIUM_PACKAGE="chromium"
    CHROMEDRIVER_PACKAGE="chromium-driver"
elif apt-cache show chromium-bsu >/dev/null 2>&1; then
    # Some ARM systems have this package
    CHROMIUM_PACKAGE="chromium-bsu"
    CHROMEDRIVER_PACKAGE="chromium-driver"
else
    echo "WARNING: No standard Chromium package found in repositories"
    echo ""
    echo "Trying alternative installation methods..."
fi

# Install Chromium browser and driver
if [ -n "$CHROMIUM_PACKAGE" ]; then
    echo ""
    echo "Installing $CHROMIUM_PACKAGE and driver..."
    sudo apt-get install -y $CHROMIUM_PACKAGE $CHROMEDRIVER_PACKAGE || {
        echo "Failed to install $CHROMIUM_PACKAGE"
        echo "Trying without chromedriver..."
        sudo apt-get install -y $CHROMIUM_PACKAGE
    }
else
    # Alternative: Try snap
    echo "Trying to install Chromium via snap..."
    if command -v snap >/dev/null 2>&1; then
        sudo snap install chromium
    else
        echo ""
        echo "ERROR: Could not find Chromium in package manager"
        echo ""
        echo "Please try one of these methods:"
        echo "1. Enable additional repositories:"
        echo "   sudo add-apt-repository universe"
        echo "   sudo apt-get update"
        echo ""
        echo "2. Install snap and then Chromium:"
        echo "   sudo apt-get install snapd"
        echo "   sudo snap install chromium"
        echo ""
        echo "3. Download Chromium manually from:"
        echo "   https://www.chromium.org/getting-involved/download-chromium"
        echo ""
        exit 1
    fi
fi

# Install Python3 and pip if not already installed
echo ""
echo "Ensuring Python3 and pip are installed..."
sudo apt-get install -y python3 python3-pip

# Install Selenium for Python
echo ""
echo "Installing Python Selenium..."
pip3 install selenium

# Install additional dependencies that might be needed
echo ""
echo "Installing additional dependencies..."
sudo apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 || {
        echo "Some dependencies failed to install, but continuing..."
    }

# Try to install ChromeDriver separately if not installed
if ! command -v chromedriver &> /dev/null; then
    echo ""
    echo "ChromeDriver not found, trying alternative installation..."
    
    # Get system architecture
    ARCH=$(uname -m)
    case $ARCH in
        armv7l|armhf)
            DRIVER_ARCH="linux32"
            ;;
        aarch64|arm64)
            DRIVER_ARCH="linux64"
            ;;
        x86_64)
            DRIVER_ARCH="linux64"
            ;;
        *)
            echo "Unknown architecture: $ARCH"
            DRIVER_ARCH="linux64"
            ;;
    esac
    
    echo "Detected architecture: $ARCH (using $DRIVER_ARCH driver)"
    
    # Option 1: Try python chromedriver-binary
    pip3 install chromedriver-binary-auto || {
        echo "Could not install chromedriver-binary-auto"
        echo "You may need to download ChromeDriver manually from:"
        echo "https://chromedriver.chromium.org/downloads"
    }
fi

# Check if installation was successful
echo ""
echo "Checking installation..."

# Check for any Chromium installation
CHROMIUM_FOUND=false
for cmd in chromium-browser chromium chromium-bsu google-chrome; do
    if command -v $cmd &> /dev/null; then
        echo "✓ Chromium browser installed successfully ($cmd)"
        $cmd --version 2>/dev/null || echo "  Version check failed (this is normal for headless systems)"
        CHROMIUM_FOUND=true
        break
    fi
done

if [ "$CHROMIUM_FOUND" = false ]; then
    # Check snap version
    if snap list chromium &> /dev/null; then
        echo "✓ Chromium installed via snap"
        CHROMIUM_FOUND=true
    else
        echo "✗ Chromium browser installation failed"
        exit 1
    fi
fi

# Check ChromeDriver (less critical)
if command -v chromedriver &> /dev/null; then
    echo "✓ ChromeDriver installed successfully"
    chromedriver --version 2>/dev/null || echo "  Version check failed"
else
    echo "⚠ ChromeDriver not found in PATH"
    echo "  Selenium will try to find it automatically"
fi

# Check Selenium
if python3 -c "import selenium" &> /dev/null; then
    echo "✓ Python Selenium installed successfully"
    python3 -c "import selenium; print(f'  Selenium version: {selenium.__version__}')"
else
    echo "✗ Python Selenium installation failed"
    exit 1
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "You can now run the headless streaming script with:"
echo "  python3 headless_agora_streamer.py"
echo ""
echo "Note: Make sure your user has access to video devices:"
echo "  sudo usermod -a -G video $USER"
echo "  (logout and login again for this to take effect)"
echo ""
echo "If Chromium was installed via snap, you may need to:"
echo "  export PATH=$PATH:/snap/bin"
echo "" 