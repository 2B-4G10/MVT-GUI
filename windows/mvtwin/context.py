"""State shared by every screen: settings, the runner, what MVT is installed,
and the indicators."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFile, QObject, Signal

from . import environment, indicators
from .background import run_in_background
from .commands import COMMANDS, CommandForm
from .runner import Runner
from .settings import Settings


class Context(QObject):
    mvt_changed = Signal()
    catalog_changed = Signal()
    downloads_changed = Signal()
    navigate = Signal(str)  # "setup", "indicators", "results" or a command id
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings(self)
        self.runner = Runner(self.settings, self)
        self.forms: dict[str, CommandForm] = {}

        self.installed_version: str | None = None
        self.latest_version: str | None = None
        self.checking = False

        self.catalog = indicators.IndicatorCatalog()
        self.loading_catalog = False
        self.downloading: set[str] = set()
        self.downloaded: list[Path] = indicators.downloaded_files()

    def form(self, command_id: str) -> CommandForm:
        if command_id not in self.forms:
            self.forms[command_id] = CommandForm(COMMANDS[command_id])
        return self.forms[command_id]

    # MARK: - MVT

    @property
    def is_outdated(self) -> bool:
        return bool(
            self.installed_version and self.latest_version
            and environment.is_older(self.installed_version, self.latest_version)
        )

    def refresh_mvt(self) -> None:
        self.installed_version = environment.installed_version()
        self.checking = True
        self.mvt_changed.emit()

        def done(latest, _error):
            self.checking = False
            self.latest_version = latest or self.latest_version
            self.mvt_changed.emit()

        run_in_background(environment.latest_version, done)

    def update_mvt(self) -> None:
        """Installs the newest MVT into the app's own runtime."""
        updating = self.is_outdated
        self.runner.clear("Updating MVT" if updating else "Reinstalling MVT")

        def finished(code: int):
            environment.remove_script_wrappers()
            self.refresh_mvt()
            if code == 0:
                self.runner.note(f"MVT {self.installed_version} is ready.")

        self.runner.run(
            environment.python_executable(), environment.update_arguments(),
            display="python -m pip install --upgrade mvt", on_finished=finished,
        )

    # MARK: - Indicators

    def refresh_downloaded(self) -> None:
        self.downloaded = indicators.downloaded_files()
        self.downloads_changed.emit()

    def load_catalog(self, then=None) -> None:
        if self.loading_catalog:
            return
        self.loading_catalog = True
        self.catalog_changed.emit()
        catalog = indicators.IndicatorCatalog()

        def done(_result, _error):
            self.catalog = catalog
            self.loading_catalog = False
            self.catalog_changed.emit()
            self.downloads_changed.emit()
            if then:
                then()

        run_in_background(catalog.load, done)

    def is_downloaded(self, indicator_set: indicators.IndicatorSet) -> bool:
        return any(p.name == indicator_set.local_file_name for p in self.downloaded)

    def download(self, sets: list[indicators.IndicatorSet], then=None) -> None:
        """Downloads sets one after another."""
        queue = [s for s in sets if s.download_url not in self.downloading]
        self.downloading.update(s.download_url for s in queue)
        self.downloads_changed.emit()

        def next_one():
            if not queue:
                if then:
                    then()
                return
            current = queue.pop(0)

            def done(_result, error):
                self.downloading.discard(current.download_url)
                if error:
                    self.error.emit(f"Couldn't download “{current.name}”: {error}")
                self.refresh_downloaded()
                next_one()

            run_in_background(lambda: indicators.download(current), done)

        next_one()

    def import_files(self, paths: list[str]) -> None:
        for path in paths:
            try:
                indicators.import_file(Path(path))
            except OSError as exc:
                self.error.emit(f"Couldn't import {Path(path).name}: {exc}")
        self.refresh_downloaded()

    def remove(self, path: Path) -> None:
        """Moves a downloaded file to the Recycle Bin."""
        if not QFile.moveToTrash(str(path)):
            try:
                path.unlink()
            except OSError as exc:
                self.error.emit(f"Couldn't remove {path.name}: {exc}")
        self.refresh_downloaded()

    def display_name(self, path: Path) -> str:
        return self.catalog.display_name(path)
