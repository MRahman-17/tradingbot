#!/usr/bin/env python3
"""
Platform Factory for Trading System
Creates and manages trading platform adapters (WebUll, and others as needed).
"""
import os
import logging
from typing import Dict, Optional

# Configure logging
logger = logging.getLogger("Platform Factory")


class PlatformFactory:
    """
    Factory class for creating platform adapters.
    Handles adapter creation, configuration, and caching.
    """

    def __init__(self):
        """Initialize the platform factory"""
        # Keep a cache of created adapters
        self.adapter_cache = {}

        # Load platform configuration from environment
        self.trading_mode = os.environ.get("TRADING_MODE", "paper").lower()

        logger.info(f"Platform factory initialized with trading mode: {self.trading_mode}")

    def create_adapter(self, platform_name: str) -> Optional[object]:
        """
        Create a platform adapter for the specified trading platform

        Args:
            platform_name: Name of the trading platform (e.g., 'webull', 'zoya')

        Returns:
            object: Platform adapter instance or None if platform not supported
        """
        # Normalize platform name
        platform_name = platform_name.lower()

        # Check if adapter is already in cache
        cache_key = f"{platform_name}_{self.trading_mode}"
        if cache_key in self.adapter_cache:
            logger.debug(f"Returning cached {platform_name} adapter")
            return self.adapter_cache[cache_key]

        # Create new adapter based on platform name
        adapter = None

        if platform_name == "webull":
            try:
                # Import the WebUll adapter
                from .webull_adapter import create_webull_adapter

                # Determine paper trading mode
                use_paper_trading = self.trading_mode in ["paper", "test", "sandbox"]

                # Create adapter
                adapter = create_webull_adapter(use_paper_trading=use_paper_trading)

                logger.info(f"Created WebUll adapter in {'paper' if use_paper_trading else 'live'} mode")

            except ImportError:
                logger.error("WebUll adapter module not found")
                return None

            except Exception as e:
                logger.error(f"Error creating WebUll adapter: {str(e)}")
                return None

        elif platform_name == "zoya":
            try:
                # Import the Zoya adapter
                from .zoya_adapter import create_zoya_adapter

                # Create adapter
                adapter = create_zoya_adapter(sandbox_mode=(self.trading_mode != "live"))

                logger.info(f"Created Zoya adapter in {'sandbox' if self.trading_mode != 'live' else 'live'} mode")

            except ImportError:
                logger.error("Zoya adapter module not found")
                return None

            except Exception as e:
                logger.error(f"Error creating Zoya adapter: {str(e)}")
                return None

        elif platform_name == "mock":
            try:
                # Import the mock adapter for testing
                from mock_adapter import create_mock_adapter

                # Create adapter
                adapter = create_mock_adapter()

                logger.info("Created mock adapter")

            except ImportError:
                logger.error("Mock adapter module not found")
                return None

            except Exception as e:
                logger.error(f"Error creating mock adapter: {str(e)}")
                return None

        else:
            logger.error(f"Unsupported platform: {platform_name}")
            return None

        # Cache the adapter
        if adapter is not None:
            self.adapter_cache[cache_key] = adapter

        return adapter

    def get_adapter(self, platform_name: str) -> Optional[object]:
        """
        Get an existing adapter or create a new one if it doesn't exist

        Args:
            platform_name: Name of the trading platform

        Returns:
            object: Platform adapter instance or None if platform not supported
        """
        return self.create_adapter(platform_name)

    def close_all_adapters(self):
        """Close all platform adapters and clear cache"""
        for key, adapter in self.adapter_cache.items():
            try:
                if hasattr(adapter, 'close') and callable(adapter.close):
                    adapter.close()
                    logger.debug(f"Closed adapter: {key}")

            except Exception as e:
                logger.error(f"Error closing adapter {key}: {str(e)}")

        # Clear cache
        self.adapter_cache.clear()
        logger.info("All adapters closed and cache cleared")

    def health_check_all(self) -> Dict[str, Dict]:
        """
        Perform health check on all active adapters

        Returns:
            Dict[str, Dict]: Health status for each platform
        """
        results = {}

        for key, adapter in self.adapter_cache.items():
            try:
                if hasattr(adapter, 'health_check') and callable(adapter.health_check):
                    health = adapter.health_check()
                    results[key] = health
                else:
                    results[key] = {"status": "Unknown", "error": "Adapter does not support health check"}

            except Exception as e:
                results[key] = {"status": "Error", "error": str(e)}

        return results


# Factory instance for global use
_factory_instance = None


def get_factory_instance() -> PlatformFactory:
    """
    Get the global factory instance

    Returns:
        PlatformFactory: Factory instance
    """
    global _factory_instance

    if _factory_instance is None:
        _factory_instance = PlatformFactory()

    return _factory_instance


# Helper function to create an adapter
def create_adapter(platform_name: str) -> Optional[object]:
    """
    Create a platform adapter using the global factory

    Args:
        platform_name: Name of the trading platform

    Returns:
        object: Platform adapter instance or None if platform not supported
    """
    factory = get_factory_instance()
    return factory.create_adapter(platform_name)


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create factory
    factory = PlatformFactory()

    try:
        # Create WebUll adapter
        webull = factory.create_adapter("webull")
        if webull:
            # Perform health check
            health = webull.health_check()
            print(f"WebUll Health: {health['status']}")

        # Create Zoya adapter (if available)
        zoya = factory.create_adapter("zoya")
        if zoya:
            # Perform health check
            health = zoya.health_check()
            print(f"Zoya Health: {health['status']}")

        # Check health of all adapters
        health_status = factory.health_check_all()
        for platform, status in health_status.items():
            print(f"{platform}: {status['status']}")

    finally:
        # Close all adapters
        factory.close_all_adapters()
