"""MQTT client for ESP32 devices."""

import logging
from typing import Optional, Dict, Any, Callable, List
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MQTTDevice:
    """ESP32 device info."""
    device_id: str
    name: str
    device_type: str  # sensor, switch, light, climate
    last_seen: datetime
    state: Dict[str, Any]
    online: bool = True


class MQTTClient:
    """MQTT client for IoT devices (ESP32)."""

    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1883,
        username: str = None,
        password: str = None,
        client_id: str = "yuna",
        topic_prefix: str = "yuna",
    ):
        """
        Initialize MQTT client.

        Args:
            broker: MQTT broker host
            port: MQTT broker port
            username: Optional username
            password: Optional password
            client_id: MQTT client ID
            topic_prefix: Topic prefix for all Yuna topics
        """
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id
        self.topic_prefix = topic_prefix

        self._client = None
        self._connected = False
        self._devices: Dict[str, MQTTDevice] = {}
        self._message_handlers: Dict[str, List[Callable]] = {}
        self._connection_callback: Optional[Callable] = None

    async def connect(self):
        """Connect to MQTT broker."""
        try:
            import aiomqtt
            self._client = aiomqtt.Client(
                hostname=self.broker,
                port=self.port,
                username=self.username,
                password=self.password,
                client_id=self.client_id,
            )

            async with self._client:
                # Subscribe to device topics
                await self._client.subscribe(f"{self.topic_prefix}/+/status")
                await self._client.subscribe(f"{self.topic_prefix}/+/state")
                await self._client.subscribe(f"{self.topic_prefix}/+/telemetry")
                await self._client.subscribe(f"{self.topic_prefix}/+/availability")

                self._connected = True
                logger.info(f"MQTT connected to {self.broker}:{self.port}")

                if self._connection_callback:
                    await self._connection_callback(True)

                # Message loop
                async for message in self._client.messages:
                    await self._handle_message(message)

        except ImportError:
            logger.error("aiomqtt not installed. Install with: pip install aiomqtt")
        except Exception as e:
            logger.error(f"MQTT connection error: {e}")
            self._connected = False

    async def _handle_message(self, message):
        """Handle incoming MQTT message."""
        try:
            topic = str(message.topic)
            payload = message.payload.decode()
            data = json.loads(payload)

            # Parse topic: Yuna/{device_id}/{type}
            parts = topic.split("/")
            if len(parts) >= 3:
                device_id = parts[1]
                msg_type = parts[2]

                if msg_type == "status":
                    await self._handle_status(device_id, data)
                elif msg_type == "state":
                    await self._handle_state(device_id, data)
                elif msg_type == "telemetry":
                    await self._handle_telemetry(device_id, data)
                elif msg_type == "availability":
                    await self._handle_availability(device_id, data)

            # Call registered handlers
            for pattern, handlers in self._message_handlers.items():
                if self._topic_match(pattern, topic):
                    for handler in handlers:
                        try:
                            await handler(topic, data)
                        except Exception as e:
                            logger.error(f"Handler error: {e}")

        except Exception as e:
            logger.error(f"MQTT message error: {e}")

    def _topic_match(self, pattern: str, topic: str) -> bool:
        """Simple topic pattern matching with wildcards."""
        pattern_parts = pattern.split("/")
        topic_parts = topic.split("/")

        if len(pattern_parts) != len(topic_parts):
            return False

        for p, t in zip(pattern_parts, topic_parts):
            if p != "+" and p != "#" and p != t:
                return False

        return True

    async def _handle_status(self, device_id: str, data: Dict):
        """Handle device status update."""
        if device_id not in self._devices:
            self._devices[device_id] = MQTTDevice(
                device_id=device_id,
                name=data.get("name", device_id),
                device_type=data.get("type", "unknown"),
                last_seen=datetime.now(),
                state={},
            )

        device = self._devices[device_id]
        device.last_seen = datetime.now()
        device.online = True
        device.name = data.get("name", device.name)
        device.device_type = data.get("type", device.device_type)

        logger.info(f"Device status: {device_id} ({device.name}) - {device.device_type}")

    async def _handle_state(self, device_id: str, data: Dict):
        """Handle device state update."""
        if device_id in self._devices:
            device = self._devices[device_id]
            device.state.update(data)
            device.last_seen = datetime.now()
            logger.debug(f"Device state: {device_id} = {data}")

    async def _handle_telemetry(self, device_id: str, data: Dict):
        """Handle device telemetry."""
        if device_id in self._devices:
            device = self._devices[device_id]
            device.last_seen = datetime.now()
            # Store telemetry in state
            if "telemetry" not in device.state:
                device.state["telemetry"] = []
            device.state["telemetry"].append({
                "timestamp": datetime.now().isoformat(),
                "data": data,
            })
            # Keep last 100 telemetry points
            if len(device.state["telemetry"]) > 100:
                device.state["telemetry"] = device.state["telemetry"][-100:]

    async def _handle_availability(self, device_id: str, data: Dict):
        """Handle device availability."""
        if device_id in self._devices:
            device = self._devices[device_id]
            device.online = data.get("online", True)
            device.last_seen = datetime.now()
            logger.info(f"Device availability: {device_id} = {device.online}")

    # Device control
    async def publish_command(self, device_id: str, command: str, data: Dict = None):
        """Publish command to device."""
        if not self._client:
            logger.error("MQTT not connected")
            return False

        topic = f"{self.topic_prefix}/{device_id}/command"
        payload = {
            "command": command,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
        }

        try:
            await self._client.publish(topic, json.dumps(payload))
            logger.info(f"Command sent to {device_id}: {command}")
            return True
        except Exception as e:
            logger.error(f"Publish error: {e}")
            return False

    # Common device commands
    async def turn_on(self, device_id: str) -> bool:
        """Turn on device."""
        return await self.publish_command(device_id, "turn_on")

    async def turn_off(self, device_id: str) -> bool:
        """Turn off device."""
        return await self.publish_command(device_id, "turn_off")

    async def set_value(self, device_id: str, value: Any) -> bool:
        """Set device value (brightness, temperature, etc)."""
        return await self.publish_command(device_id, "set_value", {"value": value})

    # Device registry
    def get_device(self, device_id: str) -> Optional[MQTTDevice]:
        """Get device by ID."""
        return self._devices.get(device_id)

    def get_all_devices(self) -> List[MQTTDevice]:
        """Get all devices."""
        return list(self._devices.values())

    def get_online_devices(self) -> List[MQTTDevice]:
        """Get online devices."""
        return [d for d in self._devices.values() if d.online]

    def get_devices_by_type(self, device_type: str) -> List[MQTTDevice]:
        """Get devices by type."""
        return [d for d in self._devices.values() if d.device_type == device_type]

    # Handlers
    def register_handler(self, topic_pattern: str, handler: Callable):
        """Register message handler for topic pattern."""
        if topic_pattern not in self._message_handlers:
            self._message_handlers[topic_pattern] = []
        self._message_handlers[topic_pattern].append(handler)

    def set_connection_callback(self, callback: Callable):
        """Set connection status callback."""
        self._connection_callback = callback

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected


# Global instance
_mqtt_client: Optional[MQTTClient] = None


def get_mqtt_client(**kwargs) -> MQTTClient:
    """Get global MQTT client."""
    global _mqtt_client
    if _mqtt_client is None:
        _mqtt_client = MQTTClient(**kwargs)
    return _mqtt_client


async def init_mqtt_client(**kwargs) -> MQTTClient:
    """Initialize and connect MQTT client."""
    global _mqtt_client
    _mqtt_client = MQTTClient(**kwargs)
    # Start connection in background
    asyncio.create_task(_mqtt_client.connect())
    return _mqtt_client
