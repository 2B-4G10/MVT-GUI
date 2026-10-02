"""The official lists of public indicators, and the downloaded files MVT
loads automatically. Mirrors macos/MVTGUI/Services/IndicatorsIndex.swift.

Network functions block; the app calls them off the UI thread.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from . import environment

# The index `mvt download-iocs` reads (IndicatorsUpdates in updates.py).
INDEX_URL = (
    "https://raw.githubusercontent.com/mvt-project/mvt-indicators/main/indicators.yaml"
)


@dataclass(frozen=True)
class SourceRepository:
    owner: str
    repo: str
    branch: str
    organization: str

    @property
    def web_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}"


# The repositories public indicators come from. MVT's index lists most of
# their files; any STIX2 file it doesn't list is added from here.
SOURCE_REPOSITORIES = [
    SourceRepository("mvt-project", "mvt-indicators", "main", "MVT project"),
    SourceRepository(
        "AmnestyTech", "investigations", "master", "Amnesty International"
    ),
    SourceRepository("AssoEchap", "stalkerware-indicators", "master", "Echap"),
]

# STIX2 files in the source repositories that MVT's index doesn't list, used
# when GitHub can't be asked (it allows 60 anonymous listings an hour). Keep
# in step with IndicatorsIndex.knownExtraFiles in the macOS app.
KNOWN_EXTRA_FILES = [
    ("AmnestyTech/investigations", "2021-12-16_cytrox/cytrox.stix2"),
]


@dataclass(frozen=True)
class IndicatorSet:
    name: str
    download_url: str
    sources: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    # Listed in MVT's own index, so `mvt download-iocs` fetches it too.
    in_mvt_index: bool = True

    @property
    def local_file_name(self) -> str:
        """The name MVT gives this set when it downloads it
        (download_remote_ioc in src/mvt/common/updates.py), so a set
        downloaded here and by `mvt download-iocs` ends up in one file."""
        # Python's str.lstrip("https://") strips any of those characters.
        return self.download_url.lstrip("https://").replace("/", "_")

    @property
    def local_path(self) -> Path:
        return environment.indicators_folder() / self.local_file_name


def _get(url: str, timeout: float = 30) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": environment.APP_NAME})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def parse_index(text: str) -> list[IndicatorSet]:
    """Reads indicators.yaml and resolves download URLs the way
    IndicatorsUpdates.update() does.

    The file is a flat list of entries with `type`, `name`, `sources`,
    `references` and either a `github` block or a `download_url`; this reads
    exactly that shape (like the macOS app). The app doesn't load PyYAML
    itself: a library the app has loaded can't be replaced while it runs, and
    that would stop Update MVT from updating it.
    """
    entries: list[dict] = []
    section = None
    for raw in text.splitlines():
        if raw.lstrip(" ").startswith("#"):
            continue
        line = raw.split(" #", 1)[0].rstrip(" \t")
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if body == "indicators:":
            continue
        if body.startswith("-") and indent <= 2:
            entries.append(
                {"fields": {}, "github": {}, "sources": [], "references": []}
            )
            section = None
            body = body[1:].strip()
            if not body:
                continue
            indent = 4
        if not entries:
            continue
        entry = entries[-1]
        if body.startswith("- "):
            if section in ("sources", "references"):
                entry[section].append(_unquote(body[2:]))
            continue
        if ":" not in body:
            continue
        key, value = body.split(":", 1)
        key, value = key.strip(), _unquote(value)
        if indent <= 4:
            section = None if value else key
            if value:
                entry["fields"][key] = value
        elif section == "github":
            entry["github"][key] = value

    sets = []
    for entry in entries:
        fields, github = entry["fields"], entry["github"]
        if fields.get("type") == "github":
            owner, repo, path = (
                github.get("owner"),
                github.get("repo"),
                github.get("path"),
            )
            if not (owner and repo and path):
                continue
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/{github.get('branch') or 'main'}/{path}"
        else:
            url = fields.get("download_url", "")
        if not url.startswith("https://"):
            continue
        sets.append(
            IndicatorSet(
                name=fields.get("name") or url.rsplit("/", 1)[-1],
                download_url=url,
                sources=tuple(entry["sources"]),
                references=tuple(entry["references"]),
            )
        )
    return sets


def fetch_index() -> list[IndicatorSet]:
    return parse_index(_get(INDEX_URL).decode("utf-8"))


def display_name(path: str) -> str:
    """ "2021-12-16_cytrox/cytrox.stix2" → "Cytrox indicators (2021-12-16)"."""
    folder = os.path.dirname(path)
    words = (folder or os.path.basename(path)).replace(".stix2", "").split("_")
    date = None
    if words and re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", words[0]):
        date = words.pop(0)
    title = " ".join(w[:1].upper() + w[1:] for w in words if w)
    return f"{title or 'Unnamed'} indicators" + (f" ({date})" if date else "")


def _stix2_paths(source: SourceRepository) -> list[str]:
    url = f"https://api.github.com/repos/{source.owner}/{source.repo}/git/trees/{source.branch}?recursive=1"
    tree = json.loads(_get(url)).get("tree") or []
    return [
        item["path"]
        for item in tree
        if str(item.get("path", "")).lower().endswith(".stix2")
    ]


def extra_sets(known: list[IndicatorSet]) -> list[IndicatorSet]:
    """Every STIX2 file in the source repositories that isn't in `known`,
    named after its folder."""
    known_urls = {s.download_url for s in known}
    found: list[tuple[SourceRepository, str]] = []
    listed_all = True
    for source in SOURCE_REPOSITORIES:
        try:
            found += [(source, path) for path in _stix2_paths(source)]
        except Exception:
            listed_all = False
    if not listed_all:
        for repo, path in KNOWN_EXTRA_FILES:
            source = next(
                s for s in SOURCE_REPOSITORIES if f"{s.owner}/{s.repo}" == repo
            )
            if (source, path) not in found:
                found.append((source, path))
    sets = []
    for source, path in found:
        url = f"https://raw.githubusercontent.com/{source.owner}/{source.repo}/{source.branch}/{path}"
        if url in known_urls:
            continue
        folder = os.path.dirname(path)
        sets.append(
            IndicatorSet(
                name=display_name(path),
                download_url=url,
                sources=(source.organization,),
                references=(f"{source.web_url}/tree/{source.branch}/{folder}",),
                in_mvt_index=False,
            )
        )
    return sets


def download(indicator_set: IndicatorSet) -> Path:
    data = _get(indicator_set.download_url)
    target = indicator_set.local_path
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    partial.write_bytes(data)
    os.replace(partial, target)
    return target


def downloaded_files() -> list[Path]:
    """Indicator files MVT loads automatically: only .stix2 files in the
    folder (_load_downloaded_indicators in src/mvt/common/indicators.py)."""
    folder = environment.indicators_folder()
    if not folder.is_dir():
        return []
    return sorted(
        (
            p
            for p in folder.iterdir()
            if p.suffix.lower() == ".stix2" and not p.name.startswith(".")
        ),
        key=lambda p: p.name,
    )


def import_file(source: Path) -> Path:
    """Copies a STIX2 file into the indicators folder so every check uses it.
    MVT only loads files ending in .stix2 from there."""
    name = source.name if source.suffix.lower() == ".stix2" else source.name + ".stix2"
    target = environment.indicators_folder() / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target


@dataclass
class IndicatorCatalog:
    """The sets offered for download, once loaded."""

    sets: list[IndicatorSet] = field(default_factory=list)
    error: str | None = None

    def load(self) -> None:
        loaded: list[IndicatorSet] = []
        try:
            loaded = fetch_index()
            self.error = None
        except Exception as exc:
            self.error = f"Couldn't load MVT's official list: {exc}"
        loaded += extra_sets(loaded)
        self.sets = loaded

    def display_name(self, path: Path) -> str:
        """A readable name for a downloaded file: its set's name when it came
        from the official list."""
        for s in self.sets:
            if s.local_file_name == path.name:
                return s.name
        return path.stem
