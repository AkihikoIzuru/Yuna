"""Mikrotik RouterOS API client (read-only monitoring)."""

import logging
from typing import Optional, Dict, Any, List
import asyncio
import ssl

logger = logging.getLogger(__name__)


class MikrotikClient:
    """Mikrotik RouterOS API client for monitoring."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 8728,  # Default API port
        use_ssl: bool = False,
        timeout: int = 10,
    ):
        """
        Initialize Mikrotik client.

        Args:
            host: Router IP/hostname
            username: API username (read-only recommended)
            password: API password
            port: API port (8728 plain, 8729 SSL)
            use_ssl: Use SSL connection
            timeout: Connection timeout
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.use_ssl = use_ssl
        self.timeout = timeout

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._tag_counter = 0

    async def connect(self) -> bool:
        """Connect to RouterOS API."""
        try:
            if self.use_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(
                        self.host,
                        self.port,
                        ssl=ssl_context,
                    ),
                    timeout=self.timeout,
                )
            else:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=self.timeout,
                )

            # Login
            await self._login()
            self._connected = True
            logger.info(f"Mikrotik connected: {self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"Mikrotik connection error: {e}")
            self._connected = False
            return False

    async def _login(self):
        """Login to RouterOS API."""
        # Send login command
        await self._send_sentence(["/login"])

        # Read response
        response = await self._read_sentence()

        if "!done" in response:
            # Already logged in (no password needed)
            return

        # Need to send password
        # Get challenge
        challenge = None
        for item in response:
            if "=ret=" in item:
                challenge = item.split("=ret=")[1]
                break

        if challenge:
            # Send password with challenge
            import hashlib
            import binascii

            # RouterOS uses MD5: md5('\x00' + password + challenge)
            hash_obj = hashlib.md5()
            hash_obj.update(b'\x00')
            hash_obj.update(self.password.encode())
            hash_obj.update(binascii.unhexlify(challenge))
            password_hash = hash_obj.hexdigest()

            await self._send_sentence([
                "/login",
                f"=name={self.username}",
                f"=response=00{password_hash}",
            ])

            response = await self._read_sentence()
            if "!done" not in str(response):
                raise Exception("Login failed")

    async def _send_sentence(self, words: List[str]):
        """Send API sentence."""
        for word in words:
            await self._send_word(word)
        self._writer.write(b'\x00')
        await self._writer.drain()

    async def _send_word(self, word: str):
        """Send single word (length-prefixed)."""
        data = word.encode()
        length = len(data)

        # Encode length
        if length < 0x80:
            self._writer.write(bytes([length]))
        elif length < 0x4000:
            self._writer.write(bytes([(length >> 8) | 0x80, length & 0xFF]))
        elif length < 0x200000:
            self._writer.write(bytes([
                (length >> 16) | 0xC0,
                (length >> 8) & 0xFF,
                length & 0xFF,
            ]))
        elif length < 0x10000000:
            self._writer.write(bytes([
                (length >> 24) | 0xE0,
                (length >> 16) & 0xFF,
                (length >> 8) & 0xFF,
                length & 0xFF,
            ]))
        else:
            self._writer.write(bytes([0xF0]))
            self._writer.write(length.to_bytes(4, 'big'))

        self._writer.write(data)

    async def _read_word(self) -> Optional[bytes]:
        """Read length-prefixed word."""
        # Read length
        first = await self._reader.read(1)
        if not first:
            return None

        first_byte = first[0]

        if first_byte < 0x80:
            length = first_byte
        elif first_byte < 0xC0:
            second = await self._reader.read(1)
            length = ((first_byte & 0x3F) << 8) | second[0]
        elif first_byte < 0xE0:
            rest = await self._reader.read(2)
            length = ((first_byte & 0x1F) << 16) | (rest[0] << 8) | rest[1]
        elif first_byte < 0xF0:
            rest = await self._reader.read(3)
            length = ((first_byte & 0x0F) << 24) | (rest[0] << 16) | (rest[1] << 8) | rest[2]
        else:
            rest = await self._reader.read(4)
            length = int.from_bytes(rest, 'big')

        if length == 0:
            return b''

        return await self._reader.read(length)

    async def _read_sentence(self) -> List[bytes]:
        """Read API sentence."""
        words = []
        while True:
            word = await self._read_word()
            if word is None:
                break
            if word == b'':
                break
            words.append(word)
        return words

    async def close(self):
        """Close connection."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        self._connected = False
        logger.info("Mikrotik disconnected")

    async def _command(self, command: str, *args) -> List[Dict[str, str]]:
        """Execute command and parse response."""
        if not self._connected:
            await self.connect()
            if not self._connected:
                return [{"error": "Not connected"}]

        self._tag_counter += 1
        tag = str(self._tag_counter)

        words = [command, f".tag={tag}"]
        words.extend(args)

        await self._send_sentence(words)

        results = []
        while True:
            response = await self._read_sentence()
            if not response:
                break

            if response[0] == b'!done':
                # Check tag
                for item in response[1:]:
                    if item.startswith(b'.tag='):
                        if item[5:].decode() == tag:
                            return results
                break
            elif response[0] == b'!trap':
                return [{"error": "Command failed"}]
            elif response[0] == b'!re':
                # Parse data
                data = {}
                for item in response[1:]:
                    decoded = item.decode()
                    if '=' in decoded:
                        key, value = decoded.split('=', 1)
                        data[key] = value
                results.append(data)

        return results

    # System info
    async def get_system_resource(self) -> Dict[str, Any]:
        """Get system resource info (CPU, RAM, disk, uptime)."""
        result = await self._command("/system/resource/print")
        return result[0] if result else {}

    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health (voltage, temperature)."""
        result = await self._command("/system/health/print")
        return result[0] if result else {}

    async def get_system_identity(self) -> Dict[str, Any]:
        """Get router identity."""
        result = await self._command("/system/identity/print")
        return result[0] if result else {}

    # Interfaces
    async def get_interfaces(self) -> List[Dict[str, Any]]:
        """Get all interfaces with stats."""
        return await self._command("/interface/print", "=stats")

    async def get_interface(self, name: str) -> Dict[str, Any]:
        """Get specific interface."""
        result = await self._command("/interface/print", f"=name={name}", "=stats")
        return result[0] if result else {}

    # IP addresses
    async def get_ip_addresses(self) -> List[Dict[str, Any]]:
        """Get IP addresses."""
        return await self._command("/ip/address/print")

    # DHCP leases
    async def get_dhcp_leases(self) -> List[Dict[str, Any]]:
        """Get DHCP leases."""
        return await self._command("/ip/dhcp-server/lease/print")

    # Wireless
    async def get_wireless_registrations(self) -> List[Dict[str, Any]]:
        """Get wireless clients."""
        return await self._command("/interface/wireless/registration-table/print")

    # Firewall
    async def get_firewall_connections(self) -> List[Dict[str, Any]]:
        """Get active firewall connections."""
        return await self._command("/ip/firewall/connection/print")

    # Traffic
    async def get_interface_traffic(self, interface: str) -> Dict[str, Any]:
        """Get interface traffic stats."""
        result = await self._command("/interface/monitor-traffic", f"=interface={interface}", "=once")
        return result[0] if result else {}

    # Logs
    async def get_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get system logs."""
        return await self._command("/log/print", f"=limit={limit}")

    # Users
    async def get_active_users(self) -> List[Dict[str, Any]]:
        """Get active PPP/VPN users."""
        return await self._command("/ppp/active/print")

    # System clock
    async def get_system_clock(self) -> Dict[str, Any]:
        """Get system clock."""
        result = await self._command("/system/clock/print")
        return result[0] if result else {}

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    # Health check
    async def check_connection(self) -> bool:
        """Check connection."""
        try:
            result = await self.get_system_identity()
            return "error" not in result
        except:
            return False


# Global instance
_mikrotik_client: Optional[MikrotikClient] = None


def get_mikrotik_client(**kwargs) -> MikrotikClient:
    """Get global Mikrotik client."""
    global _mikrotik_client
    if _mikrotik_client is None:
        _mikrotik_client = MikrotikClient(**kwargs)
    return _mikrotik_client


async def init_mikrotik_client(**kwargs) -> MikrotikClient:
    """Initialize and connect Mikrotik client."""
    global _mikrotik_client
    _mikrotik_client = MikrotikClient(**kwargs)
    await _mikrotik_client.connect()
    return _mikrotik_client