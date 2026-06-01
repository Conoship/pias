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

    def _is_number(self, text: str) -> bool:
        """
        Method to check if a piece of text represents a decimal value.

        Args:
            text (str):
                The text to check if it is a decimal value or not.

        Returns:
            bool:
                `True` if the text represents a decimal value, `False` otherwise.
        """
        try:
            float(text)
            return True

        except ValueError:
            return False

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
            file_path (str):
                The file path from the input field.

            None:
                If widget is missing or user cancels the dialog.
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

    def get_value_from_line_edit(self, line_edit_name: str) -> float | None:
        """
        Method to retrieve a float value from a QLineEdit widget.
        If the field is empty, the user is prompted for confirmation before returning -1.

        Args:
            line_edit_name (str):
                The Qt objectName of the QLineEdit.

        Raises:
            ValueError:
                If the inputted value is not numeric.

            ValueError:
                If the inputted value is not positive,

        Returns:
            value (float):
                Parsed float value from the input field.

            None:
                If widget is missing.
        """
        value = 0.0
        line_edit = self._window.findChild(QLineEdit, line_edit_name)
        if line_edit:
            value = line_edit.text().strip()

            # Check that the input is not empty.
            if value == "":
                return None

            # Check that the input is a number.
            elif not self._is_number(value):
                raise ValueError

            # Check that the input is a positive number.
            elif float(value) <= 0:
                raise ValueError

        return float(value)
