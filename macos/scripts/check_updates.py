"""Finds newer versions of the GitHub Actions used by this repository's
workflows, and with --apply, updates the workflows to them.

A major-version pin (actions/checkout@v7) moves to a newer major version
when the action publishes one; an exact pin (astral-sh/setup-uv@v10.0.0)
moves to the newest release. Pre-releases are ignored.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="update the workflows")
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
    report = "\n".join(
        ["### GitHub Actions", ""]
        + (lines or [f"All {len(cache)} actions are on their newest versions."])
    )
    print(report)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a") as handle:
            handle.write(report + "\n")
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a") as handle:
            handle.write(f"outdated={len(updates)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
