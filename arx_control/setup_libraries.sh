#!/bin/bash
# Setup script to download or build ARX libraries for the current platform

echo "Setting up ARX libraries for $(uname -s)..."

# Detect platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Linux detected"
    # Option: Download pre-built Linux binaries
    # wget https://your-server.com/arx-libs-linux.tar.gz
    # tar -xzf arx-libs-linux.tar.gz -C arx_control/lib/
    
    # Or copy from R5 SDK if available
    if [ -d "/home/vassar/code/R5/py/ARX_R5_python/bimanual/lib" ]; then
        echo "Copying libraries from R5 SDK..."
        cp -r /home/vassar/code/R5/py/ARX_R5_python/bimanual/lib/* arx_control/lib/
    else
        echo "ERROR: R5 SDK not found. Please install the ARX R5 SDK first."
        exit 1
    fi
    
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macOS detected"
    echo "ERROR: ARX libraries for macOS are not yet available."
    echo "Please contact ARX support for macOS binaries."
    exit 1
else
    echo "Unsupported platform: $OSTYPE"
    exit 1
fi

echo "Library setup complete!"