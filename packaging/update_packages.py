# MVT GUI
# Copyright (c) 2026 2B-4G10. All rights reserved.
# Proprietary: use of this file is governed by the MVT GUI End User
# License Agreement in the EULA.md file at the root of this repository.

"""Writes the Homebrew cask and the winget manifests for a release.

    python3 packaging/update_packages.py --version 4.0.2-beta \\
        --mac-zip dist/MVT-GUI-4.0.2-beta-macOS.zip \\
        --windows-zip dist/MVT-for-Windows-4.0.2-beta.zip

Release apps runs it after publishing a release and pushes the result to
the default branch, so that

    brew tap dream1works/mvt-gui https://github.com/Dream1Works/MVT-GUI
    brew install --cask mvt-gui

installs the newest Mac app, and packaging/winget holds manifests ready to
submit to microsoft/winget-pkgs (see packaging/README.md).
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CASK = REPO / "Casks" / "mvt-gui.rb"
WINGET = REPO / "packaging" / "winget"

OWNER = "2B-4G10"
REPOSITORY = "https://github.com/Dream1Works/MVT-GUI"
PACKAGE_ID = "2B-4G10.MVTForWindows"
MANIFEST_VERSION = "1.10.0"
SCHEMA = "https://aka.ms/winget-manifest.{kind}.1.10.0.schema.json"
DESCRIPTION = (
    "A desktop app for the Mobile Verification Toolkit (MVT), which looks for traces of "
    "spyware on iPhones and Android phones. Back up a phone, download indicators, run "
    "checks and read the results without the command line."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def release_url(version: str, name: str) -> str:
    return f"{REPOSITORY}/releases/download/gui-v{version}/{name}"


def cask(version: str, digest: str) -> str:
    return f'''# MVT GUI
# Copyright (c) 2026 2B-4G10. All rights reserved.
# Proprietary: use of this file is governed by the MVT GUI End User
# License Agreement in the EULA.md file at the root of this repository.
#
# Written by packaging/update_packages.py for each release.

cask "mvt-gui" do
  version "{version}"
  sha256 "{digest}"

  url "{REPOSITORY}/releases/download/gui-v#{{version}}/MVT-GUI-#{{version}}-macOS.zip"
  name "MVT GUI"
  desc "Desktop app for the Mobile Verification Toolkit"
  homepage "{REPOSITORY}"

  depends_on macos: ">= :ventura"

  app "MVT-GUI-#{{version}}/MVTGUI.app"

  zap trash: [
    "~/Library/Application Support/MVT GUI",
    "~/Library/Preferences/io.github.mvtgui.MVTGUI.plist",
  ]

  caveats <<~EOS
    If macOS says the app can't be checked for malicious software, open it
    once with right-click > Open, or allow it in System Settings > Privacy &
    Security. Then press Install MVT on its Setup screen.
  EOS
end
'''


def winget_manifests(version: str, digest: str, released: str) -> dict[str, str]:
    """The three files of a winget multi-file manifest."""
    zip_name = f"MVT-for-Windows-{version}.zip"

    def header(kind: str) -> str:
        return (
            f"# yaml-language-server: $schema={SCHEMA.format(kind=kind)}\n"
            f"# Written by packaging/update_packages.py for MVT GUI {version}.\n\n"
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
        + "  - RelativeFilePath: MVT for Windows\\MVT for Windows.exe\n"
        + "    PortableCommandAlias: mvt-gui\n"
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
        + "PackageName: MVT for Windows\n"
        + f"PackageUrl: {REPOSITORY}\n"
        + "License: Proprietary; MVT is under the MVT License 1.1\n"
        + f"LicenseUrl: {REPOSITORY}/blob/main/EULA.md\n"
        + "ShortDescription: Desktop app for the Mobile Verification Toolkit (MVT)\n"
        + f"Description: {DESCRIPTION}\n"
        + "Moniker: mvt-gui\n"
        + "Tags:\n"
        + "".join(f"  - {tag}\n" for tag in ("android", "forensics", "ios", "mvt", "privacy", "security", "spyware"))
        + f"ReleaseNotesUrl: {REPOSITORY}/releases/tag/gui-v{version}\n"
        + "ManifestType: defaultLocale\n"
        + f"ManifestVersion: {MANIFEST_VERSION}\n",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", required=True, help="the release's version, e.g. 4.0.2-beta")
    parser.add_argument("--mac-zip", type=Path, required=True)
    parser.add_argument("--windows-zip", type=Path, required=True)
    parser.add_argument("--date", default=date.today().isoformat(), help="release date (YYYY-MM-DD)")
    args = parser.parse_args()

    CASK.parent.mkdir(parents=True, exist_ok=True)
    CASK.write_text(cask(args.version, sha256(args.mac_zip)))
    print(f"Wrote {CASK.relative_to(REPO)}")

    # Only the newest version is kept here; winget-pkgs keeps the history.
    WINGET.mkdir(parents=True, exist_ok=True)
    for old in WINGET.glob("*.yaml"):
        old.unlink()
    for name, text in winget_manifests(args.version, sha256(args.windows_zip), args.date).items():
        (WINGET / name).write_text(text)
        print(f"Wrote {(WINGET / name).relative_to(REPO)}")


if __name__ == "__main__":
    main()
