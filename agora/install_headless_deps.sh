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

# Install Chromium browser and driver
echo ""
echo "Installing Chromium browser and driver..."
sudo apt-get install -y chromium-browser chromium-chromedriver

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
    libasound2

# Check if installation was successful
echo ""
echo "Checking installation..."
if command -v chromium-browser &> /dev/null; then
    echo "✓ Chromium browser installed successfully"
    chromium-browser --version
else
    echo "✗ Chromium browser installation failed"
    exit 1
fi

if command -v chromedriver &> /dev/null; then
    echo "✓ ChromeDriver installed successfully"
    chromedriver --version
else
    echo "✗ ChromeDriver installation failed"
    exit 1
fi

if python3 -c "import selenium" &> /dev/null; then
    echo "✓ Python Selenium installed successfully"
    python3 -c "import selenium; print(f'Selenium version: {selenium.__version__}')"
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