"""Runs one process at a time and streams its output. Mirrors
ProcessRunner.swift."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

from . import environment
from .commands import Invocation, quote
from .logs import Level, classify, strip_ansi, take_complete_lines

MAX_LINES = 50_000


class Runner(QObject):
    line_added = Signal(str, int)  # text, Level
    cleared = Signal()
    state_changed = Signal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.lines: list[tuple[str, Level]] = []
        self.alert_counts: dict[Level, int] = {}
        self.title = ""
        self.last_exit_code: int | None = None
        self._process: QProcess | None = None
        self._buffer = bytearray()
        self._stop_requested = False
        self._on_finished: Callable[[int], None] | None = None

    @property
    def is_running(self) -> bool:
        return self._process is not None

    def clear(self, title: str = "") -> None:
        self.lines.clear()
        self.alert_counts.clear()
        self.last_exit_code = None
        self.title = title
        self.cleared.emit()
        self.state_changed.emit()

    def note(self, text: str, level: Level = Level.COMMAND) -> None:
        self._append(text, level)

    def _append(self, text: str, level: Level) -> None:
        self.lines.append((text, level))
        if len(self.lines) > MAX_LINES:
            del self.lines[: len(self.lines) - MAX_LINES]
        if level.is_alert:
            self.alert_counts[level] = self.alert_counts.get(level, 0) + 1
        self.line_added.emit(text, int(level))

    # MARK: - Running MVT

    def run_mvt(self, invocation: Invocation, title: str, on_finished: Callable[[int], None] | None = None) -> bool:
        """Runs an MVT command with the app-wide options, replacing what the
        console showed before. Never clears the output of a running job."""
        if self.is_running:
            return False
        self.clear(title)
        global_args = []
        if not self.settings.check_updates:
            global_args.append("--disable-update-check")
        if not self.settings.check_indicator_updates:
            global_args.append("--disable-indicator-update-check")
        if self.settings.verbose:
            global_args.append("--verbose")
        env = dict(invocation.environment)
        display_env = ""
        if invocation.only_passed_indicators:
            # An empty data folder keeps MVT from loading every downloaded
            # indicator file; the picked ones are passed with --iocs.
            empty = environment.empty_data_folder()
            empty.mkdir(parents=True, exist_ok=True)
            env["MVT_DATA_FOLDER"] = str(empty)
            display_env = f"MVT_DATA_FOLDER={quote(str(empty))} "
            if "--disable-indicator-update-check" not in global_args:
                global_args.append("--disable-indicator-update-check")
        args = global_args + invocation.arguments
        secrets = "".join(f"{key}=•••• " for key in sorted(invocation.environment))
        display = secrets + display_env + " ".join(quote(a) for a in [invocation.tool.value, *args])
        return self.run(
            environment.python_executable(),
            environment.mvt_arguments(invocation.tool, args),
            env,
            display,
            on_finished,
        )

    def run(
        self,
        program: Path,
        arguments: list[str],
        extra_environment: dict[str, str] | None = None,
        display: str | None = None,
        on_finished: Callable[[int], None] | None = None,
    ) -> bool:
        if self.is_running:
            self.note("Another task is already running.", Level.ERROR)
            return False
        process = QProcess(self)
        process.setProgram(str(program))
        process.setArguments(arguments)
        env = QProcessEnvironment()
        for key, value in environment.process_environment(extra_environment).items():
            env.insert(key, value)
        process.setProcessEnvironment(env)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.setStandardInputFile(QProcess.nullDevice())
        process.readyReadStandardOutput.connect(self._read)
        process.finished.connect(self._finished)
        process.errorOccurred.connect(self._error)

        self.note("> " + (display or " ".join(quote(a) for a in [str(program), *arguments])))
        self._process = process
        self._buffer.clear()
        self._stop_requested = False
        self._on_finished = on_finished
        self.last_exit_code = None
        process.start()
        self.state_changed.emit()
        return True

    def stop(self) -> None:
        process = self._process
        if process is None:
            return
        self._stop_requested = True
        if sys.platform == "win32":
            # Also ends the worker processes decrypt-backup starts.
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(process.processId())],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            process.terminate()

    def _read(self) -> None:
        if self._process is None:
            return
        self._buffer += bytes(self._process.readAllStandardOutput().data())
        for line in take_complete_lines(self._buffer):
            clean = strip_ansi(line)
            self._append(clean, classify(clean))

    def _error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart and self._process is not None:
            self.note(f"Could not start {self._process.program()}: {self._process.errorString()}", Level.ERROR)
            self._done(-1)

    def _finished(self, code: int, status: QProcess.ExitStatus) -> None:
        self._read()
        if self._buffer:
            rest = strip_ansi(self._buffer.decode("utf-8", errors="replace").rstrip("\r"))
            self._buffer.clear()
            self._append(rest, classify(rest))
        if self._stop_requested or status == QProcess.ExitStatus.CrashExit:
            self.note("Stopped.", Level.WARNING)
            code = -1
        elif code == 0:
            self.note("Finished successfully.")
        else:
            self.note(f"Exited with status {code}.", Level.ERROR)
        self._done(code)

    def _done(self, code: int) -> None:
        process, self._process = self._process, None
        if process is not None:
            process.deleteLater()
        self.last_exit_code = code
        callback, self._on_finished = self._on_finished, None
        self.state_changed.emit()
        if callback:
            callback(code)
