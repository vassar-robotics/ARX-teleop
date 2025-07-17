#!/bin/bash

# Fix Selenium/Certifi Compatibility Issue
# This script reinstalls selenium and its dependencies to fix the "certifi has no attribute where" error

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Selenium/Certifi Fix Script${NC}"
echo "==========================="

# Function to check if we're in a virtual environment
check_venv() {
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        echo -e "${GREEN}Virtual environment detected: $VIRTUAL_ENV${NC}"
        return 0
    elif command -v conda &> /dev/null && conda info --envs | grep -q '\*'; then
        echo -e "${GREEN}Conda environment detected${NC}"
        return 0
    else
        echo -e "${YELLOW}No virtual environment detected${NC}"
        return 1
    fi
}

# Check for virtual environment
if check_venv; then
    PIP_CMD="pip"
else
    echo -e "${YELLOW}Using system pip (sudo may be required)${NC}"
    PIP_CMD="pip3"
    # Check if we need sudo
    if [[ $EUID -ne 0 ]]; then
        PIP_CMD="sudo pip3"
    fi
fi

echo -e "\n${GREEN}Step 1: Uninstalling problematic packages...${NC}"
$PIP_CMD uninstall -y certifi urllib3 selenium 2>/dev/null || true

echo -e "\n${GREEN}Step 2: Clearing pip cache...${NC}"
if command -v pip &> /dev/null; then
    pip cache purge 2>/dev/null || $PIP_CMD cache purge 2>/dev/null || true
fi

echo -e "\n${GREEN}Step 3: Installing specific compatible versions...${NC}"
# Install specific versions known to work together
$PIP_CMD install --no-cache-dir certifi==2023.7.22
$PIP_CMD install --no-cache-dir urllib3==1.26.18
$PIP_CMD install --no-cache-dir selenium==4.15.2

echo -e "\n${GREEN}Step 4: Verifying installation...${NC}"
python3 -c "
import certifi
import selenium
from selenium import webdriver
print(f'✓ Certifi version: {certifi.__version__}')
print(f'✓ Selenium version: {selenium.__version__}')
print(f'✓ Certifi where: {certifi.where()}')
print('✓ All imports successful!')
" && echo -e "${GREEN}Installation verified successfully!${NC}" || {
    echo -e "${RED}Verification failed!${NC}"
    echo -e "${YELLOW}Trying alternative fix...${NC}"
    
    # Alternative fix: reinstall with upgrade
    $PIP_CMD install --upgrade --force-reinstall certifi
    $PIP_CMD install --upgrade --force-reinstall urllib3
    $PIP_CMD install --upgrade --force-reinstall selenium
    
    # Try verification again
    python3 -c "
import certifi
import selenium
from selenium import webdriver
print('✓ Alternative fix successful!')
" && echo -e "${GREEN}Alternative fix worked!${NC}" || {
        echo -e "${RED}Still having issues. Try manual fix:${NC}"
        echo "1. Create a fresh virtual environment:"
        echo "   python3 -m venv fresh_env"
        echo "   source fresh_env/bin/activate"
        echo "2. Install packages:"
        echo "   pip install selenium"
        exit 1
    }
}

echo -e "\n${GREEN}Fix completed!${NC}"
echo -e "${YELLOW}You can now run: python3 agora/headless_agora_streamer.py${NC}" 