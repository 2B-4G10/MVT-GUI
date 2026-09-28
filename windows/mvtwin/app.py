"""The main window and the app's entry point."""

from __future__ import annotations

import argparse
import os
import sys

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QStyleFactory,
    QVBoxLayout,
    QWidget,
)

from . import __version__, environment
from .commands import ANDROID_COMMANDS, COMMANDS, IOS_COMMANDS
from .context import Context
from .pages import CommandPage, IndicatorsPage, ResultsPage, SettingsDialog, SetupPage
from .widgets import (
    ANDROID_GREEN,
    IOS_ACCENT,
    SUCCESS,
    ConsoleView,
    android_logo,
    app_icon,
    icon,
    is_dark,
    pick,
    tool_button,
)

APP_USER_MODEL_ID = "2B-4G10.MVTForWindows"


def stylesheet() -> str:
    dark = is_dark()
    card = "rgba(255,255,255,0.05)" if dark else "rgba(255,255,255,0.75)"
    border = "rgba(0,0,0,0.30)" if dark else "rgba(0,0,0,0.07)"
    muted = "#C5C5C5" if dark else "#5C5C5C"
    window = "#202020" if dark else "#F3F3F3"
    sidebar = "#1C1C1C" if dark else "#EBEBEB"
    hover = "rgba(255,255,255,0.06)" if dark else "rgba(0,0,0,0.04)"
    selected = "rgba(255,255,255,0.09)" if dark else "rgba(0,0,0,0.06)"
    accent = pick(IOS_ACCENT).name()
    accent_text = "#000000" if dark else "#FFFFFF"
    return f"""
    QMainWindow, QDialog, #pageBody, #page {{ background: {window}; }}
    QScrollArea#pageScroll, QScrollArea#pageScroll > QWidget > QWidget {{ background: transparent; }}
    QFrame#card {{ background: {card}; border: 1px solid {border}; border-radius: 8px; }}
    QFrame#card QLabel {{ background: transparent; }}
    QLabel#pageTitle {{ font-size: 20pt; font-weight: 600; }}
    QLabel#sectionHeading, QLabel#strong {{ font-weight: 600; }}
    QLabel#sectionHeading {{ font-size: 11pt; }}
    QLabel#caption {{ color: {muted}; }}
    QLabel#empty {{ color: {muted}; }}
    QListWidget#sidebar {{ background: {sidebar}; border: none; padding: 4px 6px; outline: 0; }}
    QListWidget#sidebar::item {{ padding: 7px 8px; border-radius: 5px; margin: 1px 0; }}
    QListWidget#sidebar::item:hover {{ background: {hover}; }}
    QListWidget#sidebar::item:selected {{ background: {selected}; color: palette(text); }}
    QWidget#sidebarPane {{ background: {sidebar}; }}
    QFrame#console, QFrame#actionBar {{ background: {card}; border-top: 1px solid {border}; }}
    QPlainTextEdit#consoleText {{ background: transparent; }}
    QLabel#consoleTitle {{ font-weight: 600; }}
    QPushButton#accent {{ background: {accent}; color: {accent_text}; border: 1px solid {accent};
                          border-radius: 4px; padding: 5px 14px; font-weight: 600; }}
    QPushButton#accent:hover {{ background: {accent}E6; }}
    QPushButton#accent[platform="mvt-android"] {{ background: #1B8A4B; border-color: #1B8A4B; color: #FFFFFF; }}
    QPushButton#accent:disabled {{ background: {border}; border-color: {border}; color: {muted}; }}
    """


class MainWindow(QMainWindow):
    def __init__(self, context: Context, start: str = "setup"):
        super().__init__()
        self.context = context
        self.setWindowTitle(environment.APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(1180, 820)
        self.setMinimumSize(QSize(900, 600))

        self.pages: dict[str, QWidget] = {}
        self.stack = QStackedWidget()
        self.console = ConsoleView(context.runner)

        right = QSplitter(Qt.Orientation.Vertical)
        right.addWidget(self.stack)
        right.addWidget(self.console)
        right.setStretchFactor(0, 3)
        right.setStretchFactor(1, 2)
        right.setSizes([480, 300])
        right.setChildrenCollapsible(False)
        self.right = right

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setIconSize(QSize(20, 20))
        self._item("setup", "Setup", "setup")
        self._item("indicators", "Indicators", "indicators")
        self._item("results", "Results", "results")
        self._header("iOS", icon("phone", pick(IOS_ACCENT)).pixmap(14, 14))
        for command_id in IOS_COMMANDS:
            command = COMMANDS[command_id]
            self._item(command_id, command.title, command.icon, pick(IOS_ACCENT).name())
        self._header("Android", android_logo())
        for command_id in ANDROID_COMMANDS:
            command = COMMANDS[command_id]
            self._item(command_id, command.title, command.icon, ANDROID_GREEN)
        self.sidebar.currentItemChanged.connect(self._selected)

        self.status = QLabel()
        self.status.setObjectName("caption")
        self.status.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status.mousePressEvent = lambda _e: self.show_page("setup")
        self.dark = QCheckBox()
        self.dark.setToolTip("Dark mode")
        self.dark.toggled.connect(self._dark_toggled)
        settings_button = tool_button("settings", "Settings", self._settings)
        footer = QHBoxLayout()
        footer.setContentsMargins(12, 6, 8, 8)
        footer.addWidget(self.status, 1)
        self.theme_icon = QLabel()
        footer.addWidget(self.theme_icon)
        footer.addWidget(self.dark)
        footer.addWidget(settings_button)

        pane = QWidget()
        pane.setObjectName("sidebarPane")
        pane_layout = QVBoxLayout(pane)
        pane_layout.setContentsMargins(0, 8, 0, 0)
        pane_layout.setSpacing(0)
        pane_layout.addWidget(self.sidebar, 1)
        pane_layout.addLayout(footer)
        pane.setFixedWidth(250)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(pane)
        layout.addWidget(right, 1)
        self.setCentralWidget(central)

        context.navigate.connect(self.show_page)
        context.mvt_changed.connect(self._update_status)
        context.error.connect(lambda message: QMessageBox.warning(self, "Something went wrong", message))
        QGuiApplication.styleHints().colorSchemeChanged.connect(lambda _: self._restyle())
        self._update_status()
        self._restyle()
        self.show_page(start if start in ("setup", "indicators", "results") or start in COMMANDS else "setup")

    def _item(self, key: str, title: str, glyph: str, color: str | None = None) -> None:
        item = QListWidgetItem(icon(glyph, color), title)
        item.setData(Qt.ItemDataRole.UserRole, key)
        item.setSizeHint(QSize(0, 36))
        self.sidebar.addItem(item)

    def _header(self, title: str, pixmap) -> None:
        item = QListWidgetItem()
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setSizeHint(QSize(0, 34))
        label = QWidget()
        row = QHBoxLayout(label)
        row.setContentsMargins(10, 10, 0, 0)
        row.setSpacing(6)
        logo = QLabel()
        logo.setPixmap(pixmap)
        text = QLabel(title)
        text.setObjectName("caption")
        row.addWidget(logo)
        row.addWidget(text)
        row.addStretch(1)
        self.sidebar.addItem(item)
        self.sidebar.setItemWidget(item, label)

    def page(self, key: str) -> QWidget:
        if key not in self.pages:
            if key == "setup":
                page = SetupPage(self.context)
            elif key == "indicators":
                page = IndicatorsPage(self.context)
            elif key == "results":
                page = ResultsPage(self.context)
            else:
                page = CommandPage(self.context, key)
            page.setObjectName("page")
            self.pages[key] = page
            self.stack.addWidget(page)
        return self.pages[key]

    def show_page(self, key: str) -> None:
        for row in range(self.sidebar.count()):
            item = self.sidebar.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == key:
                if self.sidebar.currentItem() is not item:
                    self.sidebar.setCurrentItem(item)
                    return  # _selected shows it
        page = self.page(key)
        self.stack.setCurrentWidget(page)
        # Results has no console; every other screen shows MVT's output.
        self.console.setVisible(key != "results")
        page.shown()

    def _selected(self, current: QListWidgetItem | None, _previous) -> None:
        if current is not None:
            self.show_page(current.data(Qt.ItemDataRole.UserRole))

    def _update_status(self) -> None:
        c = self.context
        if c.installed_version and c.is_outdated:
            self.status.setText(f"<span style='color:#C25E00'>●</span> MVT {c.installed_version} · update available")
        elif c.installed_version:
            self.status.setText(f"<span style='color:{pick(SUCCESS).name()}'>●</span> MVT {c.installed_version}")
        else:
            self.status.setText("<span style='color:#C25E00'>●</span> MVT not found")
        self.status.setToolTip(f"{environment.APP_NAME} {__version__}")

    def _dark_toggled(self, on: bool) -> None:
        if on != is_dark():
            self.context.settings.appearance = "dark" if on else "light"
            apply_appearance(self.context.settings.appearance)

    def _restyle(self) -> None:
        QApplication.instance().setStyleSheet(stylesheet())
        self.dark.blockSignals(True)
        self.dark.setChecked(is_dark())
        self.dark.blockSignals(False)
        self.theme_icon.setPixmap(icon("moon" if is_dark() else "sun").pixmap(14, 14))
        self._update_status()

    def _settings(self) -> None:
        SettingsDialog(self.context, self).exec()
        apply_appearance(self.context.settings.appearance)


def apply_appearance(appearance: str) -> None:
    scheme = {"light": Qt.ColorScheme.Light, "dark": Qt.ColorScheme.Dark}.get(appearance, Qt.ColorScheme.Unknown)
    QGuiApplication.styleHints().setColorScheme(scheme)


def set_app_user_model_id() -> None:
    """Groups the app's windows under its own taskbar button and icon, not
    Python's."""
    if sys.platform == "win32":
        import ctypes

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except (AttributeError, OSError):
            pass


def parse_arguments(argv: list[str]) -> argparse.Namespace:
    """Like the macOS app, the app can open on a given screen:
    -startScreen results -resultsFolder <path>. Screens: setup, indicators,
    results, or a command such as iosCheckBackup (with -inputPath and
    -outputPath)."""
    parser = argparse.ArgumentParser(prog=environment.APP_NAME, add_help=False)
    parser.add_argument("-startScreen", default="setup")
    parser.add_argument("-resultsFolder")
    parser.add_argument("-inputPath")
    parser.add_argument("-outputPath")
    parser.add_argument("-appearance", choices=["system", "light", "dark"])
    # Saves a picture of the window after it has loaded, then quits (used
    # for the README's screenshots and as a smoke test).
    parser.add_argument("-screenshot")
    args, _unknown = parser.parse_known_args(argv)
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(sys.argv[1:] if argv is None else argv)
    set_app_user_model_id()
    app = QApplication(sys.argv[:1])
    app.setApplicationName(environment.APP_NAME)
    app.setApplicationVersion(__version__)
    app.setWindowIcon(app_icon())
    if "windows11" in [name.lower() for name in QStyleFactory.keys()]:
        app.setStyle("windows11")

    context = Context()
    if args.appearance:
        context.settings.appearance = args.appearance
    apply_appearance(context.settings.appearance)
    if args.resultsFolder:
        context.settings.results_folder = args.resultsFolder
    if args.startScreen in COMMANDS:
        form = context.form(args.startScreen)
        form.input_path = args.inputPath or ""
        form.output_path = args.outputPath or ""
    context.refresh_mvt()

    window = MainWindow(context, args.startScreen)
    window.show()

    if args.screenshot:
        def capture():
            window.grab().save(args.screenshot)
            app.quit()

        # Long enough for the indicator list and the update check to load.
        QTimer.singleShot(int(float(os.environ.get("MVTWIN_SCREENSHOT_DELAY", "8")) * 1000), capture)
    elif context.installed_version is None:
        QTimer.singleShot(0, lambda: window.show_page("setup"))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
