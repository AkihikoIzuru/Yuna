"""Proactive alert manager for home monitoring."""

import logging
import asyncio
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from yuna.memory import ReminderManager

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data class."""
    id: str
    level: AlertLevel
    source: str  # ha, mqtt, mikrotik, system
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class AlertManager:
    """Manage proactive alerts from various sources."""

    def __init__(self, reminder_manager: ReminderManager = None):
        self.alerts: List[Alert] = []
        self._handlers: List[Callable[[Alert], Any]] = []
        self._running = False
        self._check_task: Optional[asyncio.Task] = None
        self._reminder_manager = reminder_manager

        # Thresholds
        self.thresholds = {
            "cpu_percent": 80,
            "memory_percent": 85,
            "disk_percent": 90,
            "temperature_celsius": 70,
            "voltage_deviation": 0.1,  # 10%
        }

    def add_handler(self, handler: Callable[[Alert], Any]):
        """Add alert handler (async or sync)."""
        self._handlers.append(handler)

    async def _dispatch_alert(self, alert: Alert):
        """Dispatch alert to all handlers."""
        for handler in self._handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    def create_alert(
        self,
        level: AlertLevel,
        source: str,
        title: str,
        message: str,
        metadata: Dict[str, Any] = None,
    ) -> Alert:
        """Create and dispatch alert."""
        alert = Alert(
            id=f"{source}_{datetime.now().timestamp()}",
            level=level,
            source=source,
            title=title,
            message=message,
            metadata=metadata or {},
        )

        self.alerts.append(alert)

        # Keep only last 1000 alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]

        logger.log(
            logging.WARNING if level in (AlertLevel.WARNING, AlertLevel.CRITICAL) else logging.INFO,
            f"Alert [{level.value.upper()}] {source}: {title} - {message}"
        )

        # Dispatch sync (handlers can be async but we'll run them in background task)
        self._dispatch_sync(alert)

        # If critical, also create reminder for TTS
        if level == AlertLevel.CRITICAL and self._reminder_manager:
            self._reminder_manager.add_reminder(
                datetime.now() + timedelta(seconds=5),
                f"Peringatan kritis: {title} - {message}"
            )

        return alert

    def _dispatch_sync(self, alert: Alert):
        """Dispatch alert to handlers synchronously."""
        for handler in self._handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    # Schedule async handler
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(handler(alert))
                    except RuntimeError:
                        # No running loop, skip async handler
                        pass
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge alert."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_unacknowledged(self) -> List[Alert]:
        """Get unacknowledged alerts."""
        return [a for a in self.alerts if not a.acknowledged]

    def get_recent(self, limit: int = 50) -> List[Alert]:
        """Get recent alerts."""
        return sorted(self.alerts, key=lambda a: a.timestamp, reverse=True)[:limit]

    def get_by_level(self, level: AlertLevel) -> List[Alert]:
        """Get alerts by level."""
        return [a for a in self.alerts if a.level == level]

    def get_by_source(self, source: str) -> List[Alert]:
        """Get alerts by source."""
        return [a for a in self.alerts if a.source == source]

    # Threshold checking helpers
    def check_threshold(
        self,
        metric: str,
        value: float,
        source: str,
        title: str,
        metadata: Dict = None,
    ):
        """Check if value exceeds threshold and create alert."""
        threshold = self.thresholds.get(metric)
        if threshold is None:
            return

        if value >= threshold:
            level = AlertLevel.CRITICAL if value >= threshold * 1.2 else AlertLevel.WARNING
            self.create_alert(
                level=level,
                source=source,
                title=title,
                message=f"{metric} = {value} (threshold: {threshold})",
                metadata={**(metadata or {}), "metric": metric, "value": value, "threshold": threshold},
            )

    def check_range(
        self,
        metric: str,
        value: float,
        min_val: float,
        max_val: float,
        source: str,
        title: str,
        metadata: Dict = None,
    ):
        """Check if value is outside range."""
        if value < min_val or value > max_val:
            level = AlertLevel.CRITICAL if (value < min_val * 0.8 or value > max_val * 1.2) else AlertLevel.WARNING
            self.create_alert(
                level=level,
                source=source,
                title=title,
                message=f"{metric} = {value} (range: {min_val}-{max_val})",
                metadata={**(metadata or {}), "metric": metric, "value": value, "min": min_val, "max": max_val},
            )

    # Monitoring tasks
    async def start_monitoring(self, interval: int = 60):
        """Start background monitoring."""
        self._running = True
        self._check_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info(f"Alert monitoring started (interval={interval}s)")

    async def stop_monitoring(self):
        """Stop background monitoring."""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("Alert monitoring stopped")

    async def _monitor_loop(self, interval: int):
        """Background monitoring loop."""
        while self._running:
            try:
                # This will be called by external monitors
                # (HA, MQTT, Mikrotik will call check_threshold directly)
                pass
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

            await asyncio.sleep(interval)


# Pre-built handlers
async def tts_alert_handler(alert: Alert, tts_client=None):
    """TTS handler for critical alerts."""
    if alert.level == AlertLevel.CRITICAL and tts_client:
        await tts_client.speak_stream_and_play(f"Peringatan: {alert.title}. {alert.message}")


def log_alert_handler(alert: Alert):
    """Simple log handler."""
    pass  # Already logged in create_alert


# Global instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager(reminder_manager: ReminderManager = None) -> AlertManager:
    """Get global alert manager."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager(reminder_manager)
    return _alert_manager


def init_alert_manager(reminder_manager: ReminderManager = None) -> AlertManager:
    """Initialize alert manager."""
    global _alert_manager
    _alert_manager = AlertManager(reminder_manager)
    return _alert_manager
