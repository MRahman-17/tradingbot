#!/usr/bin/env python3
import os
import sys
import time
import logging
import threading
import json
import signal
import argparse
from datetime import datetime, timedelta
import requests

# Define current directory as part of Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/trading_system_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Trading System")

# Create required directories
os.makedirs("models", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("config", exist_ok=True)
os.makedirs("platform_adapters", exist_ok=True)
os.makedirs("security/encryption", exist_ok=True)

# Create __init__.py if it doesn't exist
if not os.path.exists("platform_adapters/__init__.py"):
    with open("platform_adapters/__init__.py", "w") as f:
        f.write("# Module initialization\n")

# Default configuration
DEFAULT_CONFIG = {
    "trading_bot": {
        "enabled": True,
        "symbols": ["AAPL"],
        "max_drawdown": 0.05,
        "kelly_fraction": 0.02,
        "quantity": 1,
        "min_hold_period": 86400,  # 48 hours in seconds
        "sleep_time": 60,
        "halal_compliance": True
    },
    "monitor_bot": {
        "enabled": True,
        "check_interval": 3600,  # 1 hour in seconds
        "quantum_optimizer_interval": 259200,  # 3 days in seconds
        "legal_check_interval": 604800,  # 7 days in seconds
        "api_check_interval": 86400  # 1 day in seconds
    },
    "improvement_bot": {
        "enabled": True,
        "check_interval": 3600,  # 1 hour in seconds
        "debug_scan_interval": 21600,  # 6 hours in seconds
        "ml_update_interval": 604800,  # 7 days in seconds
        "quantum_optimization_interval": 1209600,  # 14 days in seconds
        "encryption_update_interval": 2592000,  # 30 days in seconds
        "legal_compliance_interval": 604800,  # 7 days in seconds
        "backup_interval": 86400  # 1 day in seconds
    },
    "platform": {
        "name": "mock",  # Options: "webull", "robinhood", "alpaca", "custom", "mock"
        "use_paper_trading": True
    }
}


def check_dependencies():
    """Check if all required packages are installed"""
    required_packages = [
        "numpy", "pandas", "matplotlib", "cryptography", "requests", "schedule", "joblib"
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)

    # Special check for scikit-learn
    try:
        import sklearn
        logger.info(f"scikit-learn is available (version {sklearn.__version__})")
    except ImportError:
        missing_packages.append("scikit-learn")

    if missing_packages:
        logger.error(f"Missing required packages: {', '.join(missing_packages)}")
        logger.info("Please install missing packages with: pip install " + " ".join(missing_packages))
        return False

    return True


def load_or_create_config(config_path="config/config.json"):
    """Load or create configuration file"""
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as file:
                config = json.load(file)
                logger.info("Configuration loaded successfully")
                return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            logger.info("Using default configuration")
            return DEFAULT_CONFIG
    else:
        logger.info("No configuration found, creating default")
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as file:
                json.dump(DEFAULT_CONFIG, file, indent=4)
            return DEFAULT_CONFIG
        except Exception as e:
            logger.error(f"Error creating configuration: {e}")
            return DEFAULT_CONFIG


def load_environment_variables():
    # Initialize platform adapters with the new factory
    try:
        from platform_adapters.platform_factory import get_factory_instance
        platform_factory = get_factory_instance()
        logger.info("Initialized platform factory with new adapters")
    except Exception as e:
        logger.error(f"Error initializing platform factory: {e}")
    """Load environment variables from secrets.env file"""
    if os.path.exists("config/secrets.env"):
        with open("config/secrets.env", "r") as file:
            for line in file:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value
        logger.info("Environment variables loaded")
    else:
        logger.warning("No secrets.env file found. Please create it with your API credentials.")
        logger.info("Creating template secrets.env file...")
        with open("config/secrets.env", "w") as file:
            file.write("# WebUll Credentials\n")
            file.write("WEBULL_USERNAME=your_username\n")
            file.write("WEBULL_PASSWORD=your_password\n")
            file.write("WEBULL_DEVICE_ID=your_device_id\n")
            file.write("WEBULL_TRADE_PIN=your_trade_pin\n\n")
            file.write("# Robinhood Credentials (if needed)\n")
            file.write("ROBINHOOD_USERNAME=your_username\n")
            file.write("ROBINHOOD_PASSWORD=your_password\n\n")
            file.write("# Zoya API Key for Halal Compliance\n")
            file.write("ZOYA_API_KEY=your_zoya_api_key\n\n")
            file.write("# Set this to 'paper' for paper trading or 'live' for live trading\n")
            file.write("TRADING_MODE=paper\n")
        logger.info("Template created at config/secrets.env - please edit with your credentials")
        return False
    return True


def setup_encryption():
    """Set up encryption for sensitive data"""
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    import base64

    key_path = "security/encryption/key.bin"
    salt_path = "security/encryption/salt.bin"

    if os.path.exists(key_path) and os.path.exists(salt_path):
        # Load existing key and salt
        with open(key_path, 'rb') as f:
            key = f.read()
        logger.info("Encryption key loaded")
        return Fernet(key)
    else:
        # Generate new encryption key and salt
        logger.info("Generating new encryption keys")
        password = os.urandom(32)
        salt = os.urandom(16)

        # Derive a key from the password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))

        # Save key and salt
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        with open(key_path, 'wb') as f:
            f.write(key)
        with open(salt_path, 'wb') as f:
            f.write(salt)

        # Set secure permissions
        os.chmod(key_path, 0o600)  # Read/write for owner only
        os.chmod(salt_path, 0o600)  # Read/write for owner only

        logger.info("New encryption keys generated and saved")
        return Fernet(key)


def create_platform_factory():
    """Create the platform factory if it doesn't exist"""
    factory_path = os.path.join(current_dir, "platform_adapters", "platform_factory.py")
    webull_adapter_path = os.path.join(current_dir, "platform_adapters", "webull_adapter.py")
    zoya_adapter_path = os.path.join(current_dir, "platform_adapters", "zoya_adapter.py")

    # Create factory file with updated code if it doesn't exist
    if not os.path.exists(factory_path):
        try:
            # Copy the content from the provided platform_factory.py
            with open(factory_path, 'w') as f:
                f.write(open(os.path.join(current_dir, "platform_factory.py")).read())
            logger.info("Platform factory created successfully")
        except Exception as e:
            logger.error(f"Error creating platform factory: {e}")
            return False

    # Create WebUll adapter if it doesn't exist
    if not os.path.exists(webull_adapter_path):
        try:
            # Copy the content from the provided webull_adapter.py
            with open(webull_adapter_path, 'w') as f:
                f.write(open(os.path.join(current_dir, "webull_adapter.py")).read())
            logger.info("WebUll adapter created successfully")
        except Exception as e:
            logger.error(f"Error creating WebUll adapter: {e}")

    # Create Zoya adapter if it doesn't exist
    if not os.path.exists(zoya_adapter_path):
        try:
            # Copy the content from the provided zoya_adapter.py
            with open(zoya_adapter_path, 'w') as f:
                f.write(open(os.path.join(current_dir, "zoya_adapter.py")).read())
            logger.info("Zoya adapter created successfully")
        except Exception as e:
            logger.error(f"Error creating Zoya adapter: {e}")

    return True


def fix_improvement_bot():
    """Fix the syntax error in the improvement bot"""
    improvement_bot_path = os.path.join(current_dir, "improvement_bot.py")
    try:
        with open(improvement_bot_path, 'r') as f:
            code = f.read()

        # Fix the indentation issue
        fixed_code = code.replace(
            "# Main loop\n     while True:",
            "# Main loop\n    while True:"
        )

        with open(improvement_bot_path, 'w') as f:
            f.write(fixed_code)

        logger.info("Fixed syntax error in improvement_bot.py")
        return True
    except Exception as e:
        logger.error(f"Error fixing improvement_bot.py: {e}")
        return False


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


def safe_import(module_name):
    """Safely import a module with error handling"""
    try:
        return __import__(module_name)
    except Exception as e:
        logger.error(f"Error importing {module_name}: {e}")
        return None


def main():
    """Main function to initialize and run the trading system"""
    # Load configuration and environment variables
    config = load_or_create_config()
    load_environment_variables()

    # Set up encryption
    cipher = setup_encryption()

    # Make sure platform factory exists
    create_platform_factory()

    # Fix the improvement bot syntax if needed
    fix_improvement_bot()

    # Check dependencies
    if not check_dependencies():
        logger.error("Missing required dependencies. Exiting.")
        sys.exit(1)

    # Import the bot modules
    sys.path.append(current_dir)
    trading_bot = safe_import("trading_bot")
    monitor_bot = safe_import("monitor_bot")
    improvement_bot = safe_import("improvement_bot")

    # Check if all modules were imported successfully
    if not all([trading_bot, monitor_bot, improvement_bot]):
        logger.error("Failed to import one or more bot modules. Exiting.")
        sys.exit(1)

    # Start the bot threads
    threads = []

    # Trading Bot thread
    if config.get("trading_bot", {}).get("enabled", True):
        trading_thread = threading.Thread(
            target=trading_bot.trading_loop,
            name="Trading Bot",
            daemon=False
        )
        trading_thread.start()
        threads.append(trading_thread)
        logger.info("Started Trading Bot")

    # Monitor Bot thread
    if config.get("monitor_bot", {}).get("enabled", True):
        monitor_thread = threading.Thread(
            target=monitor_bot.monitor_loop,
            name="Monitor Bot",
            daemon=False
        )
        monitor_thread.start()
        threads.append(monitor_thread)
        logger.info("Started Monitor Bot")

    # Improvement Bot thread
    if config.get("improvement_bot", {}).get("enabled", True):
        improvement_thread = threading.Thread(
            target=improvement_bot.improvement_loop,
            name="Improvement Bot",
            daemon=False
        )
        improvement_thread.start()
        threads.append(improvement_thread)
        logger.info("Started Improvement Bot")

    # Thread for status checking
    status_thread = threading.Thread(
        target=lambda: check_thread_status(threads),
        name="Status Thread",
        daemon=True
    )
    status_thread.start()

    # Keep the main process running and properly handle shutdown
    try:
        logger.info("All bots started. Press Ctrl+C to exit.")

        # Join threads with timeout to allow keyboard interrupt
        while all(thread.is_alive() for thread in threads):
            for thread in threads:
                thread.join(timeout=1.0)

    except KeyboardInterrupt:
        logger.info("Main process interrupted, shutting down...")

    logger.info("Trading system shutdown complete")


if __name__ == "__main__":
    main()
