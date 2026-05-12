# Import standard library packages.
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Import third party packages.
from PySide6.QtCore import QFile
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

# Import local packages.
from src.app.controller import connect_file_browse_button, handle_agent_pipeline


class App:
    """Main application class for the AI Agent UI."""

    _WINDOW_TITLE: str = "AI Agent to predict Damage Stability"
    _WINDOW_ICON_PATH: str = "src/app/assets/icons/icon.png"
    _UI_FILE_PATH: str = "src/app/ui/agentMainWindow.ui"

    def __init__(self) -> None:
        """Initialize the application."""
        self._app: QApplication = QApplication(sys.argv)
        self._window: QWidget = self._load_ui()

    def run(self) -> None:
        """Load, configure, and run the application."""

        self._configure_window()
        self._center_window()
        self._connect_buttons()

        self._window.show()

        sys.exit(self._app.exec())

    def _load_ui(self) -> QWidget:
        """Load the UI from the .ui file.

        Returns:
            QWidget: The loaded main window widget.
        """
        loader = QUiLoader()

        ui_file = QFile(self._UI_FILE_PATH)
        ui_file.open(QFile.OpenModeFlag.ReadOnly)

        window = loader.load(ui_file)

        ui_file.close()

        if window is None:
            raise RuntimeError("Failed to load UI file.")

        return window

    def _configure_window(self) -> None:
        """Configure the main window properties."""
        if self._window is None:
            raise RuntimeError("Window has not been initialized.")

        self._window.setWindowTitle(self._WINDOW_TITLE)
        self._window.setWindowIcon(QIcon(self._WINDOW_ICON_PATH))
        self._window.setFixedSize(self._window.size())

    def _center_window(self) -> None:
        """Center the window on the primary screen."""
        if self._window is None:
            raise RuntimeError("Window has not been initialized.")

        screen_geometry = QGuiApplication.primaryScreen().geometry()

        window_geometry = self._window.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())

        self._window.move(window_geometry.topLeft())

    def _connect_buttons(self) -> None:
        """Connect all UI buttons and actions."""
        if self._window is None:
            raise RuntimeError("Window has not been initialized.")

        self._connect_file_browse_buttons()
        self._connect_run_button()

    def _connect_file_browse_buttons(self) -> None:
        """Connect file browse buttons to file dialogs."""
        if self._window is None:
            raise RuntimeError("Window has not been initialized.")

        connect_file_browse_button(
            button_name="mainDimsBtn",
            window=self._window,
            caption="Browse Main Dimensions PDF",
            file_type="PDF Files (*.pdf)",
            line_edit_name="mainDimsLineEdit",
        )

        connect_file_browse_button(
            button_name="openingsBtn",
            window=self._window,
            caption="Browse Openings PDF",
            file_type="PDF Files (*.pdf)",
            line_edit_name="openingsLineEdit",
        )

        connect_file_browse_button(
            button_name="internalSubdivBtn",
            window=self._window,
            caption="Browse Internal Subdivision XML",
            file_type="XML Files (*.xml)",
            line_edit_name="internalSubdivLineEdit",
        )

    def _connect_run_button(self) -> None:
        """Connect the run button to the AI pipeline."""
        if self._window is None:
            raise RuntimeError("Window has not been initialized.")

        run_button = self._window.findChild(QPushButton, "runBtn")

        if run_button:
            run_button.clicked.connect(lambda: handle_agent_pipeline(self._window))


def main() -> None:
    """Run the desktop application."""
    App().run()
