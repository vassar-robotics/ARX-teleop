# Chromium Installation Guide for ARM Linux

If the `chromium-browser` package is not available on your Orange Pi or ARM device, try these alternatives:

## Quick Solutions

### 1. Try Different Package Names
```bash
# Try these in order:
sudo apt-get install chromium
sudo apt-get install chromium-bsu
sudo apt-get install chromium-browser-l10n
```

### 2. Enable Additional Repositories
```bash
# For Ubuntu/Debian based systems
sudo add-apt-repository universe
sudo apt-get update
sudo apt-get install chromium-browser
```

### 3. Install via Snap
```bash
# Install snapd first
sudo apt-get install snapd
sudo systemctl enable --now snapd.socket

# Install Chromium
sudo snap install chromium

# Add snap to PATH
export PATH=$PATH:/snap/bin
echo 'export PATH=$PATH:/snap/bin' >> ~/.bashrc
```

## Distribution-Specific Instructions

### Armbian (Orange Pi)
```bash
# Update sources
sudo apt-get update
sudo apt-get install chromium
```

### Raspberry Pi OS
```bash
sudo apt-get update
sudo apt-get install chromium-browser chromium-chromedriver
```

### Ubuntu on ARM
```bash
sudo apt-get update
sudo apt-get install chromium-browser chromium-chromedriver
```

### Debian on ARM
```bash
sudo apt-get update
sudo apt-get install chromium chromium-driver
```

## Manual Installation

If package managers fail, you can download Chromium manually:

### For ARMv7 (32-bit ARM)
```bash
# Download from Debian repositories
wget http://ftp.debian.org/debian/pool/main/c/chromium/chromium_<version>_armhf.deb
sudo dpkg -i chromium_*.deb
sudo apt-get install -f  # Fix dependencies
```

### For ARM64 (64-bit ARM)
```bash
# Download from Debian repositories
wget http://ftp.debian.org/debian/pool/main/c/chromium/chromium_<version>_arm64.deb
sudo dpkg -i chromium_*.deb
sudo apt-get install -f  # Fix dependencies
```

## Verify Installation

After installation, verify Chromium is available:

```bash
# Check if installed
which chromium || which chromium-browser || which chromium-bsu

# Test headless mode
chromium --headless --disable-gpu --dump-dom https://www.google.com
```

## Alternative: Firefox

If Chromium is problematic, Firefox ESR might work:
```bash
sudo apt-get install firefox-esr

# Modify the headless_agora_streamer.py to use Firefox:
# Change: driver = webdriver.Chrome(options=options)
# To: driver = webdriver.Firefox(options=options)
```

## Check Your System

Find out what packages are available:
```bash
# Search for chromium packages
apt-cache search chromium | grep browser

# Check your architecture
uname -m

# Check your OS version
cat /etc/os-release
```

## Updated Install Script

The updated `install_headless_deps.sh` now automatically detects and installs the correct Chromium package for your system. Just run:

```bash
./install_headless_deps.sh
```

It will try multiple package names and installation methods automatically. 