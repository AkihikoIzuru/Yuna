"""Path jail - restrict file operations to safe directory."""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PathJail:
    """Restrict file/shell operations to a safe directory."""

    def __init__(self, jail_root: Optional[Path] = None):
        """
        Initialize path jail.

        Args:
            jail_root: Root directory for allowed operations.
                       Defaults to %APPDATA%/Yuna/home/
        """
        if jail_root is None:
            appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
            self.jail_root = Path(appdata) / "Yuna" / "home"
        else:
            self.jail_root = Path(jail_root).resolve()

        # Create jail directory if it doesn't exist
        self.jail_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"Path jail initialized at: {self.jail_root}")

    def is_allowed(self, path: Path) -> bool:
        """
        Check if a path is within the jail.

        Args:
            path: Path to check

        Returns:
            True if path is within jail_root
        """
        try:
            resolved = path.resolve()
            return resolved.is_relative_to(self.jail_root)
        except Exception:
            return False

    def resolve_safe(self, path: str) -> Path:
        """
        Resolve a path safely within the jail.

        Args:
            path: Relative path (can include subdirectories)

        Returns:
            Resolved path within jail

        Raises:
            ValueError: If path tries to escape jail
        """
        # Normalize the path
        safe_path = (self.jail_root / path).resolve()

        if not safe_path.is_relative_to(self.jail_root):
            raise ValueError(f"Path '{path}' attempts to escape jail")

        return safe_path

    def create_subdir(self, subdir: str) -> Path:
        """Create a subdirectory within the jail."""
        safe_path = self.resolve_safe(subdir)
        safe_path.mkdir(parents=True, exist_ok=True)
        return safe_path

    def get_jail_root(self) -> Path:
        """Get the jail root directory."""
        return self.jail_root


# Global instance
_jail: Optional[PathJail] = None


def get_path_jail(jail_root: Optional[Path] = None) -> PathJail:
    """Get global path jail instance."""
    global _jail
    if _jail is None:
        _jail = PathJail(jail_root)
    return _jail


def reset_path_jail():
    """Reset global path jail (for testing)."""
    global _jail
    _jail = None