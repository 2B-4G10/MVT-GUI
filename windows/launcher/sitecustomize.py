"""Opens MVT for Windows when "MVT for Windows.exe" is started.

"MVT for Windows.exe" is Python's own pythonw.exe, renamed so that it keeps
the Python Software Foundation's signature, which Windows trusts. Python
imports this file whenever it starts. When the renamed executable is started
without a script, this starts the app in a new process and exits. Every
other start of Python (MVT's runs, pip) is left alone.
"""

import os
import sys


def _open_app() -> None:
    name = os.path.splitext(os.path.basename(sys.executable))[0]
    if name.lower() != "mvt for windows":
        return
    extra = sys.orig_argv[1:]
    if extra[:2] == ["-m", "mvtwin"]:
        return
    import subprocess

    subprocess.Popen([sys.executable, "-m", "mvtwin", *extra], close_fds=True)
    os._exit(0)


_open_app()
