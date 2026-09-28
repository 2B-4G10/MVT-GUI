"""Severity of MVT's output lines, from the prefix its log handler prints
(MVTLogHandler in src/mvt/common/log.py). Mirrors LogLine.swift."""

from __future__ import annotations

import re
from enum import IntEnum


class Level(IntEnum):
    PLAIN = 0
    COMMAND = 1
    WARNING = 2
    ERROR = 3
    INFO_ALERT = 4
    LOW_ALERT = 5
    MEDIUM_ALERT = 6
    HIGH_ALERT = 7
    CRITICAL_ALERT = 8

    @property
    def is_alert(self) -> bool:
        return self >= Level.INFO_ALERT

    @property
    def alert_name(self) -> str:
        return {
            Level.INFO_ALERT: "Info",
            Level.LOW_ALERT: "Low",
            Level.MEDIUM_ALERT: "Medium",
            Level.HIGH_ALERT: "High",
            Level.CRITICAL_ALERT: "Critical",
        }.get(self, "")


_PREFIXES = [
    ("CRITICAL ALERT", Level.CRITICAL_ALERT),
    ("HIGH ALERT", Level.HIGH_ALERT),
    ("MEDIUM ALERT", Level.MEDIUM_ALERT),
    ("LOW ALERT", Level.LOW_ALERT),
    ("INFO ALERT", Level.INFO_ALERT),
    ("WARNING", Level.WARNING),
    ("ERROR", Level.ERROR),
    ("FATAL", Level.ERROR),
    ("Error:", Level.ERROR),
    ("Traceback", Level.ERROR),
]

# alerts.json levels, most severe first.
ALERT_LEVELS = [
    ("CRITICAL", Level.CRITICAL_ALERT),
    ("HIGH", Level.HIGH_ALERT),
    ("MEDIUM", Level.MEDIUM_ALERT),
    ("LOW", Level.LOW_ALERT),
    ("INFORMATIONAL", Level.INFO_ALERT),
]


def classify(line: str) -> Level:
    for prefix, level in _PREFIXES:
        if line.startswith(prefix):
            return level
    return Level.PLAIN


_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07")


def strip_ansi(text: str) -> str:
    return _ANSI.sub("", text) if "\x1b" in text else text


def take_complete_lines(buffer: bytearray) -> list[str]:
    """Removes the complete lines from `buffer` and returns them decoded. A
    carriage return redraws a line (progress output), so only what ended up
    visible is kept."""
    end = buffer.rfind(b"\n")
    if end < 0:
        return []
    chunk = bytes(buffer[:end])
    del buffer[: end + 1]
    lines = []
    for raw in chunk.split(b"\n"):
        line = raw.decode("utf-8", errors="replace")
        if "\r" in line:
            parts = [p for p in line.split("\r") if p]
            line = parts[-1] if parts else ""
        lines.append(line)
    return lines
