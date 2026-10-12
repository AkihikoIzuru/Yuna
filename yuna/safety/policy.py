"""Safety & Confirmation Policy untuk Yuna.

Mengelola risk level per tool, audit log, shell/file allowlist,
dan proteksi prompt injection.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from yuna.config import get_config

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk level untuk tool."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ToolPolicy:
    """Policy untuk satu tool."""
    name: str
    risk: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    confirmation_message: str = ""
    allowed_args: Optional[Dict[str, Any]] = None  # untuk validasi argumen
    description: str = ""


@dataclass
class AuditEntry:
    """Entry audit log."""
    timestamp: str
    tool_name: str
    args: Dict[str, Any]
    result: str
    risk_level: RiskLevel
    user_confirmed: bool = False
    error: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps({
            "timestamp": self.timestamp,
            "tool_name": self.tool_name,
            "args": self.args,
            "result": self.result,
            "risk_level": self.risk_level.value,
            "user_confirmed": self.user_confirmed,
            "error": self.error,
        }, ensure_ascii=False)


class SafetyPolicy:
    """Kelola policy keamanan untuk tools."""

    def __init__(self):
        self._policies: Dict[str, ToolPolicy] = {}
        self._audit_log_path: Optional[Path] = None
        self._shell_allowlist: Set[str] = set()
        self._file_allowlist: Set[Path] = set()
        self._initialize_default_policies()
        self._setup_audit_log()

    def _initialize_default_policies(self):
        """Inisialisasi policy default untuk tools yang ada."""
        # Low risk - langsung jalan
        low_risk_tools = [
            "get_time", "get_date", "get_system_info",
            "list_timers", "search_conversation", "recall_fact", "list_facts",
            "get_ha_system_status", "get_ha_entity", "get_mikrotik_status",
            "get_mikrotik_wifi_clients", "get_mikrotik_interface_stats",
            "get_mikrotik_dhcp_leases", "get_alerts", "list_reminders",
        ]

        # Medium risk - informasi aksi, jalan kalau tidak dibatalkan
        medium_risk_tools = [
            "open_app", "set_volume", "set_timer", "clear_timers",
            "ha_turn_on_light", "ha_turn_off_light", "ha_toggle_light",
            "ha_set_temperature", "remember_fact", "forget_fact",
            "add_reminder", "delete_reminder", "trigger_alert",
        ]

        # High risk - butuh konfirmasi eksplisit "ya, lanjutkan"
        high_risk_tools = [
            "acknowledge_alert",  # mengubah state alert
        ]

        for name in low_risk_tools:
            self.register_policy(ToolPolicy(name=name, risk=RiskLevel.LOW))

        for name in medium_risk_tools:
            self.register_policy(ToolPolicy(
                name=name,
                risk=RiskLevel.MEDIUM,
                requires_confirmation=True,
                confirmation_message=f"Mau {name.replace('_', ' ')}? Bilang 'ya' kalau iya."
            ))

        for name in high_risk_tools:
            self.register_policy(ToolPolicy(
                name=name,
                risk=RiskLevel.HIGH,
                requires_confirmation=True,
                confirmation_message=(
                    f"PERINGATAN: {name.replace('_', ' ')} adalah aksi berisiko. "
                    "Yakin mau lanjut? Bilang 'ya, lanjutkan' kalau iya."
                )
            ))

    def _setup_audit_log(self):
        """Setup audit log file."""
        config = get_config()
        # Default ke folder data di project root
        data_dir = Path.cwd() / "data"
        data_dir.mkdir(exist_ok=True)
        self._audit_log_path = data_dir / "audit.log"
        logger.info(f"Audit log: {self._audit_log_path}")

    def register_policy(self, policy: ToolPolicy):
        """Daftarkan policy untuk tool."""
        self._policies[policy.name] = policy
        logger.debug(f"Registered policy: {policy.name} -> {policy.risk.value}")

    def get_policy(self, tool_name: str) -> ToolPolicy:
        """Dapatkan policy untuk tool (default LOW jika tidak ada)."""
        return self._policies.get(tool_name, ToolPolicy(name=tool_name, risk=RiskLevel.LOW))

    def get_risk_level(self, tool_name: str) -> RiskLevel:
        """Dapatkan risk level tool."""
        return self.get_policy(tool_name).risk

    def requires_confirmation(self, tool_name: str) -> bool:
        """Cek apakah tool butuh konfirmasi."""
        return self.get_policy(tool_name).requires_confirmation

    def get_confirmation_message(self, tool_name: str) -> str:
        """Dapatkan pesan konfirmasi untuk tool."""
        return self.get_policy(tool_name).confirmation_message

    def should_execute(self, tool_name: str, user_input: str = "") -> tuple[bool, str]:
        """
        Cek apakah tool boleh dijalankan.

        Returns:
            (bool, message): (True, "") jika boleh jalan, (False, pesan) jika tidak
        """
        policy = self.get_policy(tool_name)

        if policy.risk == RiskLevel.LOW:
            return True, ""

        # Medium/High: butuh konfirmasi
        if policy.requires_confirmation:
            # Cek apakah user sudah konfirmasi di input
            user_lower = user_input.lower().strip()

            if policy.risk == RiskLevel.HIGH:
                # High risk: butuh "ya, lanjutkan" eksplisit
                if "ya, lanjutkan" in user_lower or "ya lanjutkan" in user_lower:
                    return True, ""
                return False, policy.confirmation_message
            else:
                # Medium risk: "ya" atau "oke" cukup
                if user_lower in ("ya", "oke", "ok", "lanjut", "ya lanjut", "gas"):
                    return True, ""
                return False, policy.confirmation_message

        return True, ""

    def log_audit(self, entry: AuditEntry):
        """Tulis entry ke audit log."""
        if self._audit_log_path:
            try:
                with open(self._audit_log_path, "a", encoding="utf-8") as f:
                    f.write(entry.to_json() + "\n")
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")

    def create_audit_entry(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        risk_level: RiskLevel,
        user_confirmed: bool = False,
        error: Optional[str] = None,
    ) -> AuditEntry:
        """Buat audit entry dari pemanggilan tool."""
        # Mask sensitive args
        masked_args = self._mask_sensitive_args(args)

        return AuditEntry(
            timestamp=datetime.now().isoformat(),
            tool_name=tool_name,
            args=masked_args,
            result=str(result)[:500],  # limit panjang
            risk_level=risk_level,
            user_confirmed=user_confirmed,
            error=error,
        )

    def _mask_sensitive_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Mask argumen sensitif (password, token, API key)."""
        sensitive_keys = {"password", "token", "api_key", "apikey", "secret", "key", "pass"}
        masked = {}
        for k, v in args.items():
            if any(s in k.lower() for s in sensitive_keys):
                masked[k] = "***MASKED***"
            else:
                masked[k] = v
        return masked

    # ========== Shell/File Allowlist ==========

    def add_shell_allowlist(self, command: str):
        """Tambahkan command ke shell allowlist."""
        self._shell_allowlist.add(command)
        logger.info(f"Added to shell allowlist: {command}")

    def is_shell_allowed(self, command: str) -> bool:
        """Cek apakah command diizinkan."""
        return command in self._shell_allowlist

    def add_file_allowlist(self, path: Path):
        """Tambahkan path ke file allowlist."""
        self._file_allowlist.add(path.resolve())
        logger.info(f"Added to file allowlist: {path}")

    def is_file_allowed(self, path: Path) -> bool:
        """Cek apakah path diizinkan untuk akses file."""
        try:
            resolved = path.resolve()
            return any(resolved.is_relative_to(allowed) for allowed in self._file_allowlist)
        except Exception:
            return False

    # ========== Prompt Injection Protection ==========

    def sanitize_tool_result(self, tool_name: str, result: str) -> str:
        """
        Sanitasi hasil tool untuk mencegah prompt injection.
        Tandai hasil sebagai data, bukan instruksi.
        """
        # Untuk tool yang mengambil data eksternal (web, file, router)
        data_tools = {
            "get_ha_entity", "get_mikrotik_status", "get_mikrotik_wifi_clients",
            "get_mikrotik_interface_stats", "get_mikrotik_dhcp_leases",
            "search_conversation", "get_router_status", "get_interface_traffic",
            "get_active_clients", "get_wifi_clients", "get_bandwidth_usage",
            "check_internet",
        }

        if tool_name in data_tools:
            # Bungkus hasil dengan marker data
            return f"[DATA dari {tool_name}]\n{result}\n[/DATA]"

        return result

    def is_injection_attempt(self, text: str) -> bool:
        """
        Deteksi upaya prompt injection dalam teks.
        Cari pattern seperti "ignore previous instructions", "system prompt", dll.
        """
        injection_patterns = [
            "ignore previous instructions",
            "ignore all previous",
            "forget everything",
            "system prompt",
            "you are now",
            "act as",
            "pretend to be",
            "new instructions",
            "override",
            "bypass",
            "jailbreak",
            "developer mode",
            "admin mode",
            "root access",
            "execute code",
            "run command",
            "delete all",
            "format disk",
        ]

        text_lower = text.lower()
        return any(pattern in text_lower for pattern in injection_patterns)


# Global instance
_policy: Optional[SafetyPolicy] = None


def get_policy() -> SafetyPolicy:
    """Get global safety policy instance."""
    global _policy
    if _policy is None:
        _policy = SafetyPolicy()
    return _policy


def reset_policy() -> None:
    """Reset policy (untuk testing)."""
    global _policy
    _policy = None
