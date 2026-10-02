#!/usr/bin/env python3
"""Builds the portable MVT for Windows folder and its zip.

The app runs on the official Python for Windows (the "embeddable package"
from python.org), with MVT and Qt installed from their PyPI wheels:

    MVT for Windows/
      MVT for Windows.exe    Python's pythonw.exe, renamed; opens the app
      python.exe             runs MVT
      python3*.dll, python3*._pth, vcruntime140*.dll
      DLLs/                  Python's extension modules
      Lib/                   Python's standard library and site-packages
      app/                   the app (windows/mvtwin) and its launcher
      LICENSE.txt, NOTICE.txt, README.txt

Every executable and DLL a user starts or Windows loads first is signed:
python.exe and "MVT for Windows.exe" by the Python Software Foundation, and
Qt's DLLs by The Qt Company. Renaming a signed file keeps its signature, so
Windows SmartScreen and Microsoft Defender see the same file as python.org's.
Nothing is packed or self-extracting, which is what makes antivirus software
suspicious of PyInstaller-style apps.

Runs on Windows or, for a quick look, anywhere (then without compiled .pyc
files):

    python windows/scripts/build_portable.py --version 4.0.1
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
APP_NAME = "MVT for Windows"
LAUNCHER = f"{APP_NAME}.exe"

# The newest Python that every locked MVT dependency has Windows wheels for.
# check_updates.py reports newer releases.
PYTHON_VERSION = "3.14.8"
PYSIDE_VERSION = "6.11.2"
PIP_VERSION = "26.2.1"

# Qt pieces the app uses. Everything else in PySide6-Essentials (QML, Quick,
# Designer, tools…) is left out.
QT_KEEP = {
    "__init__.py",
    "_config.py",
    "_git_pyside_version.py",
    "py.typed",
    "QtCore.pyd",
    "QtGui.pyd",
    "QtWidgets.pyd",
    "Qt6Core.dll",
    "Qt6Gui.dll",
    "Qt6Widgets.dll",
    "pyside6.abi3.dll",
    "concrt140.dll",
    "msvcp140.dll",
    "msvcp140_1.dll",
    "msvcp140_2.dll",
    "msvcp140_codecvt_ids.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
}
QT_PLUGINS_KEEP = {
    "platforms/qwindows.dll",
    "styles",
    "imageformats/qico.dll",
    "imageformats/qjpeg.dll",
}

# Windows' own DLLs, which the PE check doesn't expect to find in the folder.
SYSTEM_DLL = re.compile(
    r"^(api-ms-win-|ext-ms-)|^(kernel32|user32|gdi32|advapi32|shell32|ole32|oleaut32|ws2_32|comdlg32|"
    r"shlwapi|version|winmm|imm32|dwmapi|uxtheme|d3d9|d3d11|d3d12|dxgi|dcomp|opengl32|crypt32|bcrypt|"
    r"ncrypt|secur32|setupapi|netapi32|iphlpapi|userenv|wtsapi32|authz|mpr|winspool\.drv|dwrite|"
    r"d2d1|comctl32|rpcrt4|ntdll|msvcrt|ucrtbase|cfgmgr32|powrprof|dxcore|propsys|shcore|"
    r"windowscodecs|winhttp|wininet|dnsapi|mswsock|psapi|dbghelp|userenv|wldap32|normaliz|"
    r"cabinet|oleacc|uiautomationcore|wevtapi|msimg32|hid|imagehlp|bcryptprimitives|icuuc|icuin|icu|"
    r"d3dcompiler_47)\.dll$",
    re.IGNORECASE,
)


def log(message: str) -> None:
    print(f"==> {message}", flush=True)


def download(url: str, cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / url.rsplit("/", 1)[-1]
    if not target.exists():
        log(f"Downloading {url}")
        with urllib.request.urlopen(url, timeout=120) as response:
            target.write_bytes(response.read())
    return target


def python_runtime(root: Path, version: str, cache: Path) -> str:
    """Unpacks the embeddable Python and arranges it; returns e.g. "314"."""
    archive = download(
        f"https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip",
        cache,
    )
    with zipfile.ZipFile(archive) as z:
        z.extractall(root)
    short = "".join(version.split(".")[:2])
    (root / "DLLs").mkdir()
    (root / "Lib").mkdir()
    core = {
        "python.exe",
        "pythonw.exe",
        f"python{short}.dll",
        "python3.dll",
        "vcruntime140.dll",
        "vcruntime140_1.dll",
    }
    for item in list(root.iterdir()):
        if (
            item.is_file()
            and item.suffix.lower() in (".pyd", ".dll")
            and item.name.lower() not in core
        ):
            item.rename(root / "DLLs" / item.name)
    (root / f"python{short}.zip").rename(root / "Lib" / f"python{short}.zip")
    (root / "LICENSE.txt").rename(root / "Lib" / "PYTHON-LICENSE.txt")
    (root / "python.cat").unlink(missing_ok=True)
    # Where Python looks for modules. The ._pth file also keeps out
    # PYTHONPATH and the user's own site-packages, so nothing installed
    # elsewhere on the PC can interfere.
    (root / f"python{short}._pth").write_text(
        f"Lib\\python{short}.zip\nDLLs\nLib\\site-packages\napp\nimport site\n"
    )
    return short


def install_packages(root: Path, short: str, mvt: str) -> None:
    site = root / "Lib" / "site-packages"
    log(f"Installing {mvt}, PySide6-Essentials {PYSIDE_VERSION} and pip {PIP_VERSION}")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "--disable-pip-version-check",
            "--target",
            str(site),
            "--no-compile",
            "--only-binary=:all:",
            "--platform",
            "win_amd64",
            "--python-version",
            f"{short[0]}.{short[1:]}",
            "--implementation",
            "cp",
            mvt,
            f"PySide6-Essentials=={PYSIDE_VERSION}",
            f"pip=={PIP_VERSION}",
        ],
        check=True,
    )
    # pip's .exe wrappers for console scripts: the app doesn't use them.
    for folder in ("bin", "Scripts"):
        shutil.rmtree(site / folder, ignore_errors=True)

    pyside = site / "PySide6"
    for item in pyside.iterdir():
        if item.name == "plugins":
            continue
        if item.name not in QT_KEEP:
            shutil.rmtree(item) if item.is_dir() else item.unlink()
    plugins = pyside / "plugins"
    for group in plugins.iterdir():
        for item in group.iterdir():
            keep = (
                f"{group.name}/{item.name}" in QT_PLUGINS_KEEP
                or group.name in QT_PLUGINS_KEEP
            )
            if not keep:
                shutil.rmtree(item) if item.is_dir() else item.unlink()
        if not any(group.iterdir()):
            group.rmdir()
    for item in (site / "shiboken6").iterdir():
        # C++ AMP, OpenMP and WinRT runtimes: nothing loads them.
        if item.suffix in (".lib", ".pyi") or item.name in (
            "vcamp140.dll",
            "vccorlib140.dll",
            "vcomp140.dll",
        ):
            item.unlink()
    for pattern in ("**/*.pyi", "**/__pycache__"):
        for item in site.glob(pattern):
            shutil.rmtree(item) if item.is_dir() else item.unlink()


def install_app(root: Path, version: str) -> None:
    app = root / "app"
    shutil.copytree(
        REPO / "windows" / "mvtwin",
        app / "mvtwin",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    init = app / "mvtwin" / "__init__.py"
    init.write_text(
        re.sub(r'__version__ = ".*"', f'__version__ = "{version}"', init.read_text())
    )
    icons = REPO / "macos" / "MVTGUI" / "Assets.xcassets" / "AppIcon.appiconset"
    (app / "mvtwin" / "resources").mkdir()
    for size in ("16x16", "32x32", "32x32@2x", "128x128", "256x256"):
        shutil.copy(
            icons / f"icon_{size}.png",
            app / "mvtwin" / "resources" / f"icon_{size.replace('@2x', '_2x')}.png",
        )
    shutil.copy(
        REPO / "windows" / "launcher" / "sitecustomize.py", app / "sitecustomize.py"
    )
    # The app's own executable: Python's signed pythonw.exe.
    (root / "pythonw.exe").rename(root / LAUNCHER)
    shutil.copy(REPO / "LICENSE", root / "LICENSE.txt")
    shutil.copy(REPO / "NOTICE", root / "NOTICE.txt")
    shutil.copy(REPO / "windows" / "README.txt", root / "README.txt")


def compile_bytecode(root: Path) -> None:
    """Compiles .pyc files with the app's own Python, for a faster start.
    Only possible on Windows."""
    if sys.platform != "win32":
        log("Not on Windows: skipped compiling .pyc files")
        return
    log("Compiling .pyc files")
    subprocess.run(
        [
            str(root / "python.exe"),
            "-m",
            "compileall",
            "-q",
            "-j",
            "0",
            str(root / "Lib" / "site-packages"),
            str(root / "app"),
        ],
        check=True,
    )


def check_dlls(root: Path) -> None:
    """Every DLL a binary in the folder imports must be in the folder or be
    part of Windows, so the app can't fail with a missing DLL."""
    import pefile

    binaries = [
        p for p in root.rglob("*") if p.suffix.lower() in (".exe", ".dll", ".pyd")
    ]
    present = {p.name.lower() for p in binaries}
    missing = []
    for path in binaries:
        pe = pefile.PE(str(path), fast_load=True)
        pe.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]]
        )
        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
            name = entry.dll.decode().lower()
            if name not in present and not SYSTEM_DLL.search(name):
                missing.append(f"{path.relative_to(root)} needs {name}")
        pe.close()
    if missing:
        raise SystemExit("Missing DLLs:\n  " + "\n  ".join(sorted(set(missing))))
    log(f"All {len(binaries)} binaries find the DLLs they need")


def signatures(root: Path) -> tuple[list[str], list[str]]:
    """Which binaries carry an Authenticode signature."""
    import pefile

    signed, unsigned = [], []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() in (".exe", ".dll", ".pyd"):
            pe = pefile.PE(str(path), fast_load=True)
            security = pe.OPTIONAL_HEADER.DATA_DIRECTORY[
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_SECURITY"]
            ]
            (signed if security.Size else unsigned).append(str(path.relative_to(root)))
            pe.close()
    return signed, unsigned


def make_zip(root: Path, target: Path) -> None:
    log(f"Writing {target.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(root.rglob("*")):
            z.write(path, Path(root.name) / path.relative_to(root))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--version",
        default=None,
        help="the app's version (default: windows/mvtwin/__init__.py)",
    )
    parser.add_argument(
        "--python",
        default=PYTHON_VERSION,
        help=f"Python version (default {PYTHON_VERSION})",
    )
    parser.add_argument(
        "--mvt",
        default="mvt",
        help='MVT to install: "mvt", "mvt==2026.9.28" or a wheel',
    )
    parser.add_argument("--out", type=Path, default=REPO / "dist", help="output folder")
    parser.add_argument("--cache", type=Path, default=REPO / "build" / "windows-cache")
    parser.add_argument("--no-zip", action="store_true")
    args = parser.parse_args()

    version = (args.version or "").removeprefix("gui-v") or re.search(
        r'__version__ = "(.*)"',
        (REPO / "windows" / "mvtwin" / "__init__.py").read_text(),
    ).group(1)
    root = args.out / APP_NAME
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    short = python_runtime(root, args.python, args.cache)
    install_packages(root, short, args.mvt)
    install_app(root, version)
    compile_bytecode(root)
    check_dlls(root)
    signed, unsigned = signatures(root)
    log(
        f"{len(signed)} signed binaries; {len(unsigned)} unsigned (extension modules of PyPI packages):"
    )
    for name in unsigned:
        print(f"    {name}")
    for name in ("python.exe", LAUNCHER):
        if name not in signed:
            raise SystemExit(f"{name} is not signed")

    size = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
    log(f"{APP_NAME} {version}: {size / 1e6:.0f} MB in {root}")
    if not args.no_zip:
        zip_path = args.out / f"MVT-for-Windows-{version}.zip"
        make_zip(root, zip_path)
        log(
            f"{zip_path.stat().st_size / 1e6:.0f} MB, sha256 {hashlib.sha256(zip_path.read_bytes()).hexdigest()}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
