"""
build_exe.py
============
Helper script that invokes PyInstaller to produce a single-file Windows .exe.

IMPORTANT: PyInstaller builds a binary for whatever OS it runs ON. To get a
Windows .exe you must run this script ON WINDOWS (or in a Windows CI runner).
Running it on Linux/macOS will build a Linux/macOS binary, not a .exe.

Usage (on a Windows machine, inside this project's folder, with a venv
where `pip install -r requirements.txt` has been run):

    python build_exe.py

The resulting executable will be at: dist/AI Voice Studio.exe
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

APP_ENTRY = "app.py"
APP_NAME = "AI Voice Studio"


def main() -> None:
    project_dir = Path(__file__).resolve().parent

    voices_json = project_dir / "voices.json"
    if not voices_json.exists():
        print("ERROR: voices.json not found next to build_exe.py", file=sys.stderr)
        sys.exit(1)

    # `--add-data` syntax differs between Windows (`;`) and POSIX (`:`)
    sep = ";" if sys.platform.startswith("win") else ":"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", APP_NAME,
        f"--add-data=voices.json{sep}.",
        APP_ENTRY,
    ]

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=project_dir, check=True)

    print("\nDone. Executable created under dist/.")
    print("Remember: bundle ffmpeg.exe alongside the .exe (or ensure ffmpeg")
    print("is on the end-user's PATH) if you plan to export mp3/flac/aac.")


if __name__ == "__main__":
    main()
