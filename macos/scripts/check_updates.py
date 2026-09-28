"""Finds newer versions of the GitHub Actions used by this repository's
workflows and of what the Windows app is built with, and with --apply,
updates them.

A major-version pin (actions/checkout@v7) moves to a newer major version
when the action publishes one; an exact pin (astral-sh/setup-uv@v10.0.0)
moves to the newest release. Pre-releases are ignored.

The Windows app (windows/scripts/build_portable.py) moves to the newest
PySide6 and pip releases and to the newest bug-fix release of its Python.
A newer Python feature release (3.15) is only reported, because MVT's
dependencies may not have Windows wheels for it yet.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / ".github" / "workflows"
WINDOWS_BUILD = REPO / "windows" / "scripts" / "build_portable.py"
USES = re.compile(r"(uses:\s*)([\w.-]+/[\w.-]+)((?:/[\w.-]+)*)@(v\d+(?:\.\d+)*)(?=\s|$)")
RELEASE_TAG = re.compile(r"^v(\d+(?:\.\d+)*)$")


def version(tag: str) -> tuple[int, ...]:
    return tuple(int(part) for part in tag.lstrip("v").split("."))


def release_tags(repo: str) -> set[str]:
    result = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", f"https://github.com/{repo}.git"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    tags = (line.rsplit("refs/tags/", 1)[-1] for line in result.stdout.splitlines())
    return {tag for tag in tags if RELEASE_TAG.match(tag)}


def newer_pin(current: str, tags: set[str]) -> str | None:
    """The pin to move to, in the same style as the current one."""
    if not tags:
        return None
    newest = max(tags, key=version)
    if len(version(current)) == 1:
        major = f"v{version(newest)[0]}"
        # Some actions only publish exact tags; fall back to the newest one.
        target = major if major in tags else newest
        return target if version(newest)[0] > version(current)[0] else None
    return newest if version(newest) > version(current) else None


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def pypi_version(package: str) -> str:
    return json.loads(fetch(f"https://pypi.org/pypi/{package}/json"))["info"]["version"]


def embeddable_pythons() -> list[str]:
    """Python releases with a Windows embeddable package, newest first."""
    listing = fetch("https://www.python.org/ftp/python/").decode()
    versions = sorted(set(re.findall(r'href="(3\.\d+\.\d+)/"', listing)), key=version, reverse=True)
    found = []
    for candidate in versions[:12]:
        request = urllib.request.Request(
            f"https://www.python.org/ftp/python/{candidate}/python-{candidate}-embed-amd64.zip", method="HEAD"
        )
        try:
            with urllib.request.urlopen(request, timeout=30):
                found.append(candidate)
        except OSError:
            pass
    return found


def windows_updates(apply: bool) -> tuple[list[str], list[str]]:
    """Returns (updates, notes) for the Windows app's build."""
    text = WINDOWS_BUILD.read_text()
    pins = dict(re.findall(r'^(PYTHON_VERSION|PYSIDE_VERSION|PIP_VERSION) = "([^"]+)"', text, re.MULTILINE))
    newest = {"PYSIDE_VERSION": pypi_version("PySide6-Essentials"), "PIP_VERSION": pypi_version("pip")}
    notes = []
    pythons = embeddable_pythons()
    current = pins["PYTHON_VERSION"]
    same_minor = [v for v in pythons if version(v)[:2] == version(current)[:2]]
    if same_minor:
        newest["PYTHON_VERSION"] = same_minor[0]
    newer_minor = [v for v in pythons if version(v)[:2] > version(current)[:2]]
    if newer_minor:
        notes.append(f"- Python {newer_minor[0]} is out; the Windows app uses {current}. Move to it by hand "
                     "once MVT's dependencies have Windows wheels for it.")
    updates = []
    names = {"PYTHON_VERSION": "Python", "PYSIDE_VERSION": "PySide6", "PIP_VERSION": "pip"}
    for key, latest in newest.items():
        if version(latest) > version(pins[key]):
            updates.append(f"- `{WINDOWS_BUILD.name}`: {names[key]} {pins[key]} → {latest}")
            text = re.sub(rf'^{key} = "[^"]+"', f'{key} = "{latest}"', text, flags=re.MULTILINE)
    if apply and updates:
        WINDOWS_BUILD.write_text(text)
    return updates, notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="apply the updates")
    args = parser.parse_args()

    cache: dict[str, set[str]] = {}
    updates: list[tuple[str, str, str, str]] = []
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        text = workflow.read_text()

        def bump(match: re.Match) -> str:
            prefix, repo, subpath, current = match.groups()
            if repo not in cache:
                cache[repo] = release_tags(repo)
            target = newer_pin(current, cache[repo])
            if not target:
                return match.group(0)
            updates.append((workflow.name, repo + subpath, current, target))
            return f"{prefix}{repo}{subpath}@{target}"

        updated = USES.sub(bump, text)
        if args.apply and updated != text:
            workflow.write_text(updated)

    lines = [f"- `{name}`: `{action}` {old} → {new}" for name, action, old, new in updates]
    windows, notes = windows_updates(args.apply)
    report = "\n".join(
        ["### GitHub Actions", ""]
        + (lines or [f"All {len(cache)} actions are on their newest versions."])
        + ["", "### Windows app runtime", ""]
        + (windows or ["Python, PySide6 and pip are on their newest versions."])
        + notes
    )
    print(report)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a") as handle:
            handle.write(report + "\n")
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a") as handle:
            handle.write(f"outdated={len(updates) + len(windows)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
