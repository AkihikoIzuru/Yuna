"""Icon generator untuk system tray menggunakan Pillow."""

import os
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


# Color palette for different statuses
STATUS_COLORS = {
    "idle": "#00f0ff",      # cyan
    "listening": "#ffaa00",  # orange
    "thinking": "#ff00aa",   # magenta
    "speaking": "#00ff88",   # green
    "error": "#ff0044",      # red
    "muted": "#888888",      # gray
}


def create_tray_icon(status: str = "idle", size: int = 64) -> Image.Image:
    """
    Create a tray icon image for the given status.

    Args:
        status: One of 'idle', 'listening', 'thinking', 'speaking', 'error', 'muted'
        size: Icon size in pixels (default 64)

    Returns:
        PIL Image
    """
    color = STATUS_COLORS.get(status, STATUS_COLORS["idle"])
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle
    margin = 4
    draw.ellipse([margin, margin, size - margin, size - margin],
                 fill=(10, 14, 26, 230), outline=color, width=2)

    # Central core
    core_margin = size // 3
    draw.ellipse([core_margin, core_margin, size - core_margin, size - core_margin],
                 fill=color)

    # Status-specific accents
    if status == "listening":
        # Wave lines on sides
        wave_color = (255, 255, 255, 200)
        for i in range(3):
            x = size // 2 + 12 + i * 6
            draw.rectangle([x, size // 2 - 15 + i * 5, x + 3, size // 2 + 15 - i * 5],
                          fill=wave_color)
            x = size // 2 - 15 - i * 6
            draw.rectangle([x, size // 2 - 15 + i * 5, x + 3, size // 2 + 15 - i * 5],
                          fill=wave_color)

    elif status == "speaking":
        # Sound waves
        wave_color = (255, 255, 255, 200)
        for i in range(3):
            r = 18 + i * 8
            draw.arc([size // 2 - r, size // 2 - r, size // 2 + r, size // 2 + r],
                    start=-45, end=-135, fill=wave_color, width=3)

    elif status == "thinking":
        # Gear/cog icon
        cog_color = (255, 255, 255, 220)
        cx, cy = size // 2, size // 2
        # Draw simple gear teeth
        for angle in range(0, 360, 45):
            import math
            x1 = cx + int(18 * math.cos(math.radians(angle)))
            y1 = cy + int(18 * math.sin(math.radians(angle)))
            x2 = cx + int(24 * math.cos(math.radians(angle)))
            y2 = cy + int(24 * math.sin(math.radians(angle)))
            draw.line([x1, y1, x2, y2], fill=cog_color, width=3)

    elif status == "error":
        # Exclamation mark
        draw.text((size // 2 - 4, size // 2 - 10), "!", fill=(255, 255, 255, 255),
                 font_size=24, anchor="mm")

    elif status == "muted":
        # Slash through mic
        draw.line([size // 2 - 15, size // 2 + 15, size // 2 + 15, size // 2 - 15],
                 fill=(255, 100, 100, 255), width=3)

    return img


def save_icons(output_dir: Optional[Path] = None):
    """Save all status icons to output directory."""
    if output_dir is None:
        output_dir = Path.cwd() / "yuna" / "app" / "icons"

    output_dir.mkdir(parents=True, exist_ok=True)

    for status in STATUS_COLORS.keys():
        for size in [16, 32, 48, 64]:
            img = create_tray_icon(status, size)
            filename = output_dir / f"tray_{status}_{size}.png"
            img.save(filename)
            print(f"Saved: {filename}")

    print(f"All icons saved to {output_dir}")


if __name__ == "__main__":
    save_icons()
