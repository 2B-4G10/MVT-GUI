# Telltrace
# Copyright (c) 2026 2B-4G10. All rights reserved.
# Proprietary: use of this file is governed by the Telltrace End User
# License Agreement in the EULA.md file at the root of this repository.

"""Writes the winget manifests for a release.

    python3 packaging/update_packages.py --version 4.0.2-beta \\
        --windows-zip dist/Telltrace-for-Windows-4.0.2-beta.zip

packages.yml runs it after a release is published and pushes the result to
the default branch, so that packaging/winget holds manifests ready to submit
to microsoft/winget-pkgs. The Mac app is sold on the Mac App Store, so there
is no Homebrew cask.
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WINGET = REPO / "packaging" / "winget"

OWNER = "2B-4G10"
REPOSITORY = "https://github.com/Dream1Works/Telltrace"
PACKAGE_ID = "2B-4G10.Telltrace"
MANIFEST_VERSION = "1.10.0"
SCHEMA = "https://aka.ms/winget-manifest.{kind}.1.10.0.schema.json"
DESCRIPTION = (
    "Telltrace looks for traces of spyware on iPhones and Android phones. Back up a phone, "
    "download indicators, run checks and read the results without the command line. "
    "Powered by MVT, the Mobile Verification Toolkit created by Amnesty International's "
    "Security Lab. Telltrace is an independent app, not affiliated with or endorsed by "
    "Amnesty International."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def release_url(version: str, name: str) -> str:
    return f"{REPOSITORY}/releases/download/gui-v{version}/{name}"


def winget_manifests(version: str, digest: str, released: str) -> dict[str, str]:
    """The three files of a winget multi-file manifest."""
    zip_name = f"Telltrace-for-Windows-{version}.zip"

    def header(kind: str) -> str:
        return (
            f"# yaml-language-server: $schema={SCHEMA.format(kind=kind)}\n"
            f"# Written by packaging/update_packages.py for Telltrace {version}.\n\n"
            f"PackageIdentifier: {PACKAGE_ID}\n"
            f"PackageVersion: {version}\n"
        )

    return {
        f"{PACKAGE_ID}.yaml": header("version")
        + "DefaultLocale: en-US\n"
        + "ManifestType: version\n"
        + f"ManifestVersion: {MANIFEST_VERSION}\n",
        f"{PACKAGE_ID}.installer.yaml": header("installer")
        + "InstallerType: zip\n"
        + "NestedInstallerType: portable\n"
        + "NestedInstallerFiles:\n"
        + "  - RelativeFilePath: Telltrace\\Telltrace.exe\n"
        + "    PortableCommandAlias: telltrace\n"
        # The app runs on the Python next to it, so it is started from its
        # folder rather than through a link.
        + "ArchiveBinariesDependOnPath: true\n"
        + "MinimumOSVersion: 10.0.17763.0\n"
        + f"ReleaseDate: {released}\n"
        + "Installers:\n"
        + "  - Architecture: x64\n"
        + f"    InstallerUrl: {release_url(version, zip_name)}\n"
        + f"    InstallerSha256: {digest.upper()}\n"
        + "ManifestType: installer\n"
        + f"ManifestVersion: {MANIFEST_VERSION}\n",
        f"{PACKAGE_ID}.locale.en-US.yaml": header("defaultLocale")
        + "PackageLocale: en-US\n"
        + f"Publisher: {OWNER}\n"
        + f"PublisherUrl: https://github.com/{OWNER}\n"
        + f"PublisherSupportUrl: {REPOSITORY}/issues\n"
        + "PackageName: Telltrace\n"
        + f"PackageUrl: {REPOSITORY}\n"
        + "License: Proprietary; MVT is under the MVT License 1.1\n"
        + f"LicenseUrl: {REPOSITORY}/blob/main/EULA.md\n"
        + "ShortDescription: Check phones for spyware, powered by MVT\n"
        + f"Description: {DESCRIPTION}\n"
        + "Moniker: telltrace\n"
        + "Tags:\n"
        + "".join(f"  - {tag}\n" for tag in ("android", "forensics", "ios", "mvt", "privacy", "security", "spyware"))
        + f"ReleaseNotesUrl: {REPOSITORY}/releases/tag/gui-v{version}\n"
        + "ManifestType: defaultLocale\n"
        + f"ManifestVersion: {MANIFEST_VERSION}\n",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", required=True, help="the release's version, e.g. 4.0.2-beta")
    parser.add_argument("--windows-zip", type=Path, required=True)
    parser.add_argument("--date", default=date.today().isoformat(), help="release date (YYYY-MM-DD)")
    args = parser.parse_args()

    # Only the newest version is kept here; winget-pkgs keeps the history.
    WINGET.mkdir(parents=True, exist_ok=True)
    for old in WINGET.glob("*.yaml"):
        old.unlink()
    for name, text in winget_manifests(args.version, sha256(args.windows_zip), args.date).items():
        (WINGET / name).write_text(text)
        print(f"Wrote {(WINGET / name).relative_to(REPO)}")


if __name__ == "__main__":
    main()
