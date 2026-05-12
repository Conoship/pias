# Import standard library packages.
import sys

# Import third party packages.
from PySide6.QtGui import QIcon
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QApplication, QPushButton

# Import local packages.
from src.app.controllers.agent_pipeline_controller import AgentPipelineController
from src.app.controllers.button_controller import ButtonController


class App(object):
    # The title of the application that is displayed on the main window.
    _WINDOW_TITLE = "AI Agent to predict Damage Stability"

    # The path to the icon of the application that is displated on the window.
    _WINDOW_ICON_PATH = "src/app/assets/icon.png"

    # The path to the .ui file containing the layout and widgets of hte main window.
    _UI_FILE_PATH = "src/app/ui/agentMainWindow.ui"

    def __init__(self) -> None:
        """
        App containing the line edits for inputting files
        and specific variables that predicts based on the
        uploaded data the value of the attained index (A)
        and also gives a 95% CI for it.
        """
        # Window and application.
        self._app = QApplication(sys.argv)
        self._window = self._load_ui()

        # Controllers.
        self._agent_controller = AgentPipelineController(self._window)
        self._button_controller = ButtonController()

    def _load_ui(self) -> QWidget:
        """
        Method to load the `.ui` file describing the layout and widgets of the main window.

        Raises:
            RuntimeError:
                Error raised if the UI file was not loaded successfully.

        Returns:
            window (QWidget):
                The window containing the layout of the `.ui` file.
        """
        loader = QUiLoader()
        file = QFile(self._UI_FILE_PATH)
        file.open(QFile.OpenModeFlag.ReadOnly)
        window = loader.load(file)
        file.close()

        if window is None:
            raise RuntimeError("Failed to load the UI file...")

        return window

    def _configure_window(self) -> None:
        """
        Method to set the title, icon and resizability of the window according to their respective attributes.

        Raises:
            RuntimeError:
                Error raised if the `self._window` is `None` meaning the UI was not loaded successfully or not loaded at all.
        """
        if self._window is None:
            raise RuntimeError("Window has not been initialized...")

        self._window.setWindowTitle(self._WINDOW_TITLE)
        self._window.setWindowIcon(QIcon(self._WINDOW_ICON_PATH))
        self._window.setFixedSize(self._window.size())

    def _center_window(self) -> None:
        """
        Method to center the window on the screen.

        Raises:
            RuntimeError:
                Error raised if the `self._window` is `None` meaning the UI was not loaded successfully or not loaded at all.
        """
        if self._window is None:
            raise RuntimeError("Window has not been initialized...")

        screen = QGuiApplication.primaryScreen().geometry()
        window_geometry = self._window.frameGeometry()
        center_point = screen.center()
        window_geometry.moveCenter(center_point)
        self._window.move(window_geometry.topLeft())

    def _connect_file_browse_buttons(self) -> None:
        """
        Method to connect all file browse buttons to the correct line edits and file types using the `connect_file_browse_button` function.

        Raises:
            RuntimeError:
                Error raised if the `self._window` is `None` meaning the UI was not loaded successfully or not loaded at all.
        """
        if self._window is None:
            raise RuntimeError("Window has not been initialized...")

        # Connect Main Dimensions Button with searching for PDFs.
        self._button_controller.connect_file_browse_button(
            button_name="mainDimsBtn",
            window=self._window,
            caption="Browse Main Dimensions PDF",
            file_type="PDF Files (*.pdf)",
            line_edit_name="mainDimsLineEdit",
        )

        # Connect Openings Button with searching for PDFs.
        self._button_controller.connect_file_browse_button(
            button_name="openingsBtn",
            window=self._window,
            caption="Browse Openings PDF",
            file_type="PDF Files (*.pdf)",
            line_edit_name="openingsLineEdit",
        )

        # Connect Layouts Button with searching for XMLs.
        self._button_controller.connect_file_browse_button(
            button_name="layoutsBtn",
            window=self._window,
            caption="Browse Layouts XML",
            file_type="XML Files (*.xml)",
            line_edit_name="layoutsLineEdit",
        )

    def _connect_run_button(self) -> None:
        """
        Method to connect the Run button to the pipeline described in the `handle_agent_pipeline` function.

        Raises:
            RuntimeError:
                Error raised if the `self._window` is `None` meaning the UI was not loaded successfully or not loaded at all.
        """
        if self._window is None:
            raise RuntimeError("Window has not been initialized...")

        # Connect the Run button to the AI Agent pipeline.
        run_btn = self._window.findChild(QPushButton, "runBtn")
        if run_btn:
            run_btn.clicked.connect(self._agent_controller.handle_agent_pipeline)

    def _connect_buttons(self) -> None:
        """
        Method to connect all buttons to their respective actions, both file browse buttons and the run button.

        Raises:
            RuntimeError:
                Error raised if the `self._window` is `None` meaning the UI was not loaded successfully or not loaded at all.
        """
        if self._window is None:
            raise RuntimeError("Window has not been initialized...")

        self._connect_file_browse_buttons()
        self._connect_run_button()

    def run(self) -> None:
        """
        Method to run the application by doing first the following:
        1. Configure the window by calling `self._configure_window()`
        2. Center the window by calling `self._center_window()`
        3. Connect all buttons to their respective actions by calling `self._connect_buttons()`
        """
        # Configure the window.
        self._configure_window()

        # Center the window.
        self._center_window()

        # Connect all buttons.
        self._connect_buttons()

        # Run the application.
        self._window.show()
        sys.exit(self._app.exec())
