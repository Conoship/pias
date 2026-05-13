# Import third party packages.
from PySide6.QtWidgets import QWidget, QFileDialog, QLineEdit, QPushButton


class ButtonController(object):
    def __init__(self) -> None:
        """
        Controller class to connect the buttons to their corresponding actions.
        This class handles only the file browse buttons as the run button of the application
        is handled individually in the `App` class.
        """
        pass

    def _open_file(
        self,
        window: QWidget,
        caption: str,
        file_type: str,
        line_edit_name: str,
    ) -> None:
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
            line_edit = window.findChild(QLineEdit, line_edit_name)
            if line_edit:
                line_edit.setText(file_path)

    def connect_file_browse_button(
        self,
        button_name: str,
        window: QWidget,
        caption: str,
        file_type: str,
        line_edit_name: str,
    ) -> None:
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
        btn = window.findChild(QPushButton, button_name)
        if btn:
            btn.clicked.connect(
                lambda: self._open_file(window, caption, file_type, line_edit_name)
            )
