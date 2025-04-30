import os
import base64
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class Security:
    """Security functionality for the trading system"""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize security with configuration

        Args:
            config: Security configuration section
        """
        self.config = config
        self.security_dir = Path("security/keys")
        self.security_dir.mkdir(exist_ok=True, parents=True)
        self.key_path = self.security_dir / "key.bin"
        self.salt_path = self.security_dir / "salt.bin"
        self.metadata_path = self.security_dir / "metadata.json"

        # Rate limiting
        self.rate_limits: Dict[str, Dict[str, Any]] = {}

        # Initialize encryption
        self.cipher = self._initialize_encryption()

    def _initialize_encryption(self) -> Optional[Fernet]:
        """Initialize encryption, rotating keys if needed

        Returns:
            Fernet cipher or None if initialization fails
        """
        try:
            # Check if we need to generate new keys
            if self._should_rotate_keys():
                logger.info("Generating new encryption keys")
                return self._generate_new_keys()

            # Load existing keys
            if self.key_path.exists() and self.salt_path.exists():
                with open(self.key_path, 'rb') as f:
                    key = f.read()
                logger.info("Encryption key loaded")
                return Fernet(key)
            else:
                logger.info("No encryption keys found, generating new ones")
                return self._generate_new_keys()
        except Exception as e:
            logger.error(f"Error initializing encryption: {e}")
            return None

    def _should_rotate_keys(self) -> bool:
        """Check if encryption keys should be rotated

        Returns:
            True if keys should be rotated, False otherwise
        """
        if not self.metadata_path.exists():
            return True

        try:
            import json
            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f)

            created_date = datetime.fromisoformat(metadata.get('created_at', '2000-01-01T00:00:00'))
            rotation_days = self.config.get('key_rotation_days', 30)

            # Check if keys are older than rotation period
            return datetime.now() - created_date > timedelta(days=rotation_days)
        except Exception as e:
            logger.error(f"Error checking key rotation: {e}")
            return True

    def _generate_new_keys(self) -> Fernet:
        """Generate new encryption keys

        Returns:
            Fernet cipher
        """
        import json

        # Generate new key and salt
        password = os.urandom(32)
        salt = os.urandom(16)

        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))

        # Save key and salt
        with open(self.key_path, 'wb') as f:
            f.write(key)
        with open(self.salt_path, 'wb') as f:
            f.write(salt)

        # Set secure permissions
        os.chmod(self.key_path, 0o600)  # Read/write for owner only
        os.chmod(self.salt_path, 0o600)  # Read/write for owner only

        # Save metadata
        with open(self.metadata_path, 'w') as f:
            json.dump({
                'created_at': datetime.now().isoformat(),
                'rotation_days': self.config.get('key_rotation_days', 30)
            }, f, indent=4)

        logger.info("New encryption keys generated and saved")
        return Fernet(key)

    def encrypt(self, data: str) -> Optional[str]:
        """Encrypt data

        Args:
            data: Data to encrypt

        Returns:
            Base64-encoded encrypted data or None if encryption fails
        """
        if not self.cipher:
            logger.error("Encryption not initialized")
            return None

        try:
            encrypted = self.cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            return None

    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """Decrypt data

        Args:
            encrypted_data: Base64-encoded encrypted data

        Returns:
            Decrypted data or None if decryption fails
        """
        if not self.cipher:
            logger.error("Encryption not initialized")
            return None

        try:
            encrypted = base64.urlsafe_b64decode(encrypted_data)
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            return None

    def check_rate_limit(self, resource: str, limit: int = None) -> bool:
        """Check if a resource has exceeded its rate limit

        Args:
            resource: Resource identifier (e.g., 'api.webull.com')
            limit: Maximum requests per minute, overrides config if provided

        Returns:
            True if within rate limit, False if exceeded
        """
        if not self.config.get('rate_limiting', {}).get('enabled', True):
            return True

        now = time.time()

        # Initialize resource tracking if not exists
        if resource not in self.rate_limits:
            self.rate_limits[resource] = {
                'requests': [],
                'last_reset': now
            }

        # Get max requests per minute
        if limit is None:
            limit = self.config.get('rate_limiting', {}).get('max_requests_per_minute', 60)

        # Clean up old requests (older than 1 minute)
        self.rate_limits[resource]['requests'] = [
            req_time for req_time in self.rate_limits[resource]['requests']
            if now - req_time < 60
        ]

        # Check if limit exceeded
        if len(self.rate_limits[resource]['requests']) >= limit:
            logger.warning(f"Rate limit exceeded for {resource}")
            return False

        # Add new request
        self.rate_limits[resource]['requests'].append(now)
        return True
