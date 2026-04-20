# Import standard library packages.
import sys

# Import third party packages.
from PySide6.QtGui import QIcon
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QWidget, QFileDialog, QLineEdit, QPushButton


def open_file(window: QWidget, caption: str, file_type: str, line_edit_name: str):
    """
    Open a file selection dialog and populate a QLineEdit with the selected file path.

    Args:
        window (QWidget):
            The parent widget that owns the file dialog and contains the target QLineEdit.

        caption (str):
            The title displayed on the file dialog window.

        file_type (str):
            File filter string (e.g., "CSV Files (*.csv);;All Files (*)") used to limit
            selectable file types.

        line_edit_name (str):
            The objectName of the QLineEdit widget to update with the selected file path.
    """
    file_path, _ = QFileDialog.getOpenFileName(window, caption, "", file_type)
    if file_path:
        line_edit: QLineEdit | None = window.findChild(QLineEdit, line_edit_name)
        if line_edit:
            line_edit.setText(file_path)


def connect_file_browse_button(
    button_name: str, window: QWidget, caption: str, file_type: str, line_edit_name: str
):
    """
    Connects a QPushButton in a Qt window to a file selection handler.

    Args:
        button_name (str):
            The objectName of the QPushButton to find in the window.

        window (QWidget):
            The parent Qt widget containing the button and line edit.

        caption (str):
            The title shown in the file selection dialog.

        file_type (str):
            The file filter string used in the dialog (e.g. "Images (*.png *.jpg)").

        line_edit_name (str):
            The objectName of the QLineEdit that will display the selected file path.
    """
    btn: QPushButton | None = window.findChild(QPushButton, button_name)
    if btn is not None:
        btn.clicked.connect(
            lambda: open_file(window, caption, file_type, line_edit_name)
        )


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
        caption="Browse Main Dimensions PDF",
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

    # Connect Damage Stability Button with searching for PDFs/RTFs.
    connect_file_browse_button(
        button_name="damageStabBtn",
        window=window,
        caption="Browse Damage Stability PDF/RTF",
        file_type="PDF Files (*.pdf);;RTF Files (*.rtf)",
        line_edit_name="damageStabLineEdit",
    )

    # Close the file and run the app.
    file.close()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
