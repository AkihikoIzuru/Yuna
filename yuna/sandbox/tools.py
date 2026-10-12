"""Sandbox tools - coding, file operations, journal within path jail."""

import logging
import json
import subprocess
import sys
import tempfile
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from yuna.tools.registry import tool
from yuna.sandbox.path_jail import get_path_jail

logger = logging.getLogger(__name__)

# Import get_policy locally to avoid circular import
def _get_policy():
    from yuna.safety.policy import get_policy
    return get_policy()

@tool(risk="low")
def journal_entry(title: str, content: str, tags: Optional[List[str]] = None) -> str:
    """
    Tulis entri jurnal harian.

    Args:
        title: Judul entri
        content: Isi jurnal
        tags: Tag-tag opsional (list string)
    """
    jail = get_path_jail()
    journal_dir = jail.create_subdir("journal")

    # Create filename based on date
    date_str = datetime.now().strftime("%Y-%m-%d")
    file_path = journal_dir / f"{date_str}.jsonl"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "title": title,
        "content": content,
        "tags": tags or [],
    }

    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info(f"Journal entry saved: {title}")
        return f"Jurnal '{title}' tersimpan."
    except Exception as e:
        logger.error(f"Failed to save journal: {e}")
        return f"Gagal simpan jurnal: {e}"


@tool(risk="low")
def read_journal(date: Optional[str] = None, limit: int = 10) -> str:
    """
    Baca jurnal.

    Args:
        date: Tanggal format YYYY-MM-DD (None = hari ini)
        limit: Maksimal entri yang dibaca
    """
    jail = get_path_jail()
    journal_dir = jail.jail_root / "journal"

    if not journal_dir.exists():
        return "Belum ada jurnal."

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    file_path = journal_dir / f"{date}.jsonl"

    if not file_path.exists():
        return f"Tidak ada jurnal untuk {date}."

    entries = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))

        # Show last N entries
        entries = entries[-limit:]

        if not entries:
            return f"Jurnal {date} kosong."

        lines = [f"Jurnal {date} ({len(entries)} entri):"]
        for e in entries:
            time_str = e["timestamp"][11:16]  # HH:MM
            tags_str = f" [{', '.join(e['tags'])}]" if e['tags'] else ""
            lines.append(f"  {time_str} - {e['title']}{tags_str}")
            lines.append(f"    {e['content'][:100]}{'...' if len(e['content']) > 100 else ''}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to read journal: {e}")
        return f"Gagal baca jurnal: {e}"


@tool(risk="low")
def list_journal_dates() -> str:
    """List tanggal-tanggal yang punya jurnal."""
    jail = get_path_jail()
    journal_dir = jail.jail_root / "journal"

    if not journal_dir.exists():
        return "Belum ada jurnal."

    files = sorted(journal_dir.glob("*.jsonl"))
    if not files:
        return "Belum ada jurnal."

    dates = [f.stem for f in files]
    return f"Tanggal jurnal: {', '.join(dates)}"


# ========== File Operations (within jail) ==========

@tool(risk="medium")
def write_file(path: str, content: str) -> str:
    """
    Tulis file di dalam path jail.

    Args:
        path: Path relatif dari jail root (contoh: 'projects/hello.py')
        content: Isi file
    """
    jail = get_path_jail()
    try:
        safe_path = jail.resolve_safe(path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)

        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"File written: {safe_path}")
        return f"File '{path}' tertulis ({len(content)} karakter)."
    except ValueError as e:
        return f"Gagal: {e}"
    except Exception as e:
        logger.error(f"Failed to write file: {e}")
        return f"Gagal tulis file: {e}"


@tool(risk="low")
def read_file(path: str) -> str:
    """
    Baca file dari dalam path jail.

    Args:
        path: Path relatif dari jail root
    """
    jail = get_path_jail()
    try:
        safe_path = jail.resolve_safe(path)

        if not safe_path.exists():
            return f"File '{path}' tidak ditemukan."

        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()

        return content
    except ValueError as e:
        return f"Gagal: {e}"
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        return f"Gagal baca file: {e}"


@tool(risk="low")
def list_files(path: str = ".") -> str:
    """
    List file di dalam path jail.

    Args:
        path: Path relatif dari jail root (default: root jail)
    """
    jail = get_path_jail()
    try:
        safe_path = jail.resolve_safe(path)

        if not safe_path.exists():
            return f"Path '{path}' tidak ditemukan."

        items = []
        for item in sorted(safe_path.iterdir()):
            if item.is_dir():
                items.append(f"📁 {item.name}/")
            else:
                size = item.stat().st_size
                items.append(f"📄 {item.name} ({size} bytes)")

        if not items:
            return f"Direktori '{path}' kosong."

        return f"Isi '{path}':\n" + "\n".join(items)
    except ValueError as e:
        return f"Gagal: {e}"
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        return f"Gagal list file: {e}"


@tool(risk="medium")
def delete_file(path: str) -> str:
    """
    Hapus file di dalam path jail.

    Args:
        path: Path relatif dari jail root
    """
    jail = get_path_jail()
    try:
        safe_path = jail.resolve_safe(path)

        if not safe_path.exists():
            return f"File '{path}' tidak ditemukan."

        if safe_path.is_dir():
            safe_path.rmdir()  # only empty dirs
            return f"Direktori '{path}' dihapus."
        else:
            safe_path.unlink()
            return f"File '{path}' dihapus."
    except ValueError as e:
        return f"Gagal: {e}"
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        return f"Gagal hapus file: {e}"


# ========== Python Code Execution (sandboxed) ==========

def _run_python_sandboxed(code: str, timeout: int = 30) -> tuple[str, int]:
    """Run Python code in a sandboxed subprocess."""
    jail = get_path_jail()

    # Create a temp file in the jail
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", dir=jail.get_jail_root(), delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        temp_path = f.name

    try:
        # Run with restricted environment
        env = os.environ.copy()
        env["PYTHONPATH"] = ""
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(jail.get_jail_root()),
            env=env,
        )
        return result.stdout + result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return f"Timeout after {timeout} seconds", 124
    except Exception as e:
        return f"Execution error: {e}", 1
    finally:
        # Cleanup
        try:
            Path(temp_path).unlink()
        except Exception:
            pass


@tool(risk="high")
def run_python(code: str, timeout: int = 30) -> str:
    """
    Jalankan kode Python di sandbox (dibatasi di path jail).

    Args:
        code: Kode Python yang akan dijalankan
        timeout: Timeout dalam detik (default 30)
    """
    # Log execution attempt
    logger.info(f"Python sandbox execution requested ({len(code)} chars)")

    output, returncode = _run_python_sandboxed(code, timeout)

    if returncode == 0:
        return f"✅ Output:\n{output}" if output else "✅ Selesai (tidak ada output)"
    elif returncode == 124:
        return f"⏱️ Timeout ({timeout}s)"
    else:
        return f"❌ Error (exit {returncode}):\n{output}"


@tool(risk="high")
def run_shell(command: str, timeout: int = 30) -> str:
    """
    Jalankan command shell di sandbox (dibatasi di path jail & allowlist).

    Args:
        command: Command yang akan dijalankan
        timeout: Timeout dalam detik
    """
    jail = get_path_jail()
    policy = get_policy()

    # Check allowlist
    if not policy.is_shell_allowed(command.split()[0]):
        allowed = ", ".join(sorted(policy._shell_allowlist)) or "kosong"
        return f"Command tidak diizinkan. Allowlist: {allowed}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(jail.get_jail_root()),
        )
        output = result.stdout + result.stderr
        if result.returncode == 0:
            return f"✅ Output:\n{output}" if output else "✅ Selesai"
        else:
            return f"❌ Error (exit {result.returncode}):\n{output}"
    except subprocess.TimeoutExpired:
        return f"⏱️ Timeout ({timeout}s)"
    except Exception as e:
        return f"❌ Error: {e}"


# ========== Project Management ==========

@tool(risk="low")
def list_projects() -> str:
    """List proyek di dalam jail."""
    jail = get_path_jail()
    projects_dir = jail.create_subdir("projects")

    items = []
    for item in sorted(projects_dir.iterdir()):
        if item.is_dir():
            files = list(item.rglob("*"))
            py_files = [f for f in files if f.suffix == ".py"]
            items.append(f"📁 {item.name}/ ({len(py_files)} .py files)")

    if not items:
        return "Belum ada proyek. Buat folder di 'projects/'"

    return "Proyek:\n" + "\n".join(items)


@tool(risk="medium")
def create_project(name: str, template: str = "python") -> str:
    """
    Buat proyek baru.

    Args:
        name: Nama proyek
        template: Template ('python', 'empty')
    """
    jail = get_path_jail()
    projects_dir = jail.create_subdir("projects")
    project_dir = projects_dir / name

    if project_dir.exists():
        return f"Proyek '{name}' sudah ada."

    project_dir.mkdir(parents=True, exist_ok=True)

    if template == "python":
        # Create basic Python project structure
        (project_dir / "main.py").write_text("# Main entry point\nprint('Halo dari proyek baru!')\n", encoding="utf-8")
        (project_dir / "README.md").write_text(f"# {name}\n\nProyek Python baru.\n", encoding="utf-8")
        (project_dir / "requirements.txt").write_text("# Dependencies\n", encoding="utf-8")

    return f"Proyek '{name}' dibuat di projects/{name}/"