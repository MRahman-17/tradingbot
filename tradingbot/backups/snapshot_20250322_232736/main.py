#!/usr/bin/env python3
"""
Main script for initializing and running the trading system components
"""
import os
import sys
import time
import logging
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Trading System")

# Create required directories
os.makedirs("logs", exist_ok=True)
os.makedirs("models", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("config", exist_ok=True)
os.makedirs("platform_adapters", exist_ok=True)


def import_with_fallback(module_name):
    """Import a module with fallback to minimal version if errors occur"""
    try:
        return __import__(module_name)
    except (SyntaxError, ImportError) as e:
        logger.error(f"Error importing {module_name}: {e}")
        return None


# Import modules with error handling
trading_bot = import_with_fallback("trading_bot")
monitor_bot = import_with_fallback("monitor_bot")
improvement_bot = import_with_fallback("improvement_bot")


def create_minimal_module(module_name):
    """Create a minimal version of a module if it doesn't exist or has errors"""
    if module_name == "trading_bot":
        with open("trading_bot.py", "w") as f:
            f.write("""#!/usr/bin/env python3
def trading_loop():
    print("Trading loop started (minimal version)")
    return
""")
    elif module_name == "monitor_bot":
        with open("monitor_bot.py", "w") as f:
            f.write("""#!/usr/bin/env python3
def monitor_loop():
    print("Monitor loop started (minimal version)")
    return
""")
    elif module_name == "improvement_bot":
        with open("improvement_bot.py", "w") as f:
            f.write("""#!/usr/bin/env python3
def improvement_loop():
    print("Improvement loop started (minimal version)")
    return
""")

    # Try to import the newly created module
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    return __import__(module_name)


# If any module failed to import, create minimal versions
if trading_bot is None:
    trading_bot = create_minimal_module("trading_bot")
if monitor_bot is None:
    monitor_bot = create_minimal_module("monitor_bot")
if improvement_bot is None:
    improvement_bot = create_minimal_module("improvement_bot")


def run_bot_in_thread(bot_module, loop_function_name, thread_name):
    """Run a bot in a separate thread"""
    if bot_module is None:
        logger.error(f"Cannot start {thread_name} - module not available")
        return None

    # Get the loop function
    loop_function = getattr(bot_module, loop_function_name, None)
    if loop_function is None:
        logger.error(f"Loop function {loop_function_name} not found in {bot_module.__name__}")
        return None

    # Create and start thread
    thread = threading.Thread(target=loop_function, name=thread_name, daemon=False)
    thread.start()
    logger.info(f"Started {thread_name}")
    return thread


def check_thread_status(threads):
    """Check if threads are still running and log their status"""
    while all(thread.is_alive() for thread in threads):
        for thread in threads:
            logger.info(f"{thread.name} is alive: {thread.is_alive()}")
        time.sleep(60)  # Check every minute

    # If we get here, at least one thread has died
    for thread in threads:
        if not thread.is_alive():
            logger.error(f"{thread.name} has exited unexpectedly")


def main():
    """Main function to start all components"""
    logger.info("Starting trading system...")

    # Start bot threads
    threads = []

    trading_thread = run_bot_in_thread(trading_bot, "trading_loop", "Trading Bot")
    if trading_thread:
        threads.append(trading_thread)

    monitor_thread = run_bot_in_thread(monitor_bot, "monitor_loop", "Monitor Bot")
    if monitor_thread:
        threads.append(monitor_thread)

    improvement_thread = run_bot_in_thread(improvement_bot, "improvement_loop", "Improvement Bot")
    if improvement_thread:
        threads.append(improvement_thread)

    if not threads:
        logger.error("No bot threads started successfully. Exiting.")
        return

    # Monitor thread status
    try:
        check_thread_status(threads)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")

    logger.info("Trading system shutdown complete")


if __name__ == "__main__":
    main()
