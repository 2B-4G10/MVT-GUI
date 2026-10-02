"""The app's screens. Mirrors the views in macos/MVTGUI/Views."""

from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtGui import (
    QFont,
    QKeySequence,
    QShortcut,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import environment
from .commands import COMMANDS, CommandForm, InputKind, Option, Tool
from .context import Context
from .logs import ALERT_LEVELS, Level
from .widgets import (
    ANDROID_GREEN,
    IOS_ACCENT,
    SUCCESS,
    Badge,
    Card,
    PathField,
    caption,
    hbox,
    icon,
    level_color,
    link,
    open_path,
    open_url,
    pick,
    reveal,
    tool_button,
)

HELP_AMNESTY = "https://securitylab.amnesty.org/get-help/?c=mvt_docs"
HELP_ACCESS_NOW = "https://www.accessnow.org/help/"


def accent(command) -> str:
    return ANDROID_GREEN if command.tool == Tool.ANDROID else pick(IOS_ACCENT).name()


class Page(QWidget):
    """A screen: a title and a scrolling column of cards."""

    def __init__(
        self, title: str, subtitle: str = "", scrolls: bool = True, parent=None
    ):
        super().__init__(parent)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("pageTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("caption")
        self.subtitle_label.setVisible(bool(subtitle))

        self.body = QWidget()
        self.column = QVBoxLayout(self.body)
        self.column.setContentsMargins(24, 4, 24, 16)
        self.column.setSpacing(12)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.body)
        scroll.setObjectName("pageScroll")
        self.scroll = scroll

        self.header = QHBoxLayout()
        self.header.setContentsMargins(24, 16, 24, 8)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        titles.addWidget(self.title_label)
        titles.addWidget(self.subtitle_label)
        self.header.addLayout(titles)
        self.header.addStretch(1)

        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(0)
        self.layout_.addLayout(self.header)
        if scrolls:
            self.layout_.addWidget(scroll, 1)
        else:
            self.layout_.addWidget(scroll.takeWidget(), 1)

    def add_card(self, card: QWidget) -> QWidget:
        self.column.addWidget(card)
        return card

    def finish(self) -> None:
        self.column.addStretch(1)

    def shown(self) -> None:
        """Called when the page is opened."""


def clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())


# MARK: - Setup


class SetupPage(Page):
    def __init__(self, context: Context):
        super().__init__("Setup")
        self.context = context

        status = Card("Mobile Verification Toolkit")
        self.status_icon = QLabel()
        self.status_title = QLabel()
        self.status_title.setObjectName("strong")
        self.status_detail = caption("")
        self.update_button = QPushButton("Update MVT")
        self.update_button.setObjectName("accent")
        self.update_button.clicked.connect(self._update)
        self.check_button = QPushButton("Check Again")
        self.check_button.clicked.connect(context.refresh_mvt)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        texts.addWidget(self.status_title)
        texts.addWidget(self.status_detail)
        status.add_layout(
            hbox(self.status_icon, (texts, 1), self.update_button, self.check_button)
        )
        self.add_card(status)

        acquire = Card("Acquiring data")
        acquire.add(
            self._info(
                "iPhone / iPad",
                "Connect the iPhone and open it in the Apple Devices app (or iTunes). Tick “Encrypt local backup”, "
                "set a password and back it up. Backups are saved in "
                "%USERPROFILE%\\Apple\\MobileSync\\Backup (Apple Devices, iTunes from the Microsoft Store) or "
                "%APPDATA%\\Apple Computer\\MobileSync\\Backup (iTunes from apple.com).",
                "https://docs.mvt.re/en/latest/ios/backup/itunes/",
            )
        )
        acquire.add(
            self._info(
                "Android",
                "Collect data with AndroidQF (it has a Windows version), then analyze its output folder with "
                "Check AndroidQF.",
                "https://github.com/mvt-project/androidqf",
            )
        )
        self.indicators_text = caption("")
        self.indicators_button = QPushButton()
        self.indicators_button.clicked.connect(
            lambda: context.navigate.emit("indicators")
        )
        box = QVBoxLayout()
        box.setSpacing(2)
        title = QLabel("Indicators")
        title.setObjectName("strong")
        box.addWidget(title)
        box.addWidget(self.indicators_text)
        acquire.add_layout(hbox((box, 1), self.indicators_button))
        self.add_card(acquire)

        storage = Card("Your data")
        folder = environment.data_folder()
        storage.add(
            caption(
                "Settings and downloaded indicators are kept in "
                + (
                    "the app's Data folder, so the app can be moved or run from a USB drive:"
                    if folder == environment.ROOT / "Data"
                    else "this folder:"
                )
            )
        )
        path = QLineEdit(str(folder))
        path.setReadOnly(True)
        open_button = QPushButton("Open")
        open_button.clicked.connect(
            lambda: (folder.mkdir(parents=True, exist_ok=True), open_path(folder))
        )
        storage.add_layout(hbox(path, open_button))
        self.add_card(storage)

        about = Card("About")
        about.add(
            caption(
                "MVT is a forensic research tool for technologists and investigators, developed by Amnesty "
                "International's Security Lab. It is licensed for the consensual analysis of devices; analyzing "
                "data from people who have not consented is not permitted. It is not a tool for end-user "
                "self-assessment — if you are concerned about your device, seek expert help."
            )
        )
        about.add_layout(
            hbox(
                link("Documentation", "https://docs.mvt.re/"),
                link("License", "https://docs.mvt.re/en/latest/license/"),
                link(
                    "Get help (Amnesty Security Lab)",
                    "https://securitylab.amnesty.org/get-help/",
                ),
                None,
            )
        )
        self.add_card(about)
        self.finish()

        context.mvt_changed.connect(self.refresh)
        context.downloads_changed.connect(self.refresh)
        context.runner.state_changed.connect(self.refresh)
        self.refresh()

    def _info(self, title: str, text: str, url: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        name = QLabel(title)
        name.setObjectName("strong")
        layout.addLayout(hbox(name, None, link("Learn more", url)))
        layout.addWidget(caption(text))
        return widget

    def refresh(self) -> None:
        c = self.context
        version = c.installed_version
        where = (
            str(environment.ROOT)
            if environment.PORTABLE
            else os.path.dirname(os.path.dirname(os.__file__))
        )
        if version and c.is_outdated:
            self._status(
                "update",
                "#C25E00",
                f"MVT {version} is out of date",
                f"Version {c.latest_version} is available. Updating brings the latest checks and fixes.",
            )
        elif version:
            detail = (
                "Up to date"
                if c.latest_version == version
                else (
                    "Looking for updates…"
                    if c.checking
                    else "Couldn't check for updates"
                )
            )
            self._status(
                "check",
                pick(SUCCESS).name(),
                f"MVT {version} is ready",
                f"{detail} · {where}",
            )
        else:
            self._status(
                "warning",
                "#C25E00",
                "MVT was not found",
                "This copy of the app is incomplete. Download it again from the Releases page.",
            )
        can_update = environment.can_update_in_place()
        self.update_button.setVisible(c.is_outdated)
        self.update_button.setEnabled(can_update and not c.runner.is_running)
        if c.is_outdated and not can_update:
            self.update_button.setToolTip(
                "The app's folder can't be written to. Move it to a folder you own, or download the newest release."
            )
        self.check_button.setEnabled(not c.checking)

        count = len(c.downloaded)
        self.indicators_text.setText(
            "Download the public indicators before your first check, so that known spyware traces can be found."
            if count == 0
            else f"{count} indicator files downloaded. Update them regularly."
        )
        self.indicators_button.setText(
            "Get Indicators…" if count == 0 else "Manage Indicators…"
        )

    def _status(self, glyph: str, color: str, title: str, detail: str) -> None:
        self.status_icon.setPixmap(icon(glyph, color).pixmap(28, 28))
        self.status_title.setText(title)
        self.status_detail.setText(detail)

    def _update(self) -> None:
        self.context.update_mvt()


# MARK: - Indicators


class IndicatorsPage(Page):
    def __init__(self, context: Context):
        super().__init__("Indicators")
        self.context = context

        intro = Card()
        for line in [
            "Indicators are lists of known spyware traces (STIX2 files).",
            "Every check compares the device data against the downloaded indicators.",
            "Download them before your first check, and update them regularly.",
            "Public indicators can't prove a device is clean. If you're worried, get expert help (links below).",
        ]:
            intro.add(caption("•  " + line))
        self.add_card(intro)

        official = Card("Official indicators")
        self.download_all = QPushButton(icon("download"), "Download All")
        self.download_all.setObjectName("accent")
        self.download_all.clicked.connect(self._download_all)
        self.refresh_list = QPushButton(icon("refresh"), "Refresh List")
        self.refresh_list.clicked.connect(lambda: context.load_catalog())
        self.count_label = caption("")
        official.add_layout(
            hbox(self.download_all, self.refresh_list, None, self.count_label)
        )
        self.index_error = caption("")
        self.index_error.setStyleSheet("color: #C25E00;")
        official.add(self.index_error)
        self.set_rows = QVBoxLayout()
        self.set_rows.setSpacing(6)
        official.add_layout(self.set_rows)
        official.add(
            caption(
                "From MVT's official list (mvt-indicators) plus every other STIX2 file in the Amnesty International "
                "and Echap stalkerware repositories. “Download All” runs mvt download-iocs, then downloads the rest."
            )
        )
        self.add_card(official)

        downloaded = Card("Downloaded indicators")
        self.file_rows = QVBoxLayout()
        self.file_rows.setSpacing(6)
        downloaded.add_layout(self.file_rows)
        import_button = QPushButton("Import STIX2 File…")
        import_button.clicked.connect(self._import)
        open_button = QPushButton("Open Folder")
        open_button.clicked.connect(self._open_folder)
        downloaded.add_layout(hbox(import_button, open_button, None))
        downloaded.add(
            caption(
                f"Stored in {environment.indicators_folder()}. To use only some of them in a check, press "
                "“Choose Indicators…” in that check."
            )
        )
        self.add_card(downloaded)

        sources = Card("Where indicators come from")
        for text, url in [
            (
                "MVT's official indicator list (mvt-indicators)",
                "https://github.com/mvt-project/mvt-indicators",
            ),
            (
                "The index file MVT downloads from (indicators.yaml)",
                "https://github.com/mvt-project/mvt-indicators/blob/main/indicators.yaml",
            ),
            (
                "Amnesty International investigations",
                "https://github.com/AmnestyTech/investigations",
            ),
            (
                "Stalkerware indicators",
                "https://github.com/AssoEchap/stalkerware-indicators",
            ),
            ("MVT documentation on indicators", "https://docs.mvt.re/en/latest/iocs/"),
            ("Get expert help: Amnesty International Security Lab", HELP_AMNESTY),
            ("Get expert help: Access Now Digital Security Helpline", HELP_ACCESS_NOW),
        ]:
            sources.add(link(text, url))
        self.add_card(sources)
        self.finish()

        context.catalog_changed.connect(self.refresh)
        context.downloads_changed.connect(self.refresh)
        context.runner.state_changed.connect(self._update_buttons)
        self.refresh()

    def shown(self) -> None:
        self.context.refresh_downloaded()
        if not self.context.catalog.sets:
            self.context.load_catalog()

    def refresh(self) -> None:
        c = self.context
        clear_layout(self.set_rows)
        for indicator_set in c.catalog.sets:
            self.set_rows.addWidget(self._set_row(indicator_set))
        if c.loading_catalog:
            self.count_label.setText("Loading the list…")
        elif c.catalog.sets:
            count = sum(1 for s in c.catalog.sets if c.is_downloaded(s))
            self.count_label.setText(f"{count} of {len(c.catalog.sets)} downloaded")
        else:
            self.count_label.setText("")
        self.index_error.setText(c.catalog.error or "")
        self.index_error.setVisible(bool(c.catalog.error))

        clear_layout(self.file_rows)
        if not c.downloaded:
            self.file_rows.addWidget(caption("No indicators downloaded yet."))
        for path in c.downloaded:
            name = QLabel(c.display_name(path))
            file = caption(path.name)
            texts = QVBoxLayout()
            texts.setSpacing(0)
            texts.addWidget(name)
            texts.addWidget(file)
            row = QWidget()
            row.setLayout(
                hbox(
                    (texts, 1),
                    tool_button(
                        "open",
                        "Show in File Explorer",
                        lambda _=False, p=path: reveal(p),
                    ),
                    tool_button(
                        "delete",
                        "Move to the Recycle Bin",
                        lambda _=False, p=path: c.remove(p),
                    ),
                )
            )
            self.file_rows.addWidget(row)
        self._update_buttons()

    def _update_buttons(self) -> None:
        c = self.context
        self.download_all.setEnabled(
            not c.runner.is_running and not c.downloading and not c.loading_catalog
        )
        self.refresh_list.setEnabled(not c.loading_catalog)

    def _set_row(self, indicator_set) -> QWidget:
        c = self.context
        downloaded = c.is_downloaded(indicator_set)
        mark = QLabel()
        mark.setPixmap(
            icon(
                "check" if downloaded else "remove",
                pick(SUCCESS).name() if downloaded else None,
            ).pixmap(16, 16)
        )
        texts = QVBoxLayout()
        texts.setSpacing(0)
        texts.addWidget(QLabel(indicator_set.name))
        if indicator_set.sources:
            texts.addWidget(
                caption(
                    ", ".join(indicator_set.sources)
                    + ("" if indicator_set.in_mvt_index else " · not in MVT's list")
                )
            )
        items: list = [mark, (texts, 1)]
        if indicator_set.references:
            if len(indicator_set.references) == 1:
                items.append(link("Details", indicator_set.references[0]))
            else:
                details = QToolButton()
                details.setText("Details")
                details.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
                menu = QMenu(details)
                for url in indicator_set.references:
                    menu.addAction(
                        url.split("/")[2] if "//" in url else url,
                        lambda u=url: open_url(u),
                    )
                details.setMenu(menu)
                items.append(details)
        if indicator_set.download_url in c.downloading:
            items.append(caption("Downloading…"))
        else:
            button = QPushButton("Update" if downloaded else "Download")
            button.clicked.connect(lambda: c.download([indicator_set]))
            items.append(button)
        row = QWidget()
        row.setLayout(hbox(*items))
        return row

    def _download_all(self) -> None:
        c = self.context

        def start():
            # MVT's own command fetches the sets in its list and records when
            # indicators were last updated, which its update check uses. The
            # app downloads the rest, and everything if the command fails.
            def after(code: int):
                c.refresh_downloaded()
                remaining = [
                    s for s in c.catalog.sets if code != 0 or not s.in_mvt_index
                ]
                if remaining:
                    c.download(
                        remaining,
                        lambda: c.runner.note(
                            f"Downloaded {len(remaining)} more indicator file{'s' if len(remaining) != 1 else ''} "
                            "from the source repositories."
                        ),
                    )

            c.runner.run_mvt(
                c.form("downloadIOCs").invocation(), "Download indicators", after
            )

        if not c.catalog.sets:
            c.load_catalog(then=start)
        else:
            start()

    def _import(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import STIX2 Files",
            str(Path.home()),
            "STIX2 files (*.stix2 *.json);;All files (*)",
        )
        if paths:
            self.context.import_files(paths)

    def _open_folder(self) -> None:
        folder = environment.indicators_folder()
        folder.mkdir(parents=True, exist_ok=True)
        open_path(folder)


# MARK: - Indicator picker


class IndicatorPicker(QDialog):
    """Chooses which indicators a check uses."""

    def __init__(self, context: Context, form: CommandForm, parent=None):
        super().__init__(parent)
        self.context = context
        self.form = form
        self.setWindowTitle("Choose indicators")
        self.setMinimumWidth(560)

        context.refresh_downloaded()
        present = {str(p) for p in context.downloaded}
        form.picked_indicators &= present

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        title = QLabel("Choose indicators")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        layout.addWidget(
            caption(
                "Indicators are lists of known spyware traces. The check compares the device data against the "
                "ones you choose here."
            )
        )
        self.all_radio = QRadioButton("All downloaded indicators (recommended)")
        self.picked_radio = QRadioButton("Only the ones I pick")
        group = QButtonGroup(self)
        group.addButton(self.all_radio)
        group.addButton(self.picked_radio)
        (
            self.picked_radio if form.indicator_mode == "picked" else self.all_radio
        ).setChecked(True)
        self.all_radio.toggled.connect(self._mode_changed)
        layout.addWidget(self.all_radio)
        layout.addWidget(self.picked_radio)

        downloaded = Card("Downloaded indicators")
        self.list = QListWidget()
        self.list.setMinimumHeight(160)
        for path in context.downloaded:
            item = QListWidgetItem(context.display_name(path))
            item.setToolTip(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if str(path) in form.picked_indicators
                else Qt.CheckState.Unchecked
            )
            self.list.addItem(item)
        self.list.itemChanged.connect(self._pick_changed)
        if not context.downloaded:
            downloaded.add(caption("None downloaded yet."))
        else:
            downloaded.add(self.list)
        self.select_all = QPushButton("Select All")
        self.select_all.clicked.connect(lambda: self._set_all(True))
        self.select_none = QPushButton("Select None")
        self.select_none.clicked.connect(lambda: self._set_all(False))
        downloaded.add_layout(hbox(self.select_all, self.select_none, None))
        layout.addWidget(downloaded)

        extra = Card("Extra STIX2 files")
        self.extra_rows = QVBoxLayout()
        extra.add_layout(self.extra_rows)
        add = QPushButton("Add STIX2 File…")
        add.clicked.connect(self._add_files)
        extra.add_layout(hbox(add, None, caption("Used in either mode.")))
        layout.addWidget(extra)

        self.warning = QLabel("Nothing picked: only MVT's built-in checks will run.")
        self.warning.setStyleSheet("color: #C25E00;")
        layout.addWidget(self.warning)

        buttons = QDialogButtonBox()
        more = buttons.addButton(
            "Get More Indicators…", QDialogButtonBox.ButtonRole.ResetRole
        )
        more.clicked.connect(self._more)
        done = buttons.addButton("Done", QDialogButtonBox.ButtonRole.AcceptRole)
        done.setDefault(True)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self._refresh_extra()
        self._mode_changed()

    def _mode_changed(self) -> None:
        picked = self.picked_radio.isChecked()
        self.form.indicator_mode = "picked" if picked else "all"
        self.list.setEnabled(picked)
        self.select_all.setVisible(picked)
        self.select_none.setVisible(picked)
        self._update_warning()

    def _pick_changed(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if item.checkState() == Qt.CheckState.Checked:
            self.form.picked_indicators.add(path)
        else:
            self.form.picked_indicators.discard(path)
        self._update_warning()

    def _set_all(self, checked: bool) -> None:
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )

    def _update_warning(self) -> None:
        f = self.form
        self.warning.setVisible(
            f.indicator_mode == "picked" and not f.picked_indicators and not f.ioc_files
        )

    def _refresh_extra(self) -> None:
        clear_layout(self.extra_rows)
        for file in self.form.ioc_files:
            name = QLabel(os.path.basename(file))
            name.setToolTip(file)
            self.extra_rows.addLayout(
                hbox(
                    name,
                    None,
                    tool_button(
                        "remove", "Remove", lambda _=False, f=file: self._remove(f)
                    ),
                )
            )
        self._update_warning()

    def _remove(self, file: str) -> None:
        self.form.ioc_files.remove(file)
        self._refresh_extra()

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Add STIX2 Files",
            str(Path.home()),
            "STIX2 files (*.stix2 *.json);;All files (*)",
        )
        for path in paths:
            path = os.path.normpath(path)
            if path not in self.form.ioc_files:
                self.form.ioc_files.append(path)
        self._refresh_extra()

    def _more(self) -> None:
        self.accept()
        self.context.navigate.emit("indicators")


# MARK: - Commands


class CommandPage(Page):
    def __init__(self, context: Context, command_id: str):
        command = COMMANDS[command_id]
        super().__init__(command.title, command.tool.value)
        self.context = context
        self.command = command
        self.form = context.form(command_id)
        self.finished_code: int | None = None
        options = command.options
        form = self.form

        intro = Card()
        glyph = QLabel()
        glyph.setPixmap(icon(command.icon, accent(command)).pixmap(32, 32))
        glyph.setAlignment(Qt.AlignmentFlag.AlignTop)
        texts = QVBoxLayout()
        texts.addWidget(caption(command.summary))
        texts.addWidget(link("Documentation", command.docs_url))
        intro.add_layout(hbox(glyph, (texts, 1)))
        self.add_card(intro)

        if command.input_kind is not InputKind.NONE:
            card = Card("Input")
            mode = {
                InputKind.FOLDER: PathField.FOLDER,
                InputKind.FILE: PathField.FILE,
                InputKind.FILE_OR_FOLDER: PathField.FILE_OR_FOLDER,
            }[command.input_kind]
            self.input_field = PathField(mode)
            self.input_field.set_path(form.input_path)
            self.input_field.changed.connect(lambda _: self._sync())
            card.add_row(command.input_label, self.input_field)
            if command_id == "iosCheckBackup":
                card.add(
                    caption(
                        "Backups are in %USERPROFILE%\\Apple\\MobileSync\\Backup\\<UDID> (Apple Devices app) or "
                        "%APPDATA%\\Apple Computer\\MobileSync\\Backup\\<UDID> (iTunes). "
                        "Encrypted backups must be decrypted first."
                    )
                )
            self.add_card(card)

        if options & {
            Option.IOS_PASSWORD,
            Option.ANDROID_PASSWORD,
            Option.KEY_FILE_OUTPUT,
            Option.DESTINATION,
        }:
            card = Card(
                "Decryption" if Option.DESTINATION in options else "Backup password"
            )
            self.password = QLineEdit()
            self.password.setEchoMode(QLineEdit.EchoMode.Password)
            self.password.textChanged.connect(
                lambda text: (setattr(form, "password", text), self._sync())
            )
            if Option.IOS_PASSWORD in options:
                if command_id == "iosDecryptBackup":
                    self.use_key = QComboBox()
                    self.use_key.addItems(["Password", "Key file"])
                    self.use_key.currentIndexChanged.connect(self._key_mode_changed)
                    card.add_row("Decrypt using", self.use_key, stretch=False)
                    self.key_file = PathField(PathField.FILE)
                    self.key_file.changed.connect(lambda _: self._sync())
                    self.key_row = card.add_row("Key file", self.key_file)
                self.password_row = card.add_row("Backup password", self.password)
            if Option.ANDROID_PASSWORD in options:
                card.add_row("Backup password", self.password)
                self.password.setPlaceholderText("Only if the backup is encrypted")
            if Option.KEY_FILE_OUTPUT in options:
                self.key_output = PathField(
                    PathField.SAVE_FILE, "Print the key in the output", "backup.key"
                )
                self.key_output.changed.connect(lambda _: self._sync())
                card.add_row("Save key to", self.key_output)
            if Option.DESTINATION in options:
                self.destination = PathField(PathField.FOLDER)
                self.destination.changed.connect(lambda _: self._sync())
                card.add_row("Destination folder", self.destination)
                jobs = QSpinBox()
                jobs.setRange(1, 32)
                jobs.setValue(form.jobs)
                jobs.valueChanged.connect(lambda v: setattr(form, "jobs", v))
                card.add_row("Parallel jobs", jobs, stretch=False)
            card.add(
                caption(
                    "Passwords are passed to MVT through an environment variable, never on the command line."
                )
            )
            self.add_card(card)
            if command_id == "iosDecryptBackup":
                self._key_mode_changed(0)

        if options & {Option.OUTPUT, Option.IOCS}:
            card = Card("Analysis")
            if Option.OUTPUT in options:
                self.output_field = PathField(
                    PathField.FOLDER, "Not saved (output only)"
                )
                self.output_field.set_path(form.output_path)
                self.output_field.changed.connect(lambda _: self._sync())
                card.add_row("Results folder", self.output_field)
            if Option.IOCS in options:
                self.indicator_summary = caption("")
                choose = QPushButton("Choose Indicators…")
                choose.clicked.connect(self._choose_indicators)
                row = QWidget()
                row.setLayout(hbox((self.indicator_summary, 1), choose))
                card.add_row("Indicators", row)
                context.downloads_changed.connect(self._update_indicator_summary)
            if Option.MODULE in options:
                module = QLineEdit()
                module.setPlaceholderText("All modules")
                module.textChanged.connect(lambda text: setattr(form, "module", text))
                self.list_modules = QPushButton("List Modules")
                self.list_modules.clicked.connect(self._list_modules)
                row = QWidget()
                row.setLayout(hbox(module, self.list_modules))
                card.add_row("Module", row)
            if Option.TIMEZONE in options:
                timezone = QLineEdit()
                timezone.setPlaceholderText(
                    "Read from the bug report"
                    if command_id == "androidCheckBugreport"
                    else "UTC"
                )
                timezone.textChanged.connect(
                    lambda text: setattr(form, "timezone", text)
                )
                card.add_row("Device timezone", timezone)
            if Option.FAST in options:
                fast = QCheckBox("Fast mode (skip time/resource consuming features)")
                fast.toggled.connect(lambda v: setattr(form, "fast", v))
                card.add(fast)
            if Option.HASHES in options:
                hashes = QCheckBox("Generate hashes of all analyzed files")
                hashes.toggled.connect(lambda v: setattr(form, "hashes", v))
                card.add(hashes)
            self.add_card(card)
        elif Option.HASHES in options:
            hashes = QCheckBox("Generate hashes of all decrypted files")
            hashes.toggled.connect(lambda v: setattr(form, "hashes", v))
            self.column.itemAt(self.column.count() - 1).widget().add(hashes)

        if Option.VIRUSTOTAL in options:
            card = Card("VirusTotal")
            vt = QCheckBox("Look up APK hashes on VirusTotal")
            card.add(vt)
            self.vt_key = QLineEdit()
            self.vt_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.vt_key.setPlaceholderText("Uses MVT_VT_API_KEY if empty")
            self.vt_key.textChanged.connect(
                lambda text: (setattr(form, "virustotal_api_key", text), self._sync())
            )
            key_row = card.add_row("API key", self.vt_key)
            delay = QSpinBox()
            delay.setRange(0, 120)
            delay.setSuffix(" s")
            delay.setValue(form.virustotal_delay)
            delay.valueChanged.connect(lambda v: setattr(form, "virustotal_delay", v))
            delay_row = card.add_row("Delay between requests", delay, stretch=False)
            card.add(
                caption(
                    "Sends hashes of non-system packages to VirusTotal. Requires network access."
                )
            )

            def toggled(on: bool):
                form.virustotal = on
                key_row.setVisible(on)
                delay_row.setVisible(on)
                self._sync()

            vt.toggled.connect(toggled)
            toggled(False)
            self.add_card(card)
        self.finish()

        # The action bar under the form.
        self.message = QLabel()
        self.message.setObjectName("caption")
        self.message.setWordWrap(True)
        self.view_results = QPushButton("View Results")
        self.view_results.clicked.connect(
            lambda: self.context_show_results(form.output_path)
        )
        self.check_decrypted = QPushButton("Check Decrypted Backup")
        self.check_decrypted.clicked.connect(self._check_decrypted)
        self.stop_button = QPushButton(icon("stop"), "Stop")
        self.stop_button.clicked.connect(context.runner.stop)
        self.run_button = QPushButton(icon("play", "#FFFFFF"), command.run_title)
        self.run_button.setObjectName("accent")
        self.run_button.setProperty("platform", command.tool.value)
        self.run_button.clicked.connect(self._run)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._shortcut_run)
        bar = QFrame()
        bar.setObjectName("actionBar")
        bar.setLayout(
            hbox(
                (self.message, 1),
                self.view_results,
                self.check_decrypted,
                None,
                self.stop_button,
                self.run_button,
                margins=0,
            )
        )
        bar.layout().setContentsMargins(24, 10, 24, 10)
        self.layout_.addWidget(bar)

        context.runner.state_changed.connect(self._sync)
        context.mvt_changed.connect(self._sync)
        self._update_indicator_summary()
        self._sync()

    def shown(self) -> None:
        # Another screen may have filled in the form (e.g. Check Decrypted
        # Backup). Fill every field before reading them back.
        values = [
            ("input_field", self.form.input_path),
            ("output_field", self.form.output_path),
        ]
        for name, value in values:
            if hasattr(self, name):
                field = getattr(self, name)
                field.blockSignals(True)
                field.set_path(value)
                field.blockSignals(False)
        self._update_indicator_summary()
        self._sync()

    def context_show_results(self, folder: str) -> None:
        self.context.settings.results_folder = folder
        self.context.navigate.emit("results")

    def _key_mode_changed(self, index: int) -> None:
        self.form.use_key_file = index == 1
        self.key_row.setVisible(index == 1)
        self.password_row.setVisible(index == 0)
        self._sync()

    def _read_fields(self) -> None:
        f = self.form
        if hasattr(self, "input_field"):
            f.input_path = self.input_field.path()
        if hasattr(self, "output_field"):
            f.output_path = self.output_field.path()
        if hasattr(self, "key_file"):
            f.key_file_path = self.key_file.path()
        if hasattr(self, "key_output"):
            f.key_file_output_path = self.key_output.path()
        if hasattr(self, "destination"):
            f.destination_path = self.destination.path()

    def _sync(self, *_args) -> None:
        if not hasattr(self, "run_button"):
            return  # still being built
        self._read_fields()
        runner = self.context.runner
        error = self.form.validation_error()
        running = runner.is_running
        finished = self.finished_code == 0 and not running
        self.message.setText(error or "")
        self.message.setVisible(bool(error) and not running)
        self.view_results.setVisible(
            finished
            and not error
            and self.command.produces_results
            and bool(self.form.output_path)
        )
        self.check_decrypted.setVisible(
            finished and not error and self.command.id == "iosDecryptBackup"
        )
        self.stop_button.setVisible(running)
        self.run_button.setEnabled(
            error is None and not running and self.context.installed_version is not None
        )
        if hasattr(self, "list_modules"):
            self.list_modules.setEnabled(not running)

    def _update_indicator_summary(self) -> None:
        if not hasattr(self, "indicator_summary"):
            return
        f = self.form
        extra = len(f.ioc_files)
        extra_text = (
            f" + {extra} extra file{'s' if extra != 1 else ''}" if extra else ""
        )
        if f.indicator_mode == "all":
            count = len(self.context.downloaded)
            text = (
                "None downloaded yet"
                if count == 0 and not extra
                else f"All downloaded ({count}){extra_text}"
            )
        else:
            picked = len(f.picked_indicators)
            text = (
                "None picked"
                if picked == 0 and not extra
                else f"{picked} picked{extra_text}"
            )
        self.indicator_summary.setText(text)

    def _choose_indicators(self) -> None:
        dialog = IndicatorPicker(self.context, self.form, self)
        dialog.exec()
        self._update_indicator_summary()
        self._sync()

    def _shortcut_run(self) -> None:
        if self.run_button.isEnabled() and self.isVisible():
            self._run()

    def _run(self) -> None:
        self._read_fields()
        self.finished_code = None
        if self.command.produces_results and self.form.output_path:
            os.makedirs(self.form.output_path, exist_ok=True)
        if self.command.id == "iosDecryptBackup":
            os.makedirs(self.form.destination_path, exist_ok=True)

        def done(code: int):
            self.finished_code = code
            self._sync()

        self.context.runner.run_mvt(self.form.invocation(), self.command.title, done)

    def _list_modules(self) -> None:
        self._read_fields()
        self.finished_code = None
        self.context.runner.run_mvt(
            self.form.invocation(list_modules_only=True),
            f"{self.command.title} — modules",
        )

    def _check_decrypted(self) -> None:
        self.context.form("iosCheckBackup").input_path = self.form.destination_path
        self.context.navigate.emit("iosCheckBackup")


# MARK: - Results


class ResultsPage(Page):
    COLUMNS = ["Level", "Module", "Time", "Message"]

    def __init__(self, context: Context):
        super().__init__("Results", scrolls=False)
        self.context = context
        self.alerts: list[dict] = []

        reload_button = QPushButton(icon("refresh"), "Reload")
        reload_button.clicked.connect(self.load)
        self.open_button = QPushButton(icon("open"), "Open in File Explorer")
        self.open_button.clicked.connect(lambda: open_path(self.folder()))
        self.header.addWidget(reload_button)
        self.header.addWidget(self.open_button)
        self.reload_button = reload_button

        top = Card()
        self.folder_field = PathField(
            PathField.FOLDER, "Choose a folder produced by a check"
        )
        self.folder_field.set_path(context.settings.results_folder)
        self.folder_field.changed.connect(self._folder_changed)
        top.add_row("Results folder", self.folder_field)
        self.analyzed = QLabel()
        self.analyzed.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.analyzed_row = top.add_row("Analyzed", self.analyzed)
        self.run_info = QLabel()
        self.run_row = top.add_row("Run", self.run_info)
        self.add_card(top)

        # Summary: alert counts, filter and the files the check wrote.
        self.badges = [Badge() for _ in ALERT_LEVELS]
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter alerts")
        self.filter.setClearButtonEnabled(True)
        self.filter.setMaximumWidth(240)
        self.files_button = QToolButton()
        self.files_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.files_menu = QMenu(self.files_button)
        self.files_button.setMenu(self.files_menu)
        summary = QWidget()
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.addLayout(
            hbox(*self.badges, None, self.filter, self.files_button)
        )
        summary_layout.addWidget(
            caption(
                "The lack of severe alerts does not mean a device is clean. Public indicators miss recent and "
                "targeted attacks — seek expert help if you have serious concerns."
            )
        )
        self.summary = summary
        self.column.addWidget(summary)

        self.model = QStandardItemModel(0, len(self.COLUMNS))
        self.model.setHorizontalHeaderLabels(self.COLUMNS)
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy.setFilterKeyColumn(-1)
        self.proxy.setSortRole(Qt.ItemDataRole.UserRole)
        self.filter.textChanged.connect(self.proxy.setFilterFixedString)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(False)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.resizeSection(0, 80)
        header.resizeSection(1, 170)
        header.resizeSection(2, 170)
        self.table.selectionModel().currentRowChanged.connect(self._show_detail)
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setPlaceholderText(
            "Select an alert to see the record that triggered it."
        )
        font = QFont("Cascadia Mono")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSizeF(9)
        self.detail.setFont(font)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.table)
        split.addWidget(self.detail)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setMinimumHeight(320)
        self.split = split
        self.column.addWidget(split, 1)

        self.empty = QLabel()
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setWordWrap(True)
        self.empty.setObjectName("empty")
        self.column.addWidget(self.empty, 1)
        self.load()

    def folder(self) -> str:
        return self.folder_field.path()

    def shown(self) -> None:
        if (
            self.folder_field.path()
            != os.path.normpath(self.context.settings.results_folder or ".")
            and self.context.settings.results_folder
        ):
            self.folder_field.set_path(self.context.settings.results_folder)
        else:
            self.load()

    def _folder_changed(self, _text: str) -> None:
        self.context.settings.results_folder = self.folder()
        self.load()

    def _empty(self, title: str, message: str) -> None:
        self.empty.setText(
            f"<p style='font-size:14pt; font-weight:600'>{title}</p><p>{message}</p>"
        )
        self.empty.setVisible(True)
        self.summary.setVisible(False)
        self.split.setVisible(False)

    def load(self) -> None:
        self.model.removeRows(0, self.model.rowCount())
        self.alerts = []
        self.detail.clear()
        self.files_menu.clear()
        self.analyzed_row.setVisible(False)
        self.run_row.setVisible(False)
        folder = self.folder()
        self.open_button.setEnabled(bool(folder) and os.path.isdir(folder))
        self.reload_button.setEnabled(bool(folder))
        if not folder:
            return self._empty(
                "No results selected",
                "Run a check with a results folder, or choose an existing one.",
            )
        if not os.path.isdir(folder):
            return self._empty(
                "Can't read results", f"The folder {folder} could not be read."
            )

        files = sorted(
            p
            for p in Path(folder).iterdir()
            if p.suffix.lower() in (".json", ".csv", ".log")
        )
        for path in files:
            size = path.stat().st_size
            self.files_menu.addAction(
                f"{path.name} — {_size(size)}", lambda p=path: open_path(p)
            )
        self.files_button.setText(f"Files ({len(files)})")
        self.files_button.setEnabled(bool(files))

        try:
            info = json.loads((Path(folder) / "info.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            info = {}
        if isinstance(info, dict) and info.get("target_path"):
            self.analyzed.setText(str(info["target_path"]))
            self.analyzed_row.setVisible(True)
        if isinstance(info, dict) and info.get("mvt_version") and info.get("date"):
            self.run_info.setText(f"{info['date']} · MVT {info['mvt_version']}")
            self.run_row.setVisible(True)

        alerts_path = Path(folder) / "alerts.json"
        if alerts_path.exists():
            try:
                raw = json.loads(alerts_path.read_text(encoding="utf-8"))
                self.alerts = (
                    [a for a in raw if isinstance(a, dict)]
                    if isinstance(raw, list)
                    else []
                )
            except (OSError, ValueError) as exc:
                return self._empty(
                    "Can't read results", f"alerts.json could not be parsed: {exc}"
                )

        self.empty.setVisible(False)
        self.summary.setVisible(True)
        self.split.setVisible(True)
        levels = dict(ALERT_LEVELS)
        for badge, (name, level) in zip(self.badges, ALERT_LEVELS):
            count = sum(
                1 for a in self.alerts if a.get("level", "INFORMATIONAL") == name
            )
            badge.show_count(level.alert_name, count, level_color(level))
        for index, alert in enumerate(self.alerts):
            level = levels.get(alert.get("level"), Level.INFO_ALERT)
            cells = [
                (level.alert_name, int(level)),
                (str(alert.get("module") or ""), None),
                (str(alert.get("event_time") or ""), None),
                (str(alert.get("message") or ""), None),
            ]
            row = []
            for text, sort in cells:
                item = QStandardItem(text)
                item.setData(
                    sort if sort is not None else text, Qt.ItemDataRole.UserRole
                )
                item.setData(index, Qt.ItemDataRole.UserRole + 1)
                item.setToolTip(text)
                row.append(item)
            row[0].setForeground(level_color(level))
            bold = QFont()
            bold.setBold(True)
            row[0].setFont(bold)
            self.model.appendRow(row)
        self.table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
        if not self.alerts:
            self.detail.setPlaceholderText("No alerts were recorded in this folder.")
        else:
            self.detail.setPlaceholderText(
                "Select an alert to see the record that triggered it."
            )

    def _show_detail(self, current, _previous) -> None:
        if not current.isValid():
            self.detail.clear()
            return
        alert = self.alerts[current.data(Qt.ItemDataRole.UserRole + 1)]
        parts = [
            str(alert.get("message") or ""),
            "",
            f"Module: {alert.get('module') or ''}",
        ]
        if alert.get("event_time"):
            parts.append(f"Time: {alert['event_time']}")
        if alert.get("matched_indicator") is not None:
            parts += ["", "Matched indicator:", _pretty(alert["matched_indicator"])]
        parts += ["", "Event:", _pretty(alert.get("event"))]
        self.detail.setPlainText("\n".join(parts))


def _pretty(value) -> str:
    try:
        return json.dumps(
            value, indent=2, sort_keys=True, ensure_ascii=False, default=str
        )
    except (TypeError, ValueError):
        return str(value)


def _size(size: int) -> str:
    for unit in ("bytes", "KB", "MB", "GB"):
        if size < 1000 or unit == "GB":
            return f"{size} {unit}" if unit == "bytes" else f"{size:.1f} {unit}"
        size /= 1000
    return str(size)


# MARK: - Settings


class SettingsDialog(QDialog):
    def __init__(self, context: Context, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)
        settings = context.settings
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        look = Card("Appearance")
        choice = QComboBox()
        for value, title in [
            ("system", "Match Windows"),
            ("light", "Light"),
            ("dark", "Dark"),
        ]:
            choice.addItem(title, value)
        choice.setCurrentIndex(max(0, choice.findData(settings.appearance)))
        choice.currentIndexChanged.connect(
            lambda _: setattr(settings, "appearance", choice.currentData())
        )
        look.add_row("Look", choice, stretch=False)
        layout.addWidget(look)

        behavior = Card("Behavior")
        for text, name in [
            ("Check for MVT updates on each run", "check_updates"),
            ("Check for indicator updates on each run", "check_indicator_updates"),
            ("Verbose (debug) output", "verbose"),
        ]:
            box = QCheckBox(text)
            box.setChecked(getattr(settings, name))
            box.toggled.connect(lambda value, n=name: setattr(settings, n, value))
            behavior.add(box)
        layout.addWidget(behavior)

        data = Card("Data")
        data.add(
            caption(f"Settings and indicators are kept in {environment.data_folder()}.")
        )
        layout.addWidget(data)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
