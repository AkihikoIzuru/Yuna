"""Tests for home automation module."""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from yuna.home.ha import HomeAssistantClient
from yuna.home.mqtt import MQTTClient, MQTTDevice
from yuna.home.mikrotik import MikrotikClient
from yuna.home.alerts import AlertManager, Alert, AlertLevel


class TestHomeAssistantClient:
    """Test Home Assistant client."""

    @pytest.fixture
    def ha_client(self):
        return HomeAssistantClient("http://ha.local:8123", "test-token")

    def test_init(self, ha_client):
        assert ha_client.base_url == "http://ha.local:8123"
        assert ha_client.token == "test-token"
        assert ha_client.timeout == 10


class TestMQTTClient:
    """Test MQTT client."""

    @pytest.fixture
    def mqtt_client(self):
        return MQTTClient("localhost", 1883)

    def test_init(self, mqtt_client):
        assert mqtt_client.broker == "localhost"
        assert mqtt_client.port == 1883
        assert mqtt_client.client_id == "yuna"
        assert mqtt_client.topic_prefix == "yuna"
        assert mqtt_client.is_connected is False

    def test_device_creation(self):
        device = MQTTDevice(
            device_id="esp32_001",
            name="Living Room Sensor",
            device_type="sensor",
            last_seen=datetime.now(),
            state={"temperature": 25.5},
        )
        assert device.device_id == "esp32_001"
        assert device.name == "Living Room Sensor"
        assert device.device_type == "sensor"
        assert device.online is True


class TestMikrotikClient:
    """Test Mikrotik client."""

    @pytest.fixture
    def mikrotik_client(self):
        return MikrotikClient("192.168.1.1", "admin", "password")

    def test_init(self, mikrotik_client):
        assert mikrotik_client.host == "192.168.1.1"
        assert mikrotik_client.username == "admin"
        assert mikrotik_client.port == 8728
        assert mikrotik_client.is_connected is False


class TestAlertManager:
    """Test Alert Manager."""

    @pytest.fixture
    def alert_manager(self):
        return AlertManager()

    def test_create_alert(self, alert_manager):
        alert = alert_manager.create_alert(
            level=AlertLevel.WARNING,
            source="test",
            title="Test Alert",
            message="This is a test",
        )

        assert alert.level == AlertLevel.WARNING
        assert alert.source == "test"
        assert alert.title == "Test Alert"
        assert alert.message == "This is a test"
        assert alert.acknowledged is False

    def test_get_recent(self, alert_manager):
        alert_manager.create_alert(AlertLevel.INFO, "test", "Alert 1", "Message 1")
        time.sleep(0.01)
        alert_manager.create_alert(AlertLevel.WARNING, "test", "Alert 2", "Message 2")

        recent = alert_manager.get_recent(limit=5)
        assert len(recent) == 2
        # Most recent first
        assert recent[0].title == "Alert 2"

    def test_acknowledge_alert(self, alert_manager):
        alert = alert_manager.create_alert(AlertLevel.INFO, "test", "Test", "Message")

        result = alert_manager.acknowledge_alert(alert.id)
        assert result is True
        assert alert.acknowledged is True

    def test_get_unacknowledged(self, alert_manager):
        alert1 = alert_manager.create_alert(AlertLevel.INFO, "test", "Alert 1", "Msg")
        alert2 = alert_manager.create_alert(AlertLevel.WARNING, "test", "Alert 2", "Msg")
        alert_manager.acknowledge_alert(alert1.id)

        unack = alert_manager.get_unacknowledged()
        assert len(unack) == 1
        assert unack[0].id == alert2.id

    def test_check_threshold(self, alert_manager):
        # Should create warning at threshold
        alert_manager.check_threshold(
            metric="cpu_percent",
            value=85,
            source="system",
            title="High CPU",
        )

        alerts = alert_manager.get_by_level(AlertLevel.WARNING)
        assert len(alerts) >= 1

        # Should create critical at 1.2x threshold
        alert_manager.check_threshold(
            metric="cpu_percent",
            value=100,
            source="system",
            title="Critical CPU",
        )

        critical = alert_manager.get_by_level(AlertLevel.CRITICAL)
        assert len(critical) >= 1

    def test_check_range(self, alert_manager):
        alert_manager.check_range(
            metric="voltage",
            value=10.5,  # Outside 11-13 range
            min_val=11.0,
            max_val=13.0,
            source="system",
            title="Voltage Low",
        )

        alerts = alert_manager.get_by_level(AlertLevel.WARNING)
        assert len(alerts) >= 1
        assert "voltage" in alerts[-1].metadata.get("metric", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])