"""Opens the app's window and runs a real check through it."""

import os
import shutil
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
BACKUP = REPO / "tests" / "artifacts" / "ios_backup"
STIX2 = REPO / "tests" / "artifacts" / "stix2" / "cytrox.stix2"


@pytest.fixture(scope="module")
def window(tmp_path_factory):
    os.environ["MVTWIN_DATA_FOLDER"] = str(tmp_path_factory.mktemp("data"))
    from mvtwin import environment
    from mvtwin.app import MainWindow
    from mvtwin.context import Context

    environment.data_folder.cache_clear()
    app = QApplication.instance() or QApplication([])
    context = Context()
    context.settings.check_updates = False
    context.settings.check_indicator_updates = False
    context.installed_version = environment.installed_version()
    win = MainWindow(context)
    win.show()
    yield win
    win.close()
    app.processEvents()


def wait_for(condition, timeout: float = 180) -> None:
    loop = QEventLoop()
    timer = QTimer()
    timer.timeout.connect(lambda: condition() and loop.quit())
    timer.start(100)
    QTimer.singleShot(int(timeout * 1000), loop.quit)
    loop.exec()
    timer.stop()
    assert condition(), "timed out"


def test_every_screen_opens(window):
    from mvtwin.commands import COMMANDS

    for key in ["setup", "indicators", "results", *COMMANDS]:
        window.show_page(key)
        assert window.stack.currentWidget() is window.pages[key]


def test_check_backup_and_results(window, tmp_path):
    context = window.context
    output = tmp_path / "Results with spaces"
    form = context.form("iosCheckBackup")
    form.input_path = str(BACKUP)
    form.output_path = str(output)
    form.ioc_files = [str(STIX2)]
    window.show_page("iosCheckBackup")
    page = window.pages["iosCheckBackup"]
    assert page.run_button.isEnabled(), page.message.text()
    page._run()
    wait_for(lambda: not context.runner.is_running)

    text = "\n".join(line for line, _ in context.runner.lines)
    assert context.runner.last_exit_code == 0, text
    assert context.runner.alert_counts, text
    assert (output / "alerts.json").is_file(), text[:1500]
    assert page.view_results.isVisibleTo(page)

    page.view_results.click()
    results = window.pages["results"]
    assert window.stack.currentWidget() is results
    assert results.model.rowCount() > 0
    results.table.selectRow(0)
    assert "Event:" in results.detail.toPlainText()


def test_only_picked_indicators(window, tmp_path):
    """"Only the ones I pick" must not load the downloaded indicators."""
    from mvtwin import environment

    folder = environment.indicators_folder()
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy(STIX2, folder / "downloaded.stix2")
    context = window.context
    form = context.form("iosCheckBackup")
    form.ioc_files = []
    form.module = "BackupInfo"

    def loaded() -> str:
        context.runner.run_mvt(form.invocation(), "test")
        wait_for(lambda: not context.runner.is_running)
        return next((line for line, _ in context.runner.lines if "Loaded a total of" in line), "")

    form.indicator_mode = "all"
    assert "Loaded a total of 0 " not in loaded()
    form.indicator_mode = "picked"
    form.picked_indicators = set()
    assert "Loaded a total of 0 " in loaded()
