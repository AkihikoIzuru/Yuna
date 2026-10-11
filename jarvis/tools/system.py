"""System tools - waktu, info sistem, buka aplikasi, timer."""

import asyncio
import logging
import platform
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Optional

import psutil

from jarvis.tools.registry import tool

logger = logging.getLogger(__name__)

# Timer storage (untuk Fase 1, simple dict. Fase 3 akan pakai database)
_timers: dict[str, asyncio.Task] = {}


@tool(risk="low")
def get_time() -> str:
    """Dapatkan waktu saat ini (jam dan menit)."""
    now = datetime.now()
    return now.strftime("%H:%M")


@tool(risk="low")
def get_date() -> str:
    """Dapatkan tanggal hari ini (format: hari, DD bulan YYYY)."""
    now = datetime.now()
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    months = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]

    day_name = days[now.weekday()]
    month_name = months[now.month - 1]

    return f"{day_name}, {now.day} {month_name} {now.year}"


@tool(risk="low")
def get_system_info() -> str:
    """Dapatkan informasi sistem (OS, CPU, RAM, disk)."""
    info = {
        "os": f"{platform.system()} {platform.release()}",
        "cpu_percent": psutil.cpu_percent(interval=1),
        "ram_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent if platform.system() != "Windows" else psutil.disk_usage("C:\\").percent,
    }

    return (
        f"OS: {info['os']}, "
        f"CPU: {info['cpu_percent']:.1f}%, "
        f"RAM: {info['ram_percent']:.1f}%, "
        f"Disk: {info['disk_percent']:.1f}%"
    )


@tool(risk="medium")
def open_app(app_name: str) -> str:
    """
    Buka aplikasi di komputer.

    Args:
        app_name: Nama aplikasi (contoh: notepad, calculator, chrome)
    """
    is_windows = platform.system() == "Windows"

    # Mapping common app names
    app_map = {
        "kalkulator": "calc" if is_windows else "gnome-calculator",
        "calculator": "calc" if is_windows else "gnome-calculator",
        "notepad": "notepad" if is_windows else "gedit",
        "chrome": "chrome" if is_windows else "google-chrome",
        "firefox": "firefox",
        "edge": "msedge" if is_windows else "microsoft-edge",
        "vscode": "code",
        "code": "code",
    }

    app_name_lower = app_name.lower()
    executable = app_map.get(app_name_lower, app_name)

    try:
        if is_windows:
            subprocess.Popen(["start", executable], shell=True)
        else:
            subprocess.Popen([executable], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return f"Aplikasi '{app_name}' berhasil dibuka."
    except Exception as e:
        logger.error(f"Gagal buka aplikasi '{app_name}': {e}")
        return f"Gagal buka aplikasi '{app_name}'. Coba pastikan nama aplikasi benar."


@tool(risk="medium")
def set_volume(level: int) -> str:
    """
    Set volume sistem (0-100).

    Args:
        level: Level volume 0-100
    """
    level = max(0, min(100, level))
    is_windows = platform.system() == "Windows"

    try:
        if is_windows:
            # Windows: pakai nircmd atau PowerShell
            # Untuk Fase 1, kita skip implementasi penuh (butuh nircmd.exe)
            return f"Volume set ke {level}% (implementasi Windows sederhana: butuh nircmd)"
        else:
            # Linux: pakai amixer atau pactl
            subprocess.run(["amixer", "set", "Master", f"{level}%"], check=True)
            return f"Volume set ke {level}%."
    except Exception as e:
        logger.error(f"Gagal set volume: {e}")
        return f"Gagal set volume. Error: {e}"


@tool(risk="low")
def set_timer(duration_minutes: int, label: str = "Timer") -> str:
    """
    Set timer/alarm.

    Args:
        duration_minutes: Durasi dalam menit
        label: Label timer (opsional)
    """
    if duration_minutes <= 0:
        return "Durasi timer harus lebih dari 0 menit."

    # Untuk Fase 1, kita hanya simpan. Fase 3 akan implement betulan dengan notifikasi TTS
    timer_id = f"timer_{len(_timers) + 1}"
    target_time = datetime.now() + timedelta(minutes=duration_minutes)

    # Store timer info (dummy untuk Fase 1)
    _timers[timer_id] = {
        "label": label,
        "target": target_time,
        "duration": duration_minutes,
    }

    return f"Timer '{label}' diset untuk {duration_minutes} menit (akan bunyi di Fase 3)."


@tool(risk="low")
def list_timers() -> str:
    """List semua timer yang aktif."""
    if not _timers:
        return "Tidak ada timer aktif."

    lines = ["Timer aktif:"]
    for tid, info in _timers.items():
        remaining = (info["target"] - datetime.now()).total_seconds() / 60
        if remaining > 0:
            lines.append(f"- {info['label']}: {remaining:.1f} menit lagi")

    return "\n".join(lines) if len(lines) > 1 else "Tidak ada timer aktif."


@tool(risk="low")
def clear_timers() -> str:
    """Hapus semua timer."""
    count = len(_timers)
    _timers.clear()
    return f"{count} timer dihapus." if count > 0 else "Tidak ada timer untuk dihapus."