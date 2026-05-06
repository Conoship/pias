# Import standard library packages.
import sys

# Import third party packages.
from PySide6.QtGui import QIcon
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QPushButton
)

# Import local packages.
from models.random_forest_baseline import RandomForestBaseline
from ui.controller import *


def main():
    # Create the App and load the UI.
    app = QApplication(sys.argv)
    loader = QUiLoader()
    file = QFile("ui/agentMainWindow.ui")
    file.open(QFile.OpenModeFlag.ReadOnly)

    # Main Window Configuration.
    window = loader.load(file)
    window.setWindowTitle("AI Agent to predict Damage Stability")
    window.setWindowIcon(QIcon("assets/icon.png"))
    window.setFixedSize(window.size())

    # Make the Window be in the centre of the screen.
    screen = QGuiApplication.primaryScreen().geometry()
    window_geometry = window.frameGeometry()
    center_point = screen.center()
    window_geometry.moveCenter(center_point)
    window.move(window_geometry.topLeft())

    # Connect Main Dimensions Button with searching for PDFs.
    connect_file_browse_button(
        button_name="mainDimsBtn",
        window=window,
        caption="Browse Main Dimensions PDF",
        file_type="PDF Files (*.pdf)",
        line_edit_name="mainDimsLineEdit",
    )

    # Connect Openings Button with searching for PDFs.
    connect_file_browse_button(
        button_name="openingsBtn",
        window=window,
        caption="Browse Openings PDF",
        file_type="PDF Files (*.pdf)",
        line_edit_name="openingsLineEdit",
    )

    # Connect Internal Subdivision Button with searching for XMLs.
    connect_file_browse_button(
        button_name="internalSubdivBtn",
        window=window,
        caption="Browse Internal Subdivision XML",
        file_type="XML Files (*.xml)",
        line_edit_name="internalSubdivLineEdit",
    )

    # Connect the Run button to the AI Agent pipeline.
    run_btn = window.findChild(QPushButton, "runBtn")
    if run_btn:
        run_btn.clicked.connect(lambda: handle_agent_pipeline(window))

    # Close the file and run the app.
    file.close()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
