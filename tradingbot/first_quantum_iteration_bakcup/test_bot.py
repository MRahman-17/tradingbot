#!/usr/bin/env python3
"""
Simple test script with proper indentation
"""
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Test Bot")


# A simple class with proper indentation
class TestClass:
    def __init__(self):
        self.value = 42
        logger.info("TestClass initialized")

    def get_value(self):
        return self.value


# A function at module level (same indentation as class)
def test_function():
    logger.info("Test function called")
    test_obj = TestClass()
    logger.info(f"Test object value: {test_obj.get_value()}")
    return True


# Main block at module level
if __name__ == "__main__":
    logger.info("========== TEST SCRIPT STARTED ==========")
    try:
        logger.info("About to call test function")
        result = test_function()
        logger.info(f"Test function returned: {result}")
    except Exception as e:
        logger.error(f"Error in test: {e}", exc_info=True)
    logger.info("========== TEST SCRIPT FINISHED ==========")
