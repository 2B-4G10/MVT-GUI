"""Building blocks shared by the screens: icons, colours, cards, path
choosers and the output console."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, QUrl, Signal
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QIcon,
    QIconEngine,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .logs import Level

# MARK: - Colours


def is_dark() -> bool:
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


# Windows 11 text colours for each level: (light, dark).
_LEVEL_COLORS = {
    Level.WARNING: ("#9D5D00", "#FCE100"),
    Level.ERROR: ("#C42B1C", "#FF99A4"),
    Level.INFO_ALERT: ("#005FB8", "#60CDFF"),
    Level.LOW_ALERT: ("#8A6A00", "#FCE100"),
    Level.MEDIUM_ALERT: ("#C25E00", "#FFB45C"),
    Level.HIGH_ALERT: ("#C42B1C", "#FF99A4"),
    Level.CRITICAL_ALERT: ("#C42B1C", "#FF99A4"),
}

IOS_ACCENT = ("#005FB8", "#60CDFF")
ANDROID_GREEN = "#3DDC84"
SUCCESS = ("#0F7B0F", "#6CCB5F")


def pick(colors: tuple[str, str]) -> QColor:
    return QColor(colors[1] if is_dark() else colors[0])


def level_color(level: Level) -> QColor:
    if level in _LEVEL_COLORS:
        return pick(_LEVEL_COLORS[level])
    palette = QApplication.palette()
    if level == Level.COMMAND:
        return palette.color(QPalette.ColorRole.PlaceholderText)
    return palette.color(QPalette.ColorRole.Text)


# MARK: - Icons

# Glyphs of Windows 11's Segoe Fluent Icons font (Segoe MDL2 Assets on
# Windows 10 has the same code points).
GLYPHS = {
    "setup": "",
    "indicators": "",
    "results": "",
    "backup": "",
    "folder": "",
    "health": "",
    "unlock": "",
    "key": "",
    "sync": "",
    "package": "",
    "bug": "",
    "shield": "",
    "download": "",
    "refresh": "",
    "play": "",
    "stop": "",
    "copy": "",
    "delete": "",
    "open": "",
    "settings": "",
    "moon": "",
    "sun": "",
    "check": "",
    "warning": "",
    "error": "",
    "update": "",
    "add": "",
    "remove": "",
    "clear": "",
    "link": "",
    "phone": "",
}


def icon_font() -> QFont | None:
    families = set(QFontDatabase.families())
    for family in ("Segoe Fluent Icons", "Segoe MDL2 Assets"):
        if family in families:
            return QFont(family)
    return None


class GlyphIconEngine(QIconEngine):
    """Draws a font glyph in the palette's text colour, or a fixed colour."""

    def __init__(self, glyph: str, color: QColor | None = None):
        super().__init__()
        self.glyph = glyph
        self.color = color

    def paint(self, painter: QPainter, rect: QRect, mode: QIcon.Mode, state: QIcon.State) -> None:
        font = icon_font()
        if font is None:
            return
        palette = QApplication.palette()
        if mode == QIcon.Mode.Disabled:
            color = palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text)
        elif mode == QIcon.Mode.Selected or self.color is None:
            color = palette.color(QPalette.ColorRole.Text)
        else:
            color = self.color
        font.setPixelSize(max(8, round(min(rect.width(), rect.height()) * 0.85)))
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setFont(font)
        painter.setPen(color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.glyph)
        painter.restore()

    def pixmap(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QPixmap:
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        self.paint(painter, QRect(0, 0, size.width(), size.height()), mode, state)
        painter.end()
        return pixmap

    def clone(self) -> QIconEngine:
        return GlyphIconEngine(self.glyph, self.color)


def icon(name: str, color: QColor | str | None = None) -> QIcon:
    if icon_font() is None:
        return QIcon()
    return QIcon(GlyphIconEngine(GLYPHS[name], QColor(color) if isinstance(color, str) else color))


def app_icon() -> QIcon:
    """The macOS app's icon: the build copies it to resources/, and a source
    checkout reads it from the macOS app."""
    here = Path(__file__).resolve().parent
    folder = here / "resources"
    if not folder.is_dir():
        folder = here.parents[1] / "macos" / "MVTGUI" / "Assets.xcassets" / "AppIcon.appiconset"
    result = QIcon()
    for path in sorted(folder.glob("icon_*.png")):
        result.addFile(str(path))
    return result


def android_logo(size: QSize = QSize(17, 11)) -> QPixmap:
    """The Android robot's head, in Android green (credited in NOTICE)."""
    ratio = QApplication.primaryScreen().devicePixelRatio() if QApplication.primaryScreen() else 1
    pixmap = QPixmap(size * ratio)
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    unit = min(size.width(), size.height() / 0.62)
    ox, oy = (size.width() - unit) / 2, (size.height() - unit * 0.62) / 2

    def point(x: float, y: float) -> QPointF:
        return QPointF(ox + x * unit, oy + y * unit)

    green = QColor(ANDROID_GREEN)
    head = QPainterPath()
    radius = 0.46 * unit
    centre = point(0.5, 0.62)
    head.moveTo(centre.x() - radius, centre.y())
    head.arcTo(QRectF(centre.x() - radius, centre.y() - radius, 2 * radius, 2 * radius), 180, -180)
    head.closeSubpath()
    painter.fillPath(head, green)
    pen = QPen(green)
    pen.setWidthF(0.075 * unit)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.drawLine(point(0.29, 0.34), point(0.19, 0.05))
    painter.drawLine(point(0.71, 0.34), point(0.81, 0.05))
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(Qt.GlobalColor.black)
    eye = 0.05 * unit
    painter.drawEllipse(point(0.33, 0.46), eye, eye)
    painter.drawEllipse(point(0.67, 0.46), eye, eye)
    painter.end()
    return pixmap


# MARK: - Layout helpers


def open_path(path: str | Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def reveal(path: str | Path) -> None:
    """Shows a file or folder in File Explorer."""
    path = os.path.normpath(str(path))
    if sys.platform == "win32":
        subprocess.Popen(["explorer", "/select,", path])
    else:
        open_path(path if os.path.isdir(path) else os.path.dirname(path))


def open_url(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


def caption(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setObjectName("caption")
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


def link(text: str, url: str) -> QLabel:
    label = QLabel(f'<a href="{url}">{text}</a>')
    label.setOpenExternalLinks(True)
    label.setToolTip(url)
    return label


def heading(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("sectionHeading")
    return label


class Card(QFrame):
    """A rounded panel of settings rows, like the ones in Windows 11's
    Settings app."""

    def __init__(self, title: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(16, 12, 16, 12)
        self.outer.setSpacing(10)
        if title:
            self.outer.addWidget(heading(title))

    def add(self, widget: QWidget) -> QWidget:
        self.outer.addWidget(widget)
        return widget

    def add_row(self, label: str, widget: QWidget, stretch: bool = True) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        name = QLabel(label)
        name.setMinimumWidth(150)
        layout.addWidget(name)
        layout.addWidget(widget, 1 if stretch else 0)
        if not stretch:
            layout.addStretch(1)
        self.outer.addWidget(row)
        return row

    def add_layout(self, layout) -> None:
        self.outer.addLayout(layout)


def hbox(*items, margins: int = 0, spacing: int = 8) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setContentsMargins(margins, margins, margins, margins)
    layout.setSpacing(spacing)
    for item in items:
        # (item, stretch) gives an item the spare room.
        item, stretch = item if isinstance(item, tuple) else (item, 0)
        if item is None:
            layout.addStretch(1)
        elif isinstance(item, QWidget):
            layout.addWidget(item, stretch)
        else:
            layout.addLayout(item, stretch)
    return layout


def tool_button(icon_name: str, tooltip: str, callback) -> QToolButton:
    button = QToolButton()
    button.setIcon(icon(icon_name))
    button.setToolTip(tooltip)
    button.setAutoRaise(True)
    if icon_font() is None:
        button.setText(tooltip)
    button.clicked.connect(callback)
    return button


# MARK: - Path chooser


class PathField(QWidget):
    """A path box with Browse…, Show in File Explorer and Clear, that also
    accepts files dropped from File Explorer."""

    changed = Signal(str)

    FOLDER, FILE, FILE_OR_FOLDER, SAVE_FILE = range(4)

    def __init__(self, mode: int, placeholder: str = "", default_name: str = "", file_filter: str = "", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.default_name = default_name
        self.file_filter = file_filter
        self.setAcceptDrops(True)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder or "Type a path, drop it here or press Browse…")
        self.edit.setClearButtonEnabled(True)
        self.edit.textChanged.connect(self.changed.emit)

        self.reveal_button = tool_button("open", "Show in File Explorer", self._reveal)
        self.browse = QToolButton()
        self.browse.setText("Browse…")
        self.browse.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        if mode == self.FILE_OR_FOLDER:
            menu = QMenu(self.browse)
            menu.addAction("Choose a File…", lambda: self._choose(self.FILE))
            menu.addAction("Choose a Folder…", lambda: self._choose(self.FOLDER))
            self.browse.setMenu(menu)
            self.browse.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        else:
            self.browse.clicked.connect(lambda: self._choose(self.mode))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.reveal_button)
        layout.addWidget(self.browse)
        self.changed.connect(lambda text: self.reveal_button.setEnabled(bool(text) and os.path.exists(text)))
        self.reveal_button.setEnabled(False)

    def path(self) -> str:
        text = self.edit.text().strip().strip('"')
        return os.path.normpath(text) if text else ""

    def set_path(self, path: str) -> None:
        self.edit.setText(os.path.normpath(path) if path else "")

    def _reveal(self) -> None:
        if self.path():
            reveal(self.path())

    def _start_folder(self) -> str:
        current = self.path()
        if current and os.path.isdir(current):
            return current
        if current and os.path.isdir(os.path.dirname(current)):
            return os.path.dirname(current)
        return str(Path.home())

    def _choose(self, mode: int) -> None:
        start = self._start_folder()
        if mode == self.FOLDER:
            chosen = QFileDialog.getExistingDirectory(self, "Choose a Folder", start)
        elif mode == self.SAVE_FILE:
            chosen, _ = QFileDialog.getSaveFileName(
                self, "Save As", os.path.join(start, os.path.basename(self.path()) or self.default_name)
            )
        else:
            chosen, _ = QFileDialog.getOpenFileName(self, "Choose a File", start, self.file_filter)
        if chosen:
            self.set_path(chosen)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = [u for u in event.mimeData().urls() if u.isLocalFile()]
        if urls:
            self.set_path(urls[0].toLocalFile())
            event.acceptProposedAction()


# MARK: - Console


class Badge(QLabel):
    """A small coloured count, like "3 High"."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("badge")

    def show_count(self, name: str, count: int, color: QColor) -> None:
        self.setText(f"{count} {name}")
        background = QColor(color)
        background.setAlphaF(0.18)
        self.setStyleSheet(
            f"QLabel#badge {{ color: {color.name()}; background: {background.name(QColor.NameFormat.HexArgb)};"
            f" border-radius: 9px; padding: 1px 8px; font-weight: 600; }}"
        )


class ConsoleView(QFrame):
    """Streams the shared runner's output."""

    def __init__(self, runner, parent=None):
        super().__init__(parent)
        self.runner = runner
        self.setObjectName("console")

        self.status = QLabel()
        self.title = QLabel("Output")
        self.title.setObjectName("consoleTitle")
        self.badges = [Badge() for _ in range(5)]
        self.alerts_only = QCheckBox("Alerts only")
        self.alerts_only.toggled.connect(self.render_all)
        self.auto_scroll = QCheckBox("Auto-scroll")
        self.auto_scroll.setChecked(True)
        self.copy_button = tool_button("copy", "Copy output", self._copy)
        self.clear_button = tool_button("delete", "Clear output", lambda: self.runner.clear())

        header = QHBoxLayout()
        header.setContentsMargins(12, 6, 8, 6)
        header.setSpacing(8)
        header.addWidget(self.status)
        header.addWidget(self.title)
        for badge in self.badges:
            header.addWidget(badge)
        header.addStretch(1)
        header.addWidget(self.alerts_only)
        header.addWidget(self.auto_scroll)
        header.addWidget(self.copy_button)
        header.addWidget(self.clear_button)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setObjectName("consoleText")
        self.text.setMaximumBlockCount(50_000)
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.text.setPlaceholderText("Output from MVT will appear here.")
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        if "Cascadia Mono" in QFontDatabase.families():
            font = QFont("Cascadia Mono")
        font.setPointSizeF(9)
        self.text.setFont(font)
        self.text.setFrameShape(QFrame.Shape.NoFrame)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("divider")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(line)
        layout.addWidget(self.text, 1)

        runner.line_added.connect(self._add_line)
        runner.cleared.connect(self.render_all)
        runner.state_changed.connect(self.update_header)
        QGuiApplication.styleHints().colorSchemeChanged.connect(lambda _: self.render_all())
        self.update_header()

    def _visible(self, level: Level) -> bool:
        return not self.alerts_only.isChecked() or level.is_alert or level in (Level.ERROR, Level.COMMAND)

    def _insert(self, cursor: QTextCursor, text: str, level: Level) -> None:
        fmt = QTextCharFormat()
        fmt.setForeground(level_color(level))
        if level == Level.CRITICAL_ALERT:
            fmt.setFontWeight(QFont.Weight.Bold)
        if not self.text.document().isEmpty():
            cursor.insertBlock()
        cursor.insertText(text, fmt)

    def _add_line(self, text: str, level: int) -> None:
        level = Level(level)
        if level.is_alert:
            self.update_header()
        if not self._visible(level):
            return
        bar = self.text.verticalScrollBar()
        at_bottom = bar.value() >= bar.maximum() - 4
        cursor = QTextCursor(self.text.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._insert(cursor, text, level)
        if self.auto_scroll.isChecked() or at_bottom:
            bar.setValue(bar.maximum())

    def render_all(self) -> None:
        self.text.clear()
        cursor = QTextCursor(self.text.document())
        cursor.beginEditBlock()
        for text, level in self.runner.lines:
            if self._visible(level):
                self._insert(cursor, text, level)
        cursor.endEditBlock()
        self.text.verticalScrollBar().setValue(self.text.verticalScrollBar().maximum())
        self.update_header()

    def update_header(self) -> None:
        runner = self.runner
        self.title.setText(runner.title or "Output")
        if runner.is_running:
            self.status.setText("Running…")
            self.status.setStyleSheet("")
        elif runner.last_exit_code is not None:
            ok = runner.last_exit_code == 0
            self.status.setText("✓" if ok else "✕")
            color = pick(SUCCESS) if ok else level_color(Level.ERROR)
            self.status.setStyleSheet(f"color: {color.name()}; font-weight: 700;")
        else:
            self.status.setText("")
        levels = [Level.CRITICAL_ALERT, Level.HIGH_ALERT, Level.MEDIUM_ALERT, Level.LOW_ALERT, Level.INFO_ALERT]
        for badge, level in zip(self.badges, levels):
            count = runner.alert_counts.get(level, 0)
            badge.setVisible(count > 0)
            if count:
                badge.show_count(level.alert_name, count, level_color(level))
        self.copy_button.setEnabled(bool(runner.lines))
        self.clear_button.setEnabled(bool(runner.lines) and not runner.is_running)

    def _copy(self) -> None:
        QApplication.clipboard().setText("\n".join(text for text, _ in self.runner.lines))


def expanding() -> QSizePolicy:
    return QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
