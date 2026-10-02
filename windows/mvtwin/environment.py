"""Where things live, and how MVT is run.

In the portable app, MVT is installed in the app's own Python runtime, the
folder that holds python.exe and "MVT for Windows.exe". The app keeps its
settings and MVT's data (downloaded indicators) in a Data folder next to
them, so the whole app can be moved or run from a USB drive. When that
folder can't be written to, it uses %LOCALAPPDATA%\\MVT for Windows instead.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from functools import cache
from importlib import metadata
from pathlib import Path

from .commands import Tool

APP_NAME = "MVT for Windows"

# <root>/app/mvtwin/environment.py in the portable app.
ROOT = Path(__file__).resolve().parents[2]
PORTABLE = (ROOT / "python.exe").is_file() and any(ROOT.glob("python3*._pth"))

PYPI_URL = "https://pypi.org/pypi/mvt/json"

MODULES = {Tool.IOS: "mvt.ios", Tool.ANDROID: "mvt.android", Tool.COMMON: "mvt.cli"}


def _writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".write-test"
        probe.write_text("")
        probe.unlink()
        return True
    except OSError:
        return False


@cache
def data_folder() -> Path:
    """The app's settings and MVT's data."""
    if override := os.environ.get("MVTWIN_DATA_FOLDER"):
        return Path(override)
    if PORTABLE and _writable(ROOT / "Data"):
        return ROOT / "Data"
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / APP_NAME


def mvt_data_folder() -> Path:
    """MVT_DATA_FOLDER for every run: downloaded indicators go in its
    indicators folder, which every check loads automatically."""
    return data_folder() / "mvt"


def indicators_folder() -> Path:
    return mvt_data_folder() / "indicators"


def empty_data_folder() -> Path:
    """An always-empty MVT data folder. Pointing MVT_DATA_FOLDER at it stops
    MVT from loading every downloaded indicator file, so that a check uses
    only the files picked for it."""
    return data_folder() / "empty-mvt-data"


def python_executable() -> Path:
    """The console Python that runs MVT (python.exe, not the windowed
    pythonw.exe the app itself runs on, so MVT's output can be read)."""
    if PORTABLE:
        return ROOT / "python.exe"
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe" and (exe.parent / "python.exe").is_file():
        return exe.parent / "python.exe"
    return exe


def mvt_arguments(tool: Tool, arguments: list[str]) -> list[str]:
    """python.exe arguments that run one of MVT's scripts, the same as its
    mvt/mvt-ios/mvt-android commands but without their unsigned .exe
    wrappers."""
    code = f"import sys; sys.argv[0] = {tool.value!r}; from {MODULES[tool]} import main; sys.exit(main())"
    return ["-c", code, *arguments]


def process_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    # MVT prints through rich; keep the output plain and wide enough that
    # log lines don't wrap mid-message.
    env.update(
        NO_COLOR="1",
        TERM="dumb",
        COLUMNS="200",
        PYTHONUNBUFFERED="1",
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        MVT_DATA_FOLDER=str(mvt_data_folder()),
    )
    env.update(extra or {})
    return env


def installed_version() -> str | None:
    try:
        return metadata.version("mvt")
    except metadata.PackageNotFoundError:
        return None


def latest_version(timeout: float = 15) -> str | None:
    """The newest MVT release on PyPI. Blocks; call off the UI thread."""
    try:
        with urllib.request.urlopen(PYPI_URL, timeout=timeout) as response:
            return json.load(response)["info"]["version"]
    except Exception:
        return None


def is_older(installed: str, latest: str) -> bool:
    """Compares release versions like 2026.5.12 numerically. False for
    anything that isn't a plain release (e.g. 0.1.dev148+g777db67)."""

    def parts(version: str) -> list[int] | None:
        pieces = version.split(".")
        return (
            [int(p) for p in pieces]
            if all(re.fullmatch(r"\d+", p) for p in pieces)
            else None
        )

    a, b = parts(installed), parts(latest)
    if not a or not b:
        return False
    width = max(len(a), len(b))
    return a + [0] * (width - len(a)) < b + [0] * (width - len(b))


def can_update_in_place() -> bool:
    """Whether MVT can be updated inside the app's own runtime."""
    return PORTABLE and _writable(ROOT / "Lib" / "site-packages")


def update_arguments() -> list[str]:
    return [
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--no-warn-script-location",
        "--disable-pip-version-check",
        "mvt",
    ]


def remove_script_wrappers() -> None:
    """pip adds mvt.exe, mvt-ios.exe… wrappers to Scripts. The app doesn't
    use them, and unsigned executables are what antivirus software worries
    about, so they're removed."""
    scripts = ROOT / "Scripts"
    if PORTABLE and scripts.is_dir():
        for item in scripts.iterdir():
            try:
                item.unlink()
            except OSError:
                pass
        try:
            scripts.rmdir()
        except OSError:
            pass
