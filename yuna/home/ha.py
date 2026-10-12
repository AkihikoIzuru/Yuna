"""Home Assistant API client."""

import logging
from typing import Optional, Dict, Any, List
import asyncio
import aiohttp

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """Home Assistant REST API client."""

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: int = 10,
    ):
        """
        Initialize HA client.

        Args:
            base_url: Home Assistant URL (e.g., http://homeassistant.local:8123)
            token: Long-lived access token
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )
        return self._session

    async def close(self):
        """Close session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to HA API."""
        session = await self._get_session()
        url = f"{self.base_url}/api{endpoint}"

        try:
            async with session.request(method, url, json=data) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    logger.error(f"HA API error {resp.status}: {text}")
                    return {"error": f"HTTP {resp.status}", "detail": text}

                if resp.status == 204:
                    return {"success": True}

                return await resp.json()
        except asyncio.TimeoutError:
            logger.error(f"HA API timeout: {url}")
            return {"error": "timeout"}
        except Exception as e:
            logger.error(f"HA API error: {e}")
            return {"error": str(e)}

    # Entity states
    async def get_states(self) -> List[Dict[str, Any]]:
        """Get all entity states."""
        return await self._request("GET", "/states")

    async def get_state(self, entity_id: str) -> Dict[str, Any]:
        """Get specific entity state."""
        return await self._request("GET", f"/states/{entity_id}")

    # Services
    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: Optional[str] = None,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Call a service."""
        payload = data or {}
        if entity_id:
            payload["entity_id"] = entity_id
        return await self._request("POST", f"/services/{domain}/{service}", payload)

    # Light
    async def light_turn_on(self, entity_id: str, **kwargs) -> Dict[str, Any]:
        """Turn on light."""
        return await self.call_service("light", "turn_on", entity_id, kwargs)

    async def light_turn_off(self, entity_id: str) -> Dict[str, Any]:
        """Turn off light."""
        return await self.call_service("light", "turn_off", entity_id)

    async def light_toggle(self, entity_id: str) -> Dict[str, Any]:
        """Toggle light."""
        return await self.call_service("light", "toggle", entity_id)

    # Switch
    async def switch_turn_on(self, entity_id: str) -> Dict[str, Any]:
        """Turn on switch."""
        return await self.call_service("switch", "turn_on", entity_id)

    async def switch_turn_off(self, entity_id: str) -> Dict[str, Any]:
        """Turn off switch."""
        return await self.call_service("switch", "turn_off", entity_id)

    async def switch_toggle(self, entity_id: str) -> Dict[str, Any]:
        """Toggle switch."""
        return await self.call_service("switch", "toggle", entity_id)

    # Climate
    async def climate_set_temperature(
        self,
        entity_id: str,
        temperature: float,
    ) -> Dict[str, Any]:
        """Set climate temperature."""
        return await self.call_service(
            "climate",
            "set_temperature",
            entity_id,
            {"temperature": temperature},
        )

    async def climate_set_hvac_mode(
        self,
        entity_id: str,
        hvac_mode: str,
    ) -> Dict[str, Any]:
        """Set HVAC mode (heat, cool, auto, off)."""
        return await self.call_service(
            "climate",
            "set_hvac_mode",
            entity_id,
            {"hvac_mode": hvac_mode},
        )

    # Media player
    async def media_play(self, entity_id: str) -> Dict[str, Any]:
        """Play media."""
        return await self.call_service("media_player", "media_play", entity_id)

    async def media_pause(self, entity_id: str) -> Dict[str, Any]:
        """Pause media."""
        return await self.call_service("media_player", "media_pause", entity_id)

    async def media_volume_set(
        self,
        entity_id: str,
        volume: float,
    ) -> Dict[str, Any]:
        """Set volume (0.0-1.0)."""
        return await self.call_service(
            "media_player",
            "volume_set",
            entity_id,
            {"volume_level": volume},
        )

    # Cover
    async def cover_open(self, entity_id: str) -> Dict[str, Any]:
        """Open cover."""
        return await self.call_service("cover", "open_cover", entity_id)

    async def cover_close(self, entity_id: str) -> Dict[str, Any]:
        """Close cover."""
        return await self.call_service("cover", "close_cover", entity_id)

    async def cover_stop(self, entity_id: str) -> Dict[str, Any]:
        """Stop cover."""
        return await self.call_service("cover", "stop_cover", entity_id)

    # Script/Automation
    async def script_turn_on(self, entity_id: str) -> Dict[str, Any]:
        """Run script."""
        return await self.call_service("script", "turn_on", entity_id)

    async def automation_trigger(self, entity_id: str) -> Dict[str, Any]:
        """Trigger automation."""
        return await self.call_service("automation", "trigger", entity_id)

    # Health check
    async def check_connection(self) -> bool:
        """Check if HA is reachable."""
        try:
            result = await self._request("GET", "/")
            return "error" not in result
        except:
            return False


# Global instance
_ha_client: Optional[HomeAssistantClient] = None


def get_ha_client(
    base_url: str = None,
    token: str = None,
) -> HomeAssistantClient:
    """Get global HA client (singleton)."""
    global _ha_client
    if _ha_client is None and base_url and token:
        _ha_client = HomeAssistantClient(base_url, token)
    return _ha_client


async def init_ha_client(base_url: str, token: str) -> HomeAssistantClient:
    """Initialize HA client."""
    global _ha_client
    _ha_client = HomeAssistantClient(base_url, token)
    # Test connection
    if await _ha_client.check_connection():
        logger.info("Home Assistant connected")
    else:
        logger.warning("Home Assistant connection failed")
    return _ha_client