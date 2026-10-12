"""Secret management menggunakan Windows Credential Manager (keyring)."""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class SecretManager:
    """Manage secrets using Windows Credential Manager via keyring."""

    def __init__(self, service_name: str = "yuna"):
        self.service_name = service_name
        self._keyring = None
        self._available = False
        self._init_keyring()

    def _init_keyring(self):
        """Initialize keyring backend."""
        try:
            import keyring
            self._keyring = keyring
            self._available = True
            logger.info("Windows Credential Manager (keyring) initialized")
        except ImportError:
            logger.warning("keyring not installed, secrets will not be persisted securely")
            self._available = False
        except Exception as e:
            logger.error(f"Failed to initialize keyring: {e}")
            self._available = False

    def set_secret(self, key: str, value: str) -> bool:
        """
        Store a secret.

        Args:
            key: Secret key/name
            value: Secret value

        Returns:
            True if successful
        """
        if not self._available:
            logger.warning("Keyring not available, cannot store secret")
            return False

        try:
            self._keyring.set_password(self.service_name, key, value)
            logger.debug(f"Secret stored: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to store secret {key}: {e}")
            return False

    def get_secret(self, key: str) -> Optional[str]:
        """
        Retrieve a secret.

        Args:
            key: Secret key/name

        Returns:
            Secret value or None if not found
        """
        if not self._available:
            return None

        try:
            value = self._keyring.get_password(self.service_name, key)
            return value
        except Exception as e:
            logger.error(f"Failed to retrieve secret {key}: {e}")
            return None

    def delete_secret(self, key: str) -> bool:
        """
        Delete a secret.

        Args:
            key: Secret key/name

        Returns:
            True if successful
        """
        if not self._available:
            return False

        try:
            self._keyring.delete_password(self.service_name, key)
            logger.debug(f"Secret deleted: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {key}: {e}")
            return False

    def list_secrets(self) -> list:
        """
        List all stored secret keys.

        Returns:
            List of secret keys
        """
        if not self._available:
            return []

        try:
            # keyring doesn't have a direct list method,
            # but we can use the underlying backend
            return []
        except Exception:
            return []

    def is_available(self) -> bool:
        """Check if keyring is available."""
        return self._available


# Standard secret keys used by Yuna
SECRET_KEYS = {
    "router_api_key": "ROUTER_API_KEY",
    "ha_token": "HA_TOKEN",
    "mikrotik_password": "MIKROTIK_PASSWORD",
    "mqtt_password": "MQTT_PASSWORD",
    "openweather_api_key": "OPENWEATHER_API_KEY",
    "weather_api_key": "WEATHER_API_KEY",
    "porcupine_access_key": "PORCUPINE_ACCESS_KEY",
}


def migrate_env_to_keyring(env_path: str = ".env") -> int:
    """
    Migrate secrets from .env file to Windows Credential Manager.

    Args:
        env_path: Path to .env file

    Returns:
        Number of secrets migrated
    """
    if not os.path.exists(env_path):
        logger.warning(f".env file not found: {env_path}")
        return 0

    manager = SecretManager()
    if not manager.is_available():
        logger.warning("Keyring not available, cannot migrate")
        return 0

    migrated = 0
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"\'')

                if key in SECRET_KEYS.values():
                    secret_key = [k for k, v in SECRET_KEYS.items() if v == key][0]
                    if manager.set_secret(secret_key, value):
                        migrated += 1
                        logger.info(f"Migrated secret: {key}")

    return migrated


def get_secret(key: str, env_fallback: bool = True) -> Optional[str]:
    """
    Get secret from keyring with .env fallback.

    Args:
        key: Secret key (from SECRET_KEYS)
        env_fallback: Fall back to environment variable

    Returns:
        Secret value or None
    """
    manager = SecretManager()

    # Try keyring first
    if manager.is_available():
        value = manager.get_secret(key)
        if value:
            return value

    # Fallback to environment
    if env_fallback:
        env_key = SECRET_KEYS.get(key, key)
        return os.getenv(env_key)

    return None


def set_secret(key: str, value: str) -> bool:
    """Set secret in keyring."""
    manager = SecretManager()
    return manager.set_secret(key, value)


# Global instance
_secret_manager: Optional[SecretManager] = None


def get_secret_manager() -> SecretManager:
    """Get global secret manager."""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager()
    return _secret_manager
