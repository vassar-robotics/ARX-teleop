#!/usr/bin/env python3
"""
Diagnostic script for Chrome/Chromium and ChromeDriver installation
Helps troubleshoot Selenium WebDriver issues
"""

import os
import subprocess
import sys
import shutil

def check_command(cmd):
    """Check if a command exists and get its version"""
    try:
        path = shutil.which(cmd)
        if path:
            print(f"✓ Found {cmd} at: {path}")
            # Try to get version
            try:
                result = subprocess.run([cmd, '--version'], capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  Version: {result.stdout.strip()}")
                return True
            except:
                return True
        else:
            print(f"✗ {cmd} not found in PATH")
            return False
    except Exception as e:
        print(f"✗ Error checking {cmd}: {e}")
        return False

def check_file(path, name):
    """Check if a file exists at a specific path"""
    if os.path.exists(path):
        print(f"✓ Found {name} at: {path}")
        # Try to check if executable
        if os.access(path, os.X_OK):
            print(f"  Executable: Yes")
        else:
            print(f"  Executable: No (may need chmod +x)")
        return True
    return False

def check_package(package):
    """Check if a package is installed via dpkg"""
    try:
        result = subprocess.run(['dpkg', '-l', package], capture_output=True, text=True)
        if result.returncode == 0 and package in result.stdout:
            print(f"✓ Package {package} is installed")
            # Get version
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if package in line and line.startswith('ii'):
                    parts = line.split()
                    if len(parts) >= 3:
                        print(f"  Version: {parts[2]}")
            return True
        else:
            print(f"✗ Package {package} is not installed")
            return False
    except:
        return False

def main():
    print("Chrome/Chromium and ChromeDriver Diagnostic Tool")
    print("=" * 50)
    
    # Check Chrome/Chromium browsers
    print("\n1. Checking Chrome/Chromium browsers:")
    chrome_found = False
    for browser in ['chromium-browser', 'chromium', 'google-chrome', 'google-chrome-stable']:
        if check_command(browser):
            chrome_found = True
    
    # Check common Chrome paths
    print("\n2. Checking common Chrome binary paths:")
    chrome_paths = [
        '/usr/bin/chromium-browser',
        '/usr/bin/chromium',
        '/usr/bin/google-chrome',
        '/usr/lib/chromium-browser/chromium-browser',
        '/usr/lib/chromium/chromium',
        '/snap/bin/chromium'
    ]
    for path in chrome_paths:
        if check_file(path, "Chrome/Chromium"):
            chrome_found = True
    
    # Check ChromeDriver
    print("\n3. Checking ChromeDriver:")
    driver_found = False
    if check_command('chromedriver'):
        driver_found = True
    
    # Check common ChromeDriver paths
    print("\n4. Checking common ChromeDriver paths:")
    driver_paths = [
        '/usr/bin/chromedriver',
        '/usr/local/bin/chromedriver',
        '/usr/lib/chromium-browser/chromedriver',
        '/usr/lib/chromium/chromedriver',
        '/usr/lib/aarch64-linux-gnu/chromium-browser/chromedriver',
        '/snap/bin/chromium.chromedriver'
    ]
    for path in driver_paths:
        if check_file(path, "ChromeDriver"):
            driver_found = True
    
    # Check installed packages
    print("\n5. Checking installed packages:")
    check_package('chromium')
    check_package('chromium-browser')
    check_package('chromium-driver')
    check_package('chromium-chromedriver')
    
    # Check Python packages
    print("\n6. Checking Python packages:")
    try:
        import selenium
        print(f"✓ Selenium is installed: {selenium.__version__}")
    except ImportError:
        print("✗ Selenium is not installed")
    
    # Summary and recommendations
    print("\n" + "=" * 50)
    print("SUMMARY:")
    
    if not chrome_found:
        print("\n✗ Chrome/Chromium browser not found!")
        print("  Install with: sudo apt-get install chromium")
    else:
        print("\n✓ Chrome/Chromium browser found")
    
    if not driver_found:
        print("\n✗ ChromeDriver not found!")
        print("  Install with: sudo apt-get install chromium-driver")
    else:
        print("\n✓ ChromeDriver found")
    
    # Test Selenium
    if chrome_found and driver_found:
        print("\n7. Testing Selenium WebDriver:")
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Try to create driver
            driver = webdriver.Chrome(options=options)
            print("✓ Successfully created Chrome WebDriver!")
            driver.quit()
        except Exception as e:
            print(f"✗ Failed to create WebDriver: {e}")
            print("\nPossible issues:")
            print("- ChromeDriver version doesn't match Chrome version")
            print("- Missing permissions or dependencies")
            print("- Try running with sudo if permission denied")
    
    # Architecture check
    print("\n8. System architecture:")
    try:
        import platform
        print(f"  Machine: {platform.machine()}")
        print(f"  System: {platform.system()}")
        print(f"  Release: {platform.release()}")
    except:
        pass

if __name__ == "__main__":
    main() 