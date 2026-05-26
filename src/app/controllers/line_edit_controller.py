# Import third party packages.
from PySide6.QtWidgets import QLineEdit, QMessageBox, QWidget


class LineEditController(object):
    def __init__(self, window: QWidget) -> None:
        """
        Controller class that performs retrieval actions related to the specified Line Edits.

        Args:
            window (QWidget):
                Parent widget containing the QLineEdit.
        """
        self._window = window

    def get_file_from_line_edit(
        self, line_edit_name: str, file_name: str
    ) -> str | None:
        """
        Method to retrieve a file path from a QLineEdit widget.

        Args:
            line_edit_name (str):
                The Qt objectName of the QLineEdit.

            file_name (str):
                The name of the file to be inputted, used to display the error message.

        Returns:
            file_path (float): The file path from the input field.
            int: -1 if user confirms leaving the field blank.
            None: If widget is missing or user cancels the dialog.
        """
        file_path = ""
        line_edit = self._window.findChild(QLineEdit, line_edit_name)
        if line_edit:
            file_path = line_edit.text().strip()
            if file_path == "":
                QMessageBox.warning(
                    self._window,
                    "Warning Empty File",
                    f"Please input {file_name}.",
                    QMessageBox.StandardButton.Ok,
                )
                return None

        return file_path

    def get_ship_name_from_line_edit(self, line_edit_name: str) -> str | None:
        """
        Method to retrieve the ship name from a QLineEdit widget.

        Args:
            line_edit_name (str):
                The Qt objectName of the QLineEdit.

        Returns:
            ship_name (str): The ship's name from the input field.
            None: If widget is missing or user cancels the dialog.
        """
        ship_name = ""
        line_edit = self._window.findChild(QLineEdit, line_edit_name)
        if line_edit:
            ship_name = line_edit.text().strip()
            if ship_name == "":
                QMessageBox.warning(
                    self._window,
                    "Warning Empty value for Ship Name",
                    "Please input the Ship Name.",
                    QMessageBox.StandardButton.Ok,
                )
                return None

        return ship_name

    def get_value_from_line_edit(
        self, line_edit_name: str, feature_name: str
    ) -> float | None:
        """
        Method to retrieve a float value from a QLineEdit widget.
        If the field is empty, the user is prompted for confirmation before returning -1.

        Args:
            line_edit_name (str):
                The Qt objectName of the QLineEdit.

            feature_name (str):
                The name of the feature, used to display the error message.

        Returns:
            value (float): Parsed float value from the input field.
            int: -1 if user confirms leaving the field blank.
            None: If widget is missing or user cancels the dialog.
        """
        value = 0.0
        line_edit = self._window.findChild(QLineEdit, line_edit_name)
        if line_edit:
            value = line_edit.text().strip()
            if value == "":
                reply = QMessageBox.question(
                    self._window,
                    "Confirm Empty Value",
                    f"Are you sure you want to leave the value of {feature_name} blank and use RTF File values?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    return -1
                else:
                    return None

        return float(value)
