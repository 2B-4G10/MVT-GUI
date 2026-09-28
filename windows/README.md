# MVT for Windows: developer notes

The user guide is in the [main README](../README.md#windows).

MVT for Windows is a portable app: a folder with the official Python for
Windows, MVT and Qt, and nothing to install. It offers the same screens and
commands as the Mac app and runs MVT the same way.

## How it avoids antivirus and SmartScreen warnings

- The app is started by `MVT for Windows.exe`, which is python.org's signed
  `pythonw.exe`, renamed. Renaming keeps the Python Software Foundation's
  signature, so SmartScreen and Microsoft Defender see a well-known file.
  `launcher/sitecustomize.py` makes it open the app.
- MVT runs through the signed `python.exe`, not through the unsigned
  `mvt-ios.exe` wrappers pip makes (these are deleted).
- Qt's DLLs are signed by The Qt Company. The only unsigned binaries are the
  extension modules of PyPI packages (cryptography, pydantic, pycryptodome…),
  the same files every `pip install mvt` gets.
- Nothing is packed, compressed into an executable or self-extracting (the
  PyInstaller approach that antivirus software often flags). The app needs no
  administrator rights and doesn't write to the registry.

Signing the unsigned modules would need a code-signing certificate. That is
only needed for PCs with Smart App Control on.

## Layout

- `mvtwin/commands.py`: the commands and their options, and how a form turns
  into arguments (like `MVTCommand.swift` and `CommandForm.swift`).
- `mvtwin/environment.py`: where the runtime and data are, and how MVT is run.
- `mvtwin/indicators.py`: the indicator sources and downloads.
- `mvtwin/runner.py`: runs MVT and streams its output.
- `mvtwin/pages.py`, `widgets.py`, `app.py`: the screens (PySide6).
- `launcher/sitecustomize.py`: opens the app from `MVT for Windows.exe`.
- `scripts/build_portable.py`: builds the folder and its zip.
- `tests/`: `test_core.py` checks the commands against
  `macos/scripts/check_cli_contract.py` and the Mac app; `test_app.py` opens
  the window and runs a real check.

To add an MVT option, add it to both apps and to `check_cli_contract.py`;
the tests fail if the Windows app passes a flag the contract doesn't check.

## Run it from a checkout

On Windows, macOS or Linux, with Python 3.10 or newer:

```
pip install . PySide6-Essentials pytest   # from the repository root
cd windows
python -m mvtwin
python -m pytest
```

It opens on a given screen like the Mac app does:
`python -m mvtwin -startScreen results -resultsFolder <path>`. Screens:
`setup`, `indicators`, `results`, or a command name such as
`iosCheckBackup` (with `-inputPath` and `-outputPath`). `-appearance dark`
and `-screenshot file.png` are also available.

## Build it

```
pip install pefile
python windows/scripts/build_portable.py --version 3.1.0
```

This writes `dist/MVT for Windows/` and `dist/MVT-for-Windows-3.1.0.zip`. On
Windows it also compiles `.pyc` files for a faster start. The script checks
that every DLL the app loads is in the folder or part of Windows, and that
the executables are signed. Versions of Python, PySide6 and pip are pinned at
the top of the script; the weekly check reports and applies newer ones.

## Workflows

- **Windows app:** runs the tests on Windows, builds the zip, runs MVT on the
  test backup with the app's own Python and opens the app from its
  executable (the screenshots are saved as an artifact).
- **Release apps** builds this app next to the Mac app.
- **Weekly check** builds it with the newest MVT from PyPI.
