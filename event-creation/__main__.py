"""Event Creation GUI — entry point.

Builds the Qt application, applies the theme and opens the main window.
Logic lives in event_creation.core (WAAPI + naming, no GUI imports);
the interface lives in event_creation.ui.
"""
import logging
import sys
from pathlib import Path

# Allow running both as `python __main__.py` and as a frozen exe
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication

from event_creation.core.settings import SettingsManager
from event_creation.ui import theme
from event_creation.ui.main_window import MainWindow


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = QApplication(sys.argv)
    theme.load_fonts()
    app.setStyleSheet(theme.build_qss())

    settings = SettingsManager()
    window = MainWindow(settings)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
