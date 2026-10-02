"""Checks of the app's logic that don't need a window."""

import importlib.util
import re
from pathlib import Path

from mvtwin import environment, indicators
from mvtwin.commands import COMMANDS, CommandForm, Option, Tool
from mvtwin.logs import Level, classify, take_complete_lines

REPO = Path(__file__).resolve().parents[2]
SWIFT = REPO / "macos" / "MVTGUI"


def contract():
    spec = importlib.util.spec_from_file_location(
        "contract", REPO / "macos" / "scripts" / "check_cli_contract.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def full_form(command_id: str) -> CommandForm:
    """A form with every field filled in, so every flag is passed."""
    form = CommandForm(COMMANDS[command_id])
    form.input_path = str(REPO)
    form.output_path = "out"
    form.indicator_mode = "picked"
    form.picked_indicators = {"a.stix2"}
    form.ioc_files = ["b.stix2"]
    form.fast = form.hashes = form.virustotal = True
    form.module = "Mod"
    form.timezone = "UTC"
    form.password = "secret"
    form.destination_path = "dest"
    form.key_file_output_path = "key"
    form.virustotal_api_key = "vt"
    return form


def test_flags_are_in_the_cli_contract():
    """Every flag the app passes is one check_cli_contract.py verifies
    against MVT, so upstream changes fail CI instead of breaking the app."""
    expected = contract().EXPECTED_OPTIONS
    for command in COMMANDS.values():
        allowed = set(expected[(command.tool.value, command.subcommand)])
        for key_file in (False, True):
            form = full_form(command.id)
            form.use_key_file = key_file
            form.key_file_path = "keyfile"
            args = form.invocation().arguments
            if Option.LIST_MODULES in command.options:
                args += form.invocation(list_modules_only=True).arguments
            flags = {a for a in args if a.startswith("--")}
            assert flags <= allowed, (command.id, flags - allowed)


def test_same_commands_as_the_macos_app():
    swift = (SWIFT / "Models" / "MVTCommand.swift").read_text(encoding="utf-8")
    swift = swift.split("var subcommand: String", 1)[1].split("var title", 1)[0]
    subcommands = dict(re.findall(r"case \.(\w+): return \"([a-z-]+)\"", swift))
    for case in re.findall(r"case \.(\w+), \.(\w+): return \"check-iocs\"", swift):
        subcommands.update(dict.fromkeys(case, "check-iocs"))
    assert set(subcommands) == set(COMMANDS)
    for command_id, subcommand in subcommands.items():
        assert COMMANDS[command_id].subcommand == subcommand


def test_known_extra_indicator_files_match_the_macos_app():
    swift = (SWIFT / "Services" / "IndicatorsIndex.swift").read_text(encoding="utf-8")
    assert set(re.findall(r'\(repo: "([^"]+)", path: "([^"]+)"\)', swift)) == set(
        indicators.KNOWN_EXTRA_FILES
    )
    repos = re.findall(
        r'SourceRepository\(owner: "([^"]+)", repo: "([^"]+)", branch: "([^"]+)"', swift
    )
    assert repos == [
        (s.owner, s.repo, s.branch) for s in indicators.SOURCE_REPOSITORIES
    ]


def test_secrets_go_in_the_environment():
    form = full_form("iosDecryptBackup")
    invocation = form.invocation()
    assert "secret" not in invocation.arguments
    assert invocation.environment == {"MVT_IOS_BACKUP_PASSWORD": "secret"}
    form.use_key_file = True
    form.key_file_path = "keyfile"
    assert form.invocation().arguments[-3:-1] == ["--key-file", "keyfile"]

    form = full_form("androidCheckAndroidQF")
    invocation = form.invocation()
    assert invocation.environment == {
        "MVT_ANDROID_BACKUP_PASSWORD": "secret",
        "MVT_VT_API_KEY": "vt",
    }
    assert invocation.arguments[-2:] == ["--non-interactive", str(REPO)]
    assert invocation.only_passed_indicators


def test_picked_indicators():
    form = full_form("iosCheckBackup")
    assert form.indicator_files == ["a.stix2", "b.stix2"]
    form.indicator_mode = "all"
    assert form.indicator_files == ["b.stix2"]
    assert not form.invocation().only_passed_indicators


def test_validation():
    form = CommandForm(COMMANDS["iosCheckBackup"])
    assert form.validation_error() == "Choose the backup folder to analyze."
    form.input_path = str(REPO / "missing")
    assert "no longer exists" in form.validation_error()
    form.input_path = str(REPO)
    assert form.validation_error() is None
    form.ioc_files = [str(REPO / "missing.stix2")]
    assert form.validation_error().startswith("Indicator file not found")

    decrypt = CommandForm(COMMANDS["iosDecryptBackup"])
    decrypt.input_path = str(REPO)
    assert (
        decrypt.validation_error()
        == "Choose a destination folder for the decrypted backup."
    )
    decrypt.destination_path = "dest"
    assert decrypt.validation_error() == "Enter the backup password."


def test_mvt_is_run_through_python():
    args = environment.mvt_arguments(Tool.ANDROID, ["check-androidqf", "x"])
    assert args[0] == "-c" and "from mvt.android import main" in args[1]
    assert args[2:] == ["check-androidqf", "x"]


def test_log_levels():
    assert classify("CRITICAL ALERT something") == Level.CRITICAL_ALERT
    assert classify("INFO ALERT x") == Level.INFO_ALERT
    assert classify("WARNING x") == Level.WARNING
    assert classify("Traceback (most recent call last):") == Level.ERROR
    assert classify("just text") == Level.PLAIN


def test_lines_from_windows_output():
    buffer = bytearray(b"one\r\ntwo 10%\rtwo 100%\r\nthr")
    assert take_complete_lines(buffer) == ["one", "two 100%"]
    assert buffer == b"thr"


def test_versions():
    assert environment.is_older("2026.5.12", "2026.9.28")
    assert not environment.is_older("2026.9.28", "2026.9.28")
    assert not environment.is_older("2026.10.1", "2026.9.28")
    assert not environment.is_older("0.1.dev148+g777db67", "2026.9.28")


INDEX = """
indicators:
  -
    type: github
    name: "NSO Group Pegasus Indicators of Compromise"
    source: Amnesty International
    sources:
      - Amnesty International
    references:
      - https://www.amnesty.org/en/latest/research/2021/07/forensic-methodology-report/
    github:
      owner: mvt-project
      repo: mvt-indicators
      branch: main
      path: 2021-07-18_nso/pegasus.stix2
  - type: download
    name: Other # a comment
    download_url: https://example.org/other.stix2
  - type: download
    name: Insecure
    download_url: http://example.org/x.stix2
"""


def test_index_parsing():
    sets = indicators.parse_index(INDEX)
    assert [s.name for s in sets] == [
        "NSO Group Pegasus Indicators of Compromise",
        "Other",
    ]
    assert sets[0].download_url == (
        "https://raw.githubusercontent.com/mvt-project/mvt-indicators/main/2021-07-18_nso/pegasus.stix2"
    )
    assert sets[0].sources == ("Amnesty International",)
    assert len(sets[0].references) == 1


def test_file_names_match_mvt():
    """contract check_indicator_downloads verifies MVT names this file the same."""
    s = indicators.IndicatorSet(
        "x", "https://raw.githubusercontent.com/o/r/main/dir/x.stix2"
    )
    assert s.local_file_name == "raw.githubusercontent.com_o_r_main_dir_x.stix2"


def test_display_names():
    assert (
        indicators.display_name("2021-12-16_cytrox/cytrox.stix2")
        == "Cytrox indicators (2021-12-16)"
    )
    assert indicators.display_name("stalkerware.stix2") == "Stalkerware indicators"


def test_every_option_is_covered():
    used = set().union(*(c.options for c in COMMANDS.values()))
    assert used == set(Option)
