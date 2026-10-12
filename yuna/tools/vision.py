"""Vision tool — describe images from file paths or URLs."""

import logging
import base64
import httpx
from pathlib import Path
from typing import Optional

from yuna.tools.registry import tool

logger = logging.getLogger(__name__)


def _image_to_base64(image_path: str) -> Optional[str]:
    """Convert image file to base64 data URI."""
    try:
        path = Path(image_path)
        if not path.exists():
            return None
        ext = path.suffix.lower()
        mime_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
        }
        mime_type = mime_map.get(ext, 'image/jpeg')
        with open(path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        return f"data:{mime_type};base64,{b64}"
    except Exception as e:
        logger.error(f"Failed to read image: {e}")
        return None


def _fetch_image_base64(url: str) -> Optional[str]:
    """Fetch image from URL and convert to base64."""
    try:
        async def _fetch():
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()
                ext = Path(url.split('?')[0]).suffix.lower()
                mime_map = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp',
                }
                mime_type = mime_map.get(ext, 'image/jpeg')
                b64 = base64.b64encode(resp.content).decode('utf-8')
                return f"data:{mime_type};base64,{b64}"
        import asyncio
        return asyncio.run(_fetch())
    except Exception as e:
        logger.error(f"Failed to fetch image URL: {e}")
        return None


@tool(risk="low")
def describe_image(image_source: str, prompt: str = "Describe this image in detail.") -> str:
    """
    Deskripsi gambar dari path file atau URL.

    Args:
        image_source: Path file gambar lokal atau URL gambar
        prompt: Pertanyaan spesifik tentang gambar (opsional)
    """
    data_uri = None

    # Try as local file path
    local_path = Path(image_source)
    if local_path.exists() and local_path.is_file():
        data_uri = _image_to_base64(str(local_path))
    else:
        # Try as URL
        data_uri = _fetch_image_base64(image_source)

    if data_uri is None:
        return f"Tidak bisa memuat gambar dari '{image_source}'. Pastikan path atau URL valid."

    # Return the data URI for the LLM to process
    # The agent will use this with the vision-capable model
    return f"[IMAGE_DATA:{data_uri[:100]}...]"


@tool(risk="low")
def check_image_exists(image_source: str) -> str:
    """
    Periksa apakah gambar tersedia di path atau URL.

    Args:
        image_source: Path file atau URL gambar
    """
    local_path = Path(image_source)
    if local_path.exists():
        size_kb = local_path.stat().st_size / 1024
        return f"Gambar ditemukan: {image_source} ({size_kb:.1f} KB)"

    # Try URL
    try:
        import httpx
        async def _check():
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.head(image_source, follow_redirects=True)
                return resp.status_code == 200
        is_accessible = False
        try:
            import asyncio
            is_accessible = asyncio.run(_check())
        except Exception:
            pass
        if is_accessible:
            return f"Gambar dapat diakses via URL: {image_source}"
    except Exception:
        pass

    return f"Gambar tidak ditemukan: {image_source}"


# Expose data URI for agent to use (internal)
def get_image_data_uri(image_source: str) -> Optional[str]:
    """Get base64 data URI for an image source (file or URL)."""
    local_path = Path(image_source)
    if local_path.exists():
        return _image_to_base64(str(local_path))
    return _fetch_image_base64(image_source)
