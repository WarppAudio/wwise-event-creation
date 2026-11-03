"""Dark theme: single palette dict, QSS generated from it, font resolution.

Colors and typography follow the design spec (CLAUDE_CODE_PROMPT.md):
blue = primary action / selected target, green = container creation / success,
yellow = warnings, red = errors.
"""
from string import Template

from PySide6.QtGui import QFont, QFontDatabase

from ..paths import resource_dir

PALETTE = {
    "window_bg":     "#15171b",
    "bar_bg":        "#101216",
    "panel_bg":      "#0f1115",
    "list_bg":       "#121418",
    "settings_bg":   "#181b20",
    "border":        "#23272e",
    "border2":       "#2e343d",
    "border3":       "#3a424e",
    "text_strong":   "#e6e9ee",
    "text":          "#c3cad4",
    "text_dim":      "#8b939f",
    "text_faint":    "#5f6875",
    "text_disabled": "#4f5866",
    "accent":        "#2d7ff9",
    "accent_light":  "#4a9eff",
    "selection_bg":  "#16202e",
    "green":         "#3ecf8e",
    "green_bg":      "#12291f",
    "green_border":  "#1f4a36",
    "green_border2": "#2a5c46",
    "green_text":    "#8fe0bb",
    "warning":       "#c9a227",
    "error":         "#c0392b",
    "scroll_thumb":  "#39414d",
    "swatch_wwu":    "#4f5866",
    "swatch_folder": "#5d6675",
    "disabled_bg":   "#1d222a",
    "plus_disabled_bg": "#16191e",
    "plus_disabled_fg": "#3d4551",
}

FONT_UI = "Segoe UI"
FONT_MONO = "Consolas"


def load_fonts() -> None:
    """Register bundled fonts (resources/fonts/*.ttf|otf) and pick families.

    Prefers Inter Tight (UI) and IBM Plex Mono (monospace); falls back to
    Segoe UI / Consolas when the files are not bundled or not installed.
    """
    global FONT_UI, FONT_MONO
    fonts_dir = resource_dir() / "fonts"
    if fonts_dir.is_dir():
        for f in fonts_dir.iterdir():
            if f.suffix.lower() in (".ttf", ".otf"):
                QFontDatabase.addApplicationFont(str(f))
    families = set(QFontDatabase.families())
    for candidate in ("Inter Tight", "Segoe UI"):
        if candidate in families:
            FONT_UI = candidate
            break
    for candidate in ("IBM Plex Mono", "Consolas"):
        if candidate in families:
            FONT_MONO = candidate
            break


def mono_font(px: float, weight: int = QFont.Normal) -> QFont:
    f = QFont(FONT_MONO)
    f.setPixelSize(round(px))
    f.setWeight(QFont.Weight(weight))
    return f


_QSS = Template("""
* { outline: none; }

QMainWindow, QWidget#Central { background: $window_bg; }

QWidget#Toolbar, QWidget#StatusBar { background: $bar_bg; }
QWidget#Toolbar { border-bottom: 1px solid $border; }
QWidget#StatusBar { border-top: 1px solid $border; }

QLabel { color: $text; background: transparent; }
QLabel#TitleLabel { color: $text_strong; font-family: "$font_ui"; font-size: 13px; font-weight: 600; }
QLabel#VersionLabel, QLabel#ProjectLabel { color: $text_dim; font-family: "$font_mono"; font-size: 11px; }
QLabel#StatusSentence { color: $text_dim; font-family: "$font_mono"; font-size: 12px; }
QLabel#StatusSentence[warning="true"] { color: $warning; }
QLabel#FieldLabel { color: $text_dim; font-family: "$font_ui"; font-size: 11px; }
QLabel#GroupHeader { color: $text_dim; font-family: "$font_mono"; font-size: 10px; }
QLabel#FormError { color: $error; font-family: "$font_ui"; font-size: 11px; }
QLabel#MutedCaption { color: #6b7482; font-family: "$font_ui"; font-size: 11px; }

QSplitter::handle { background: $border; width: 1px; }

QWidget#LeftColumn { background: $list_bg; }

QLineEdit {
    background: $panel_bg; color: $text_strong;
    border: 1px solid $border2; border-radius: 6px;
    padding: 5px 8px;
    font-family: "$font_mono"; font-size: 12px;
    selection-background-color: $accent;
}
QLineEdit:focus { border: 1px solid $accent; }
QLineEdit[invalid="true"] { border: 1px solid $error; }
QLineEdit#ContainerNameEdit {
    border: 1px solid $green; font-size: 13px; min-height: 22px;
}
QLineEdit#ContainerNameEdit:focus { border: 1px solid $green; }
QLineEdit#ContainerNameEdit[invalid="true"] { border: 1px solid $error; }

QListView#TargetList {
    background: $list_bg; border: none;
    font-family: "$font_mono";
}
QListWidget#LogList {
    background: transparent; border: none;
    font-family: "$font_mono"; font-size: 12px; color: #d5dae2;
}
QListWidget#LogList::item { padding: 2px 4px; }
QListWidget#LogList::item:selected { background: $selection_bg; }

QScrollBar:vertical {
    background: transparent; width: 10px; margin: 0;
}
QScrollBar::handle:vertical {
    background: $scroll_thumb; border-radius: 5px; min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: $border3; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: $scroll_thumb; border-radius: 5px; min-width: 24px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

QPushButton {
    background: transparent; color: $text;
    border: 1px solid $border2; border-radius: 6px;
    padding: 5px 12px;
    font-family: "$font_ui"; font-size: 12px;
}
QPushButton:hover { background: $selection_bg; }

QPushButton#CreateButton {
    background: $accent; color: white; border: none;
    font-size: 12px; font-weight: 600; padding: 7px 18px;
}
QPushButton#CreateButton:hover { background: $accent_light; }
QPushButton#CreateButton:disabled { background: $disabled_bg; color: $text_disabled; }

QPushButton#SettingsButton {
    background: transparent; color: $text_dim; border: 1px solid $border2;
}
QPushButton#SettingsButton:checked { background: $accent; color: white; border: none; }

QPushButton#OkButton {
    background: $green_border; color: $green_text; border: none; font-weight: 600;
}
QPushButton#OkButton:hover { background: $green_border2; }

QToolButton#PlusButton {
    background: $green_bg; border: 1px solid $green; border-radius: 6px;
    color: $green; font-size: 14px; font-weight: 600;
    padding: 2px 10px;
}
QToolButton#PlusButton::menu-indicator { image: none; }
QToolButton#PlusButton:hover { background: $green_border; }
QToolButton#PlusButton:disabled {
    background: $plus_disabled_bg; border: 1px solid $border; color: $plus_disabled_fg;
}

QToolButton#RefreshButton, QToolButton#CloseButton, QToolButton#LogHeader {
    background: transparent; border: 1px solid $border2; border-radius: 6px;
    color: $text_dim; padding: 3px 8px;
}
QToolButton#RefreshButton:hover, QToolButton#CloseButton:hover { background: $selection_bg; color: $text_strong; }
QToolButton#CloseButton { border: none; font-size: 13px; }
QToolButton#LogHeader {
    border: none; color: $text_dim;
    font-family: "$font_mono"; font-size: 10px;
}

QMenu {
    background: $settings_bg; border: 1px solid $border2; border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    color: $text; padding: 6px 14px; border-radius: 5px;
    font-family: "$font_ui"; font-size: 12px;
}
QMenu::item:selected { background: $selection_bg; color: $text_strong; }
QMenu::item:disabled { color: $text_faint; font-family: "$font_mono"; font-size: 9px; }

QCheckBox { color: #9aa3af; font-family: "$font_ui"; font-size: 12px; spacing: 7px; }
QCheckBox:checked { color: #d5dae2; }
QCheckBox::indicator { width: 15px; height: 15px; border-radius: 4px; border: 1px solid $text_disabled; background: transparent; }
QCheckBox::indicator:checked { background: $accent; border: none; image: url("$check_icon"); }

QFrame#ContainerForm { background: #101c17; border: 1px solid $green_border2; border-radius: 9px; }
QFrame#ContainerFormHeader { background: $green_bg; border: none; border-bottom: 1px solid $green_border; border-top-left-radius: 9px; border-top-right-radius: 9px; }
QLabel#ContainerFormTitle { color: $green_text; font-family: "$font_ui"; font-size: 12px; font-weight: 600; }

QFrame#SuccessBar { background: rgba(16, 32, 26, 0.55); border: 1px solid $green_border; border-radius: 9px; }
QLabel#SuccessCount { color: $text_strong; font-family: "$font_ui"; font-size: 16px; font-weight: 700; }
QLabel#SuccessPath { color: $text_dim; font-family: "$font_mono"; font-size: 11px; }

QFrame#Placeholder { background: transparent; border: 1px dashed #262c34; border-radius: 9px; }
QLabel#PlaceholderText { color: $text_disabled; font-family: "$font_ui"; font-size: 11px; }

QFrame#SettingsPanel { background: $settings_bg; border-left: 1px solid $border2; }
QLabel#SettingsTitle { color: $text_strong; font-family: "$font_ui"; font-size: 14px; font-weight: 600; }
QFrame#LogCard { background: $panel_bg; border: 1px solid $border; border-radius: 9px; }
""")


def build_qss() -> str:
    check_icon = (resource_dir() / "icons" / "check.svg").as_posix()
    return _QSS.substitute(PALETTE, font_ui=FONT_UI, font_mono=FONT_MONO, check_icon=check_icon)
