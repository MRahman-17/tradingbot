import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for the trading system"""

    DEFAULT_CONFIG = {
        "trading": {
            "enabled": True,
            "symbols": ["AAPL", "MSFT", "NVDA"],
            "max_drawdown": 0.05,
            "kelly_fraction": 0.02,
            "quantity": 1,
            "min_hold_period": 172800,  # 48 hours in seconds
            "sleep_time": 60,
            "halal_compliance": True
        },
        "quantum": {
            "enabled": True,
            "error_threshold": 0.15,  # Maximum acceptable error rate
            "min_confidence": 0.65,  # Minimum confidence to consider quantum signals
            "device": "default.qubit",  # Use simulator by default
            "shots": 1000,  # Number of quantum measurements
            "use_error_mitigation": True,
            "fallback_to_classical": True
        },
        "news": {
            "enabled": True,
            "api_keys": {
                "alpha_vantage": "",
                "news_api": "",
                "finnhub": ""
            },
            "sentiment_weights": {
                "news": 0.5,
                "social": 0.3,
                "fear_greed": 0.2
            },
            "cache_duration": 3600,  # 1 hour cache for API results
            "use_cache": True,
            "news_lookback_days": 3
        },
        "platform": {
            "name": "mock",  # Options: "webull", "robinhood", "alpaca", "custom", "mock"
            "use_paper_trading": True
        },
        "security": {
            "encrypt_credentials": True,
            "key_rotation_days": 30,
            "rate_limiting": {
                "enabled": True,
                "max_requests_per_minute": 60
            }
        },
        "monitoring": {
            "enabled": True,
            "check_interval": 3600,  # 1 hour in seconds
            "alert_emails": []
        },
        "logging": {
            "level": "INFO",
            "log_to_file": True,
            "log_dir": "logs"
        }
    }

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize configuration from file or defaults

        Args:
            config_path: Path to configuration file, if None uses default path
        """
        self.config_dir = Path("config")
        self.config_path = Path(config_path) if config_path else self.config_dir / "config.json"
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_path}")
                return config
            else:
                logger.info(f"No configuration found, creating default at {self.config_path}")
                self._save_default_config()
                return self.DEFAULT_CONFIG
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return self.DEFAULT_CONFIG

    def _save_default_config(self) -> None:
        """Save default configuration to file"""
        try:
            self.config_dir.mkdir(exist_ok=True, parents=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.DEFAULT_CONFIG, f, indent=4)
            logger.info(f"Default configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving default configuration: {e}")

    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """Get configuration value

        Args:
            section: Configuration section
            key: Configuration key within section, if None returns entire section
            default: Default value if section/key not found

        Returns:
            Configuration value or default if not found
        """
        if section not in self.config:
            return default

        if key is None:
            return self.config[section]

        return self.config[section].get(key, default)

    def set(self, section: str, key: str, value: Any) -> None:
        """Set configuration value

        Args:
            section: Configuration section
            key: Configuration key within section
            value: Value to set
        """
        if section not in self.config:
            self.config[section] = {}

        self.config[section][key] = value

    def save(self) -> bool:
        """Save current configuration to file

        Returns:
            True if successful, False otherwise
        """
        try:
            self.config_dir.mkdir(exist_ok=True, parents=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False

    def load_environment_variables(self) -> None:
        """Load sensitive configuration from environment variables"""
        # API Keys from environment
        self.config["news"]["api_keys"]["alpha_vantage"] = os.environ.get("ALPHA_VANTAGE_API_KEY", "")
        self.config["news"]["api_keys"]["news_api"] = os.environ.get("NEWS_API_KEY", "")
        self.config["news"]["api_keys"]["finnhub"] = os.environ.get("FINNHUB_API_KEY", "")

        # Platform credentials - not stored in config, just loaded from environment
        # These will be handled by the platform adapters directly

        logger.info("Loaded configuration from environment variables")