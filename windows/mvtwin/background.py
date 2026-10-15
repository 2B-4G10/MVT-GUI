"""Runs blocking work (network requests) off the UI thread."""

from __future__ import annotations

import atexit
from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

_alive: set = set()


class _Relay(QObject):
    done = Signal(object, object)  # result, error


class _Task(QRunnable):
    def __init__(self, work: Callable, relay: _Relay):
        super().__init__()
        self.work = work
        self.relay = relay

    def run(self) -> None:
        try:
            result, error = self.work(), None
        except Exception as exc:  # reported to the callback
            result, error = None, exc
        try:
            self.relay.done.emit(result, error)
        except RuntimeError:  # the app quit while this ran
            pass


def run_in_background(
    work: Callable, callback: Callable[[object, Exception | None], None]
) -> None:
    """Calls `work()` on a pool thread, then `callback(result, error)` on the
    UI thread."""
    relay = _Relay()
    _alive.add(relay)

    def finish(result, error):
        _alive.discard(relay)
        callback(result, error)

    relay.done.connect(finish)
    QThreadPool.globalInstance().start(_Task(work, relay))


@atexit.register
def _wait_for_tasks() -> None:
    """Lets running tasks finish before Python exits. PySide deletes the
    remaining Qt objects as the interpreter shuts down, after these handlers
    run, and a task still running then would signal a deleted relay from its
    thread."""
    QThreadPool.globalInstance().waitForDone(20_000)
