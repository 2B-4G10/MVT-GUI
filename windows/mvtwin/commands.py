"""The MVT commands the app offers, and how a form turns into a command line.

Mirrors macos/MVTGUI/Models/MVTCommand.swift and CommandForm.swift. The
flags each command passes are checked against MVT by
macos/scripts/check_cli_contract.py (EXPECTED_OPTIONS), and
windows/tests/test_commands.py checks that this file only passes flags listed
there.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from enum import Enum


class Tool(str, Enum):
    """The three console scripts MVT installs."""

    IOS = "mvt-ios"
    ANDROID = "mvt-android"
    COMMON = "mvt"


class InputKind(Enum):
    FOLDER = "folder"
    FILE = "file"
    FILE_OR_FOLDER = "file_or_folder"
    NONE = "none"


class Option(Enum):
    IOCS = "iocs"  # -i/--iocs PATH (repeatable)
    OUTPUT = "output"  # -o/--output PATH
    FAST = "fast"  # -f/--fast
    HASHES = "hashes"  # -H/--hashes
    MODULE = "module"  # -m/--module NAME
    LIST_MODULES = "list_modules"  # -l/--list-modules
    TIMEZONE = "timezone"  # -t/--timezone TZ
    IOS_PASSWORD = "ios_password"  # MVT_IOS_BACKUP_PASSWORD, or -k/--key-file
    ANDROID_PASSWORD = "android_password"  # MVT_ANDROID_BACKUP_PASSWORD
    VIRUSTOTAL = "virustotal"  # -V/--virustotal, -d/--delay, MVT_VT_API_KEY
    DESTINATION = "destination"  # -d/--destination (decrypt-backup)
    JOBS = "jobs"  # --jobs (decrypt-backup)
    KEY_FILE_OUTPUT = "key_file_output"  # -k/--key-file (extract-key: file to write)
    NON_INTERACTIVE = "non_interactive"  # -n/--non-interactive (always passed)


@dataclass(frozen=True)
class Command:
    id: str
    tool: Tool
    subcommand: str
    title: str
    icon: str
    summary: str
    input_label: str
    input_kind: InputKind
    options: frozenset[Option]
    docs_path: str

    @property
    def produces_results(self) -> bool:
        return Option.OUTPUT in self.options

    @property
    def docs_url(self) -> str:
        return f"https://docs.mvt.re/en/latest/{self.docs_path}"

    @property
    def run_title(self) -> str:
        return {"iosDecryptBackup": "Decrypt", "iosExtractKey": "Extract Key"}.get(self.id, "Run Check")


O = Option
_CHECK = frozenset({O.IOCS, O.OUTPUT, O.FAST, O.HASHES, O.MODULE, O.LIST_MODULES})
_RECHECK_SUMMARY = (
    "Compare JSON results from a previous run against indicators, without re-reading the original acquisition."
)

COMMANDS: dict[str, Command] = {
    c.id: c
    for c in [
        Command(
            "iosCheckBackup", Tool.IOS, "check-backup", "Check Backup", "backup",
            "Extract artifacts from an iPhone backup made with the Apple Devices app or iTunes. "
            "Encrypted backups must be decrypted first with Decrypt Backup.",
            "Backup folder", InputKind.FOLDER, _CHECK, "ios/backup/check/",
        ),
        Command(
            "iosCheckFS", Tool.IOS, "check-fs", "Check Filesystem Dump", "folder",
            "Extract artifacts from a full filesystem dump or mount point (e.g. from a jailbroken device).",
            "Filesystem dump", InputKind.FOLDER, _CHECK, "ios/filesystem/check/",
        ),
        Command(
            "iosCheckSysdiagnose", Tool.IOS, "check-sysdiagnose", "Check Sysdiagnose", "health",
            "Analyze an iOS sysdiagnose archive (.tar.gz) or an extracted sysdiagnose folder. "
            "Forensic checks come from installed plugin packages.",
            "Sysdiagnose", InputKind.FILE_OR_FOLDER,
            frozenset({O.IOCS, O.OUTPUT, O.HASHES, O.MODULE, O.LIST_MODULES}), "ios/sysdiagnose/",
        ),
        Command(
            "iosDecryptBackup", Tool.IOS, "decrypt-backup", "Decrypt Backup", "unlock",
            "Decrypt an encrypted iPhone backup into a new folder, using the backup password or a key file.",
            "Backup folder", InputKind.FOLDER,
            frozenset({O.DESTINATION, O.JOBS, O.IOS_PASSWORD, O.HASHES}), "ios/backup/check/",
        ),
        Command(
            "iosExtractKey", Tool.IOS, "extract-key", "Extract Backup Key", "key",
            "Derive the decryption key from an encrypted backup and its password, so you can decrypt later "
            "without the password. The key is sensitive — keep it safe.",
            "Backup folder", InputKind.FOLDER, frozenset({O.IOS_PASSWORD, O.KEY_FILE_OUTPUT}), "ios/backup/check/",
        ),
        Command(
            "iosCheckIOCs", Tool.IOS, "check-iocs", "Re-check Results", "sync", _RECHECK_SUMMARY,
            "Results folder", InputKind.FOLDER, frozenset({O.IOCS, O.MODULE, O.LIST_MODULES}), "iocs/",
        ),
        Command(
            "androidCheckAndroidQF", Tool.ANDROID, "check-androidqf", "Check AndroidQF", "package",
            "Analyze an acquisition collected with AndroidQF (folder or .zip). Includes the nested backup, "
            "bug report and intrusion logs when present.",
            "AndroidQF output", InputKind.FILE_OR_FOLDER,
            frozenset({O.IOCS, O.OUTPUT, O.HASHES, O.MODULE, O.LIST_MODULES,
                       O.VIRUSTOTAL, O.ANDROID_PASSWORD, O.NON_INTERACTIVE}),
            "android/methodology/",
        ),
        Command(
            "androidCheckBackup", Tool.ANDROID, "check-backup", "Check Backup (SMS)", "backup",
            "Check an Android backup (.ab file or unpacked folder). Currently extracts SMS/MMS messages.",
            "Backup", InputKind.FILE_OR_FOLDER,
            frozenset({O.IOCS, O.OUTPUT, O.LIST_MODULES, O.ANDROID_PASSWORD, O.NON_INTERACTIVE}),
            "android/backup/",
        ),
        Command(
            "androidCheckBugreport", Tool.ANDROID, "check-bugreport", "Check Bug Report", "bug",
            "Analyze a standalone Android bug report (.zip).",
            "Bug report", InputKind.FILE,
            frozenset({O.IOCS, O.OUTPUT, O.MODULE, O.LIST_MODULES, O.TIMEZONE}), "android/adb/",
        ),
        Command(
            "androidCheckIntrusionLogs", Tool.ANDROID, "check-intrusion-logs", "Check Intrusion Logs", "shield",
            "Analyze Android Advanced Protection intrusion logs (folder of .txt files or a .zip).",
            "Intrusion logs", InputKind.FILE_OR_FOLDER,
            frozenset({O.IOCS, O.OUTPUT, O.MODULE, O.LIST_MODULES, O.TIMEZONE}), "android/intrusion_logs/",
        ),
        Command(
            "androidCheckIOCs", Tool.ANDROID, "check-iocs", "Re-check Results", "sync", _RECHECK_SUMMARY,
            "Results folder", InputKind.FOLDER, frozenset({O.IOCS, O.MODULE, O.LIST_MODULES}), "iocs/",
        ),
        Command(
            "downloadIOCs", Tool.COMMON, "download-iocs", "Download Indicators", "download",
            "Download the public STIX2 indicators from the mvt-indicators repository. "
            "Downloaded indicators are used automatically by every check.",
            "", InputKind.NONE, frozenset(), "iocs/",
        ),
    ]
}

IOS_COMMANDS = ["iosCheckBackup", "iosCheckFS", "iosCheckSysdiagnose", "iosDecryptBackup", "iosExtractKey", "iosCheckIOCs"]
ANDROID_COMMANDS = [
    "androidCheckAndroidQF", "androidCheckBackup", "androidCheckBugreport",
    "androidCheckIntrusionLogs", "androidCheckIOCs",
]


@dataclass
class Invocation:
    """A resolved MVT run: the script, its arguments and extra environment
    variables (secrets go there so they never show up in the process list)."""

    tool: Tool
    arguments: list[str]
    environment: dict[str, str] = field(default_factory=dict)
    # Use only the indicator files passed with --iocs, instead of also
    # loading every downloaded indicator file.
    only_passed_indicators: bool = False


def quote(value: str) -> str:
    """Quotes an argument for display, the way cmd.exe would need it."""
    if value and not any(c in value for c in ' \t"&|<>^%'):
        return value
    return '"' + value.replace('"', '\\"') + '"'


@dataclass
class CommandForm:
    """What was entered in one command's form. Kept per command so that
    switching between commands doesn't lose it."""

    command: Command
    input_path: str = ""
    output_path: str = ""
    # "all": every downloaded indicator file plus extra files (MVT's default).
    # "picked": only the downloaded files picked in the form plus extra files.
    indicator_mode: str = "all"
    picked_indicators: set[str] = field(default_factory=set)
    ioc_files: list[str] = field(default_factory=list)
    fast: bool = False
    hashes: bool = False
    module: str = ""
    timezone: str = ""
    password: str = ""
    use_key_file: bool = False
    key_file_path: str = ""
    destination_path: str = ""
    jobs: int = 4
    key_file_output_path: str = ""
    virustotal: bool = False
    virustotal_delay: int = 16
    virustotal_api_key: str = ""

    def has(self, option: Option) -> bool:
        return option in self.command.options

    @property
    def indicator_files(self) -> list[str]:
        """The files passed with --iocs."""
        picked = sorted(self.picked_indicators) if self.indicator_mode == "picked" else []
        return picked + [f for f in self.ioc_files if f not in picked]

    def validation_error(self) -> str | None:
        """A problem that prevents running, or None."""
        label = self.command.input_label.lower()
        if self.command.input_kind is not InputKind.NONE:
            if not self.input_path:
                return f"Choose the {label} to analyze."
            if not os.path.exists(self.input_path):
                return f"The selected {label} no longer exists."
        if self.has(O.DESTINATION) and not self.destination_path:
            return "Choose a destination folder for the decrypted backup."
        if self.has(O.IOS_PASSWORD):
            if self.use_key_file and self.command.id == "iosDecryptBackup":
                if not self.key_file_path:
                    return "Choose the key file."
            elif not self.password:
                return "Enter the backup password."
        if (
            self.has(O.VIRUSTOTAL) and self.virustotal and not self.virustotal_api_key
            and not os.environ.get("MVT_VT_API_KEY")
        ):
            return "Enter a VirusTotal API key, or turn VirusTotal lookups off."
        if self.has(O.IOCS):
            for ioc in self.indicator_files:
                if not os.path.isfile(ioc):
                    return f"Indicator file not found: {ioc}"
        return None

    def invocation(self, list_modules_only: bool = False) -> Invocation:
        args = [self.command.subcommand]
        env: dict[str, str] = {}

        if list_modules_only:
            args.append("--list-modules")
            # click requires an existing positional path even when only
            # listing modules; any folder will do.
            if self.command.input_kind is not InputKind.NONE:
                exists = bool(self.input_path) and os.path.exists(self.input_path)
                args.append(self.input_path if exists else tempfile.gettempdir())
            return Invocation(self.command.tool, args, env)

        if self.has(O.IOCS):
            for ioc in self.indicator_files:
                args += ["--iocs", ioc]
        if self.has(O.OUTPUT) and self.output_path:
            args += ["--output", self.output_path]
        if self.has(O.FAST) and self.fast:
            args.append("--fast")
        if self.has(O.HASHES) and self.hashes:
            args.append("--hashes")
        if self.has(O.MODULE) and self.module.strip():
            args += ["--module", self.module.strip()]
        if self.has(O.TIMEZONE) and self.timezone.strip():
            args += ["--timezone", self.timezone.strip()]
        if self.has(O.DESTINATION):
            args += ["--destination", self.destination_path, "--jobs", str(self.jobs)]
        if self.has(O.IOS_PASSWORD):
            if self.use_key_file and self.command.id == "iosDecryptBackup":
                args += ["--key-file", self.key_file_path]
            else:
                env["MVT_IOS_BACKUP_PASSWORD"] = self.password
        if self.has(O.KEY_FILE_OUTPUT) and self.key_file_output_path:
            args += ["--key-file", self.key_file_output_path]
        if self.has(O.ANDROID_PASSWORD) and self.password:
            env["MVT_ANDROID_BACKUP_PASSWORD"] = self.password
        if self.has(O.VIRUSTOTAL) and self.virustotal:
            args += ["--virustotal", "--delay", str(self.virustotal_delay)]
            if self.virustotal_api_key:
                env["MVT_VT_API_KEY"] = self.virustotal_api_key
        # The app has no terminal to answer prompts on.
        if self.has(O.NON_INTERACTIVE):
            args.append("--non-interactive")

        if self.command.input_kind is not InputKind.NONE:
            args.append(self.input_path)

        return Invocation(
            self.command.tool, args, env,
            only_passed_indicators=self.has(O.IOCS) and self.indicator_mode == "picked",
        )
