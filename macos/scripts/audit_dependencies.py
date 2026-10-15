"""Audits the Python packages this fork depends on for known vulnerabilities.

Two sets are checked with pip-audit:

- What the Windows app ships: the newest MVT on PyPI with the PySide6 and
  pip that windows/scripts/build_portable.py pins, resolved for 64-bit
  Windows the way the build installs them.
- MVT's locked packages (uv.lock), which come from upstream.

Only a vulnerability this fork can fix fails the run: one in a package the
Windows build pins (PySide6 and pip). Everything else is reported as a
warning. uv.lock and MVT's own pins belong to upstream, so their fixes
arrive with the daily sync and the next MVT release, and the Windows app
picks up every other fix when it is next built.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WINDOWS_BUILD = REPO / "windows" / "scripts" / "build_portable.py"
# The packages the Windows build pins, PySide6's shiboken6 included.
FORK_PINNED = {"pyside6-essentials", "shiboken6", "pip"}


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def run(command: list[str], **kwargs) -> str:
    return subprocess.run(
        command, capture_output=True, text=True, check=True, **kwargs
    ).stdout


def windows_requirements() -> str:
    text = WINDOWS_BUILD.read_text()
    pins = dict(
        re.findall(
            r'^(PYTHON_VERSION|PYSIDE_VERSION|PIP_VERSION) = "([^"]+)"',
            text,
            re.MULTILINE,
        )
    )
    python = ".".join(pins["PYTHON_VERSION"].split(".")[:2])
    wanted = f"mvt\nPySide6-Essentials=={pins['PYSIDE_VERSION']}\npip=={pins['PIP_VERSION']}\n"
    return run(
        [
            "uv",
            "pip",
            "compile",
            "-",
            "--quiet",
            "--no-header",
            "--no-annotate",
            "--only-binary",
            ":all:",
            "--python-platform",
            "x86_64-pc-windows-msvc",
            "--python-version",
            python,
        ],
        input=wanted,
    )


def locked_requirements() -> str:
    return run(
        [
            "uv",
            "export",
            "--locked",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements-txt",
        ],
        cwd=REPO,
    )


def audit(requirements: str) -> list[dict]:
    """pip-audit's findings, retried because it depends on PyPI's API."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
        handle.write(requirements)
    error = ""
    for attempt in range(4):
        if attempt:
            time.sleep(15 * attempt)
        result = subprocess.run(
            [
                "uvx",
                "pip-audit",
                "--disable-pip",
                "--no-deps",
                "--progress-spinner",
                "off",
                "--format",
                "json",
                "-r",
                handle.name,
            ],
            capture_output=True,
            text=True,
        )
        try:
            return json.loads(result.stdout)["dependencies"]
        except (json.JSONDecodeError, KeyError):
            error = result.stderr.strip()
    raise RuntimeError(f"pip-audit didn't finish:\n{error}")


def findings(dependencies: list[dict]) -> tuple[list[tuple[str, str]], list[str]]:
    """([(package, vulnerability)], [packages pip-audit couldn't check])."""
    vulns, skipped = [], []
    for dependency in dependencies:
        name = dependency["name"]
        if reason := dependency.get("skip_reason"):
            skipped.append(f"{name}: {reason}")
        for vuln in dependency.get("vulns", []):
            fix = ", ".join(vuln["fix_versions"]) or "none yet"
            line = f"{name} {dependency['version']}: {vuln['id']} (fixed in {fix})"
            vulns.append((normalize(name), line))
    # pip-audit can list an advisory twice under its aliases.
    return list(dict.fromkeys(vulns)), skipped


def main() -> int:
    report = ["### Dependency audit", ""]
    errors, warnings = [], []

    shipped = audit(windows_requirements())
    vulns, skipped = findings(shipped)
    mvt = next((d["version"] for d in shipped if normalize(d["name"]) == "mvt"), "?")
    report.append(f"**Windows app** (MVT {mvt} from PyPI, for Windows):")
    for name, line in vulns:
        if name in FORK_PINNED:
            errors.append(f"{line}. Move its pin in {WINDOWS_BUILD.name}.")
        else:
            warnings.append(
                f"Windows app: {line}. MVT pins it, so the fix comes with MVT."
            )
    warnings += [f"Windows app: couldn't check {line}" for line in skipped]
    lines = [line for _, line in vulns] + skipped
    report += [f"- {line}" for line in lines] or ["- No known vulnerabilities."]

    vulns, skipped = findings(audit(locked_requirements()))
    report += ["", "**uv.lock** (upstream's; fixes arrive with the daily sync):"]
    warnings += [f"uv.lock: {line}" for _, line in vulns]
    warnings += [f"uv.lock: couldn't check {line}" for line in skipped]
    lines = [line for _, line in vulns] + skipped
    report += [f"- {line}" for line in lines] or ["- No known vulnerabilities."]

    print("\n".join(report))
    for line in warnings:
        print(f"::warning::{line}")
    for line in errors:
        print(f"::error::{line}")
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a") as handle:
            handle.write("\n".join(report) + "\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
