#!/usr/bin/env python3
"""
Basic Chrome/Selenium test script
Tests if Chrome can launch and load a simple page
"""

import sys
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_chrome():
    """Test basic Chrome functionality"""
    logger.info("Starting basic Chrome test...")
    
    # Setup Chrome options
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    # Enable logging
    options.add_argument('--enable-logging=stderr')
    options.add_argument('--v=1')
    
    driver = None
    try:
        # Try to find chromedriver
        import shutil
        chromedriver_path = shutil.which('chromedriver')
        
        logger.info(f"ChromeDriver path: {chromedriver_path}")
        
        # Create service with logging
        if chromedriver_path:
            service = Service(chromedriver_path)
            service.log_path = '/tmp/chromedriver_test.log'
            driver = webdriver.Chrome(service=service, options=options)
        else:
            # Try without explicit path
            driver = webdriver.Chrome(options=options)
            
        logger.info("✓ Chrome driver created successfully!")
        
        # Try to load a simple data URL
        logger.info("Loading test page...")
        test_html = """
        <html>
        <head><title>Test</title></head>
        <body>
            <h1>Chrome Test Successful</h1>
            <p id="status">Page loaded</p>
        </body>
        </html>
        """
        driver.get(f"data:text/html,{test_html}")
        
        # Check if page loaded
        title = driver.title
        logger.info(f"✓ Page title: {title}")
        
        # Try to find element
        status = driver.find_element("id", "status")
        logger.info(f"✓ Found element with text: {status.text}")
        
        # Get browser info
        logger.info(f"Browser name: {driver.capabilities.get('browserName', 'unknown')}")
        logger.info(f"Browser version: {driver.capabilities.get('browserVersion', 'unknown')}")
        
        logger.info("\n✓ SUCCESS: Chrome is working properly!")
        
    except Exception as e:
        logger.error(f"\n✗ FAILED: {str(e)}")
        
        # Print more details
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        
        # Check ChromeDriver log
        try:
            with open('/tmp/chromedriver_test.log', 'r') as f:
                logger.error(f"\nChromeDriver log:\n{f.read()}")
        except:
            pass
            
        logger.error("\nTroubleshooting tips:")
        logger.error("1. Check Chrome and ChromeDriver versions match:")
        logger.error("   chromium --version")
        logger.error("   chromedriver --version")
        logger.error("\n2. Try running Chrome manually:")
        logger.error("   chromium --headless --no-sandbox --disable-gpu --dump-dom https://google.com")
        logger.error("\n3. Install missing dependencies:")
        logger.error("   sudo apt-get update")
        logger.error("   sudo apt-get install -y chromium-driver chromium-browser")
        logger.error("   sudo apt-get install -y libnss3 libgconf-2-4 libxss1 libasound2")
        
        return False
        
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Driver closed cleanly")
            except:
                pass
                
    return True

if __name__ == "__main__":
    success = test_chrome()
    sys.exit(0 if success else 1) 