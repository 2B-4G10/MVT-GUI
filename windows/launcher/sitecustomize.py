"""Opens MVT for Windows when "MVT for Windows.exe" is started.

"MVT for Windows.exe" is Python's own pythonw.exe, renamed so that it keeps
the Python Software Foundation's signature, which Windows trusts. Python
imports this file whenever it starts. When the renamed executable is started
without a script, this starts the app in a new process and exits. Every
other start of Python (MVT's runs, pip) is left alone.

Python reads options that start with "-" before this runs, so the app's own
options (-startScreen…) only work through python.exe -m mvtwin.
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
    try:
        import subprocess

        subprocess.Popen([sys.executable, "-m", "mvtwin", *extra], close_fds=True)
    except Exception:
        # There's no console to report to: leave the details next to the app.
        import traceback

        try:
            with open(
                os.path.join(os.path.dirname(sys.executable), "launch-error.log"), "w"
            ) as log:
                traceback.print_exc(file=log)
        except OSError:
            pass
    os._exit(0)


_open_app()
