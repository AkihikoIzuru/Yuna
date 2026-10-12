"""Home automation tools - HA, MQTT, Mikrotik, alerts."""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from yuna.tools.registry import tool
from yuna.memory import ReminderManager
from yuna.home.ha import HomeAssistantClient, get_ha_client, init_ha_client
from yuna.home.mqtt import MQTTClient, get_mqtt_client, init_mqtt_client
from yuna.home.mikrotik import MikrotikClient, get_mikrotik_client, init_mikrotik_client
from yuna.home.alerts import AlertManager, get_alert_manager, AlertLevel

logger = logging.getLogger(__name__)

# Config from env (Fase 4: optional)
import os
HA_URL = os.getenv("YUNA_HA_URL")
HA_TOKEN = os.getenv("YUNA_HA_TOKEN")
MQTT_BROKER = os.getenv("YUNA_MQTT_BROKER")
MQTT_USER = os.getenv("YUNA_MQTT_USER")
MQTT_PASS = os.getenv("YUNA_MQTT_PASS")
MIKROTIK_HOST = os.getenv("YUNA_MIKROTIK_HOST")
MIKROTIK_USER = os.getenv("YUNA_MIKROTIK_USER")
MIKROTIK_PASS = os.getenv("YUNA_MIKROTIK_PASS")


# --- Tools ---

@tool(risk="low")
def get_ha_system_status() -> str:
    """Cek status sistem Home Assistant (versi, hostname, uptime)."""
    try:
        ha = get_ha_client(HA_URL, HA_TOKEN)
        if not ha:
            return "Home Assistant belum dikonfigurasi. Tambahkan YUNA_HA_URL dan YUNA_HA_TOKEN di .env"

        # Get system info
        import asyncio
        result = asyncio.new_event_loop().run_until_complete(ha.check_connection())

        if result:
            states = asyncio.new_event_loop().run_until_complete(ha.get_states())
            entity_count = len(states) if isinstance(states, list) else 0

            # Try to get system info
            try:
                identity = asyncio.new_event_loop().run_until_complete(ha.get_system_identity())
                return f"Home Assistant: Online - {entity_count} entitas"
            except:
                return f"Home Assistant: Online - {entity_count} entitas"
        else:
            return "Home Assistant: Tidak terhubung"

    except Exception as e:
        return f"Error: {e}"


@tool(risk="low")
def get_ha_entity(entity_id: str) -> str:
    """Ambil status entitas HA tertentu (contoh: light. Living Room)."""
    try:
        ha = get_ha_client(HA_URL, HA_TOKEN)
        if not ha:
            return "Home Assistant belum dikonfigurasi"

        state = asyncio.new_event_loop().run_until_complete(ha.get_state(entity_id))

        if "error" in state:
            return f"Error: {state['error']}"

        state_str = state.get("state", "unknown")
        attrs = state.get("attributes", {})

        result = f"{entity_id}: {state_str}"
        if attrs:
            extra = ", ".join([f"{k}={v}" for k, v in attrs.items() if k != "friendly_name"])
            if extra:
                result += f" ({extra})"

        return result

    except Exception as e:
        return f"Error: {e}"


@tool(risk="medium")
def ha_turn_on_light(entity_id: str) -> str:
    """Nyalakan lampu di HA (contoh: light. Living Room)."""
    try:
        ha = get_ha_client(HA_URL, HA_TOKEN)
        if not ha:
            return "Home Assistant belum dikonfigurasi"

        result = asyncio.new_event_loop().run_until_complete(ha.light_turn_on(entity_id))

        if "error" in result:
            return f"Error: {result['error']}"

        return f"Lampu {entity_id} dinyalakan"

    except Exception as e:
        return f"Error: {e}"


@tool(risk="medium")
def ha_turn_off_light(entity_id: str) -> str:
    """Matikan lampu di HA."""
    try:
        ha = get_ha_client(HA_URL, HA_TOKEN)
        if not ha:
            return "Home Assistant belum dikonfigurasi"

        result = asyncio.new_event_loop().run_until_complete(ha.light_turn_off(entity_id))

        if "error" in result:
            return f"Error: {result['error']}"

        return f"Lampu {entity_id} dimatikan"

    except Exception as e:
        return f"Error: {e}"


@tool(risk="medium")
def ha_toggle_light(entity_id: str) -> str:
    """Toggle lampu HA (nyala â†’ mati atau sebaliknya)."""
    try:
        ha = get_ha_client(HA_URL, HA_TOKEN)
        if not ha:
            return "Home Assistant belum dikonfigurasi"

        result = asyncio.new_event_loop().run_until_complete(ha.light_toggle(entity_id))

        if "error" in result:
            return f"Error: {result['error']}"

        return f"Lampu {entity_id} di-toggle"

    except Exception as e:
        return f"Error: {e}"


@tool(risk="medium")
def ha_set_temperature(entity_id: str, temperature: float) -> str:
    """Set suhu AC/Thermostat di HA (contoh: climate.Living Room 24)."""
    try:
        ha = get_ha_client(HA_URL, HA_TOKEN)
        if not ha:
            return "Home Assistant belum dikonfigurasi"

        result = asyncio.new_event_loop().run_until_complete(
            ha.climate_set_temperature(entity_id, temperature)
        )

        if "error" in result:
            return f"Error: {result['error']}"

        return f"Suhu {entity_id} diset ke {temperature}Â°C"

    except Exception as e:
        return f"Error: {e}"


@tool(risk="low")
def get_mikrotik_status() -> str:
    """Cek status router Mikrotik (CPU, RAM, uptime, koneksi)."""
    try:
        client = get_mikrotik_client(MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS)
        if not client:
            return "Mikrotik belum dikonfigurasi. Tambahkan YUNA_MIKROTIK_HOST di .env"

        import asyncio
        resource = asyncio.new_event_loop().run_until_complete(client.get_system_resource())

        if "error" in resource:
            return f"Error: {resource['error']}"

        identity = asyncio.new_event_loop().run_until_complete(client.get_system_identity())
        name = identity.get("name", "Unknown")
        uptime = resource.get("uptime", "N/A")
        cpu_load = resource.get("cpu-usage", "N/A")
        memory_free = resource.get("memory-free", "N/A")
        memory_total = resource.get("memory-total", "N/A")

        # Calculate memory usage
        try:
            free_mb = int(memory_free.replace("MiB", "").strip()) if memory_free else 0
            total_mb = int(memory_total.replace("MiB", "").strip()) if memory_total else 1
            used_percent = round((total_mb - free_mb) / total_mb * 100, 1)
        except:
            used_percent = "N/A"

        return (
            f"Router {name}:\n"
            f"  CPU: {cpu_load}%\n"
            f"  RAM: {used_percent}% ({memory_free} dari {memory_total})\n"
            f"  Uptime: {uptime}"
        )

    except Exception as e:
        return f"Error: {e}"


@tool(risk="low")
def get_mikrotik_wifi_clients() -> str:
    """List WiFi clients yang terhubung ke Mikrotik."""
    try:
        client = get_mikrotik_client(MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS)
        if not client:
            return "Mikrotik belum dikonfigurasi"

        import asyncio
        clients = asyncio.new_event_loop().run_until_complete(
            client.get_wireless_registrations()
        )

        if "error" in str(clients):
            return f"Error: {clients}"

        if not clients:
            return "Tidak ada WiFi client terhubung"

        lines = [f"WiFi Clients ({len(clients)} perangkat):"]
        for i, client in enumerate(clients[:10], 1):  # Limit 10
            mac = client.get("mac-address", "N/A")
            signal = client.get("signal-strength", "N/A")
            rssi = client.get("rssi", "N/A")
            line = f"  {i}. {mac} (RSSI: {rssi}dBm)"
            if signal and signal != "N/A":
                line += f" | Signal: {signal}"
            lines.append(line)

        if len(clients) > 10:
            lines.append(f"  ... dan {len(clients) - 10} lainnya")

        return "\n".join(lines)

    except Exception as e:
        return f"Error: {e}"


@tool(risk="low")
def get_mikrotik_interface_stats(interface: str = "") -> str:
    """Cek statistik interface (RX/TX traffic)."""
    try:
        client = get_mikrotik_client(MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS)
        if not client:
            return "Mikrotik belum dikonfigurasi"

        import asyncio

        if interface:
            # Single interface
            stats = asyncio.new_event_loop().run_until_complete(
                client.get_interface_traffic(interface)
            )
            if "error" in stats:
                return f"Error: {stats['error']}"

            rx_rate = stats.get("rx-rate", "0 bps")
            tx_rate = stats.get("tx-rate", "0 bps")
            rx_packets = stats.get("rx-packets", "0")
            tx_packets = stats.get("tx-packets", "0")

            return (
                f"Interface {interface}:\n"
                f"  RX: {rx_rate} ({rx_packets} packets)\n"
                f"  TX: {tx_rate} ({tx_packets} packets)"
            )
        else:
            # All interfaces
            interfaces = asyncio.new_event_loop().run_until_complete(
                client.get_interfaces()
            )
            if "error" in str(interfaces):
                return f"Error: {interfaces}"

            lines = ["Interface Statistics:"]
            for iface in interfaces:
                name = iface.get("name", "unknown")
                if name.startswith("wlan"):
                    continue  # Skip WiFi for this view

                rx_speed = iface.get("rx-speed", "N/A")
                tx_speed = iface.get("tx-speed", "N/A")
                running = iface.get("running", "false")

                status = "Up" if running == "true" else "Down"
                lines.append(f"  {name}: {status} (RX: {rx_speed}, TX: {tx_speed})")

            return "\n".join(lines)

    except Exception as e:
        return f"Error: {e}"


@tool(risk="low")
def get_mikrotik_dhcp_leases() -> str:
    """List DHCP leases (perangkat yang koneksi via kabel)."""
    try:
        client = get_mikrotik_client(MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS)
        if not client:
            return "Mikrotik belum dikonfigurasi"

        import asyncio
        leases = asyncio.new_event_loop().run_until_complete(
            client.get_dhcp_leases()
        )

        if "error" in str(leases):
            return f"Error: {leases}"

        if not leases:
            return "Tidak ada DHCP lease aktif"

        lines = [f"DHCP Leases ({len(leases)} perangkat):"]
        for i, lease in enumerate(leases[:10], 1):
            address = lease.get("address", "N/A")
            mac = lease.get("mac-address", "N/A")
            hostname = lease.get("hostname", "N/A")
            active = lease.get("active-address", "N/A")
            status = lease.get("status", "unknown")

            line = f"  {i}. {address} ({mac})"
            if hostname and hostname != "N/A":
                line += f" - {hostname}"
            line += f" [{status}]"
            lines.append(line)

        return "\n".join(lines)

    except Exception as e:
        return f"Error: {e}"


@tool(risk="low")
def trigger_alert(level: str, title: str, message: str) -> str:
    """Trigger alert manual (info, warning, critical)."""
    try:
        manager = get_alert_manager()

        level_map = {
            "info": AlertLevel.INFO,
            "warning": AlertLevel.WARNING,
            "critical": AlertLevel.CRITICAL,
        }

        alert_level = level_map.get(level.lower(), AlertLevel.INFO)

        alert = manager.create_alert(
            level=alert_level,
            source="manual",
            title=title,
            message=message,
        )

        return f"Alert triggered: [{level.upper()}] {title}"

    except Exception as e:
        return f"Error: {e}"


@tool(risk="low")
def get_alerts(count: int = 10) -> str:
    """Lihat alert terakhir."""
    try:
        manager = get_alert_manager()
        alerts = manager.get_recent(limit=count)

        if not alerts:
            return "Tidak ada alert"

        lines = [f"Alert Terakhir ({len(alerts)}):"]
        for i, alert in enumerate(alerts, 1):
            status = "âœ…" if alert.acknowledged else "â³"
            lines.append(f"  {i}. [{alert.level.value.upper()}] {status} {alert.title}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error: {e}"


@tool(risk="low")
def acknowledge_alert(alert_id: str) -> str:
    """Acknowledge (tandai sudah dibaca) alert tertentu."""
    try:
        manager = get_alert_manager()
        acknowledged = manager.acknowledge_alert(alert_id)

        if acknowledged:
            return f"Alert {alert_id} ditandai sudah dibaca"
        return f"Alert {alert_id} tidak ditemukan"

    except Exception as e:
        return f"Error: {e}"

