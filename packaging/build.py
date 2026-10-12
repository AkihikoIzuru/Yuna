# Yuna Packaging Script
# Run this from the project root: python packaging/build.py

import os
import sys
import subprocess
from pathlib import Path

def run_build():
    """Build the PyInstaller package."""
    base = Path(__file__).parent.parent
    spec = base / "packaging" / "yuna.spec"

    print("=" * 60)
    print("Building Yuna Desktop App")
    print("=" * 60)

    # Clean previous build
    dist = base / "dist"
    build = base / "build"
    if dist.exists():
        print("Cleaning dist/...")
        subprocess.run(["rm", "-rf", str(dist)])
    if build.exists():
        print("Cleaning build/...")
        subprocess.run(["rm", "-rf", str(build)])

    # Build with PyInstaller
    print("\nRunning PyInstaller...")
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec)
    ]

    result = subprocess.run(cmd, cwd=str(base))

    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("Build successful!")
        print(f"Output: {dist / 'Yuna'}")
        print("=" * 60)
        print("\nTo run:")
        print(f"  {dist / 'Yuna' / 'Yuna.exe'}")
        print("\nFor auto-start:")
        print(f"  Run with: {dist / 'Yuna' / 'Yuna.exe'} --minimized")
    else:
        print("\nBuild failed!")
        sys.exit(1)


if __name__ == "__main__":
    run_build()