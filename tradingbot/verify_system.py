#!/usr/bin/env python3
"""
Verification script to check if all dependencies and authentication are working
"""
import os
import sys
import importlib
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Verification")


def check_dependencies():
    """Check if all required packages are installed"""
    required_packages = [
        "numpy", "pandas", "webull-api", "robin_stocks", "qiskit", "scikit-learn",
        "matplotlib", "cryptography", "requests", "schedule", "joblib"
    ]

    missing = []
    for pkg in required_packages:
        try:
            pkg_name = pkg.replace("-", "_")
            importlib.import_module(pkg_name)
            logger.info(f"✓ {pkg} is installed")
        except ImportError:
            missing.append(pkg)
            logger.error(f"✗ {pkg} is missing")

    return len(missing) == 0


def check_environment():
    """Verify that all required directories and files exist"""
    required_dirs = [
        "logs", "models", "data", "config", "platform_adapters",
        "security/encryption", "legal/compliance_reports"
    ]

    required_files = [
        "config/config.json",
        "platform_adapters/__init__.py",
        "platform_adapters/platform_factory.py"
    ]

    for directory in required_dirs:
        if not os.path.exists(directory):
            logger.warning(f"Creating missing directory: {directory}")
            os.makedirs(directory, exist_ok=True)

    for file_path in required_files:
        if not os.path.exists(file_path):
            logger.error(f"Required file missing: {file_path}")
            return False

    return True


def check_authentication():
    """Test authentication with trading platforms"""
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    try:
        from platform_adapters.platform_factory import PlatformFactory
        factory = PlatformFactory()

        config_path = "config/config.json"
        if not os.path.exists(config_path):
            logger.error("Config file not found")
            return False

        import json
        with open(config_path, 'r') as f:
            config = json.load(f)

        platform_name = config.get('platform', {}).get('name', 'webull')
        adapter = factory.create_adapter(platform_name)

        if adapter is None:
            logger.error(f"Failed to create adapter for {platform_name}")
            return False

        logger.info(f"Testing login to {platform_name}...")
        if hasattr(adapter, 'login') and callable(adapter.login):
            result = adapter.login()
            if result:
                logger.info(f"✓ Successfully authenticated with {platform_name}")
                return True
            else:
                logger.error(f"✗ Authentication failed with {platform_name}")
                return False
        else:
            logger.error(f"Adapter for {platform_name} doesn't have a login method")
            return False
    except Exception as e:
        logger.error(f"Error checking authentication: {e}")
        return False


if __name__ == "__main__":
    print("=== Environment Check ===")
    env_ok = check_environment()

    print("\n=== Dependency Check ===")
    deps_ok = check_dependencies()

    print("\n=== Authentication Check ===")
    auth_ok = check_authentication()

    if env_ok and deps_ok and auth_ok:
        print("\n✓ All checks passed. System should be able to run.")
    else:
        print("\n✗ Some checks failed. Please fix the issues before running the system.")
