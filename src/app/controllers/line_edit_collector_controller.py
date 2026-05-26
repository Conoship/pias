# Import third party packages.
from PySide6.QtWidgets import QMessageBox, QWidget

# Import local packages.
from src.app.controllers.line_edit_controller import LineEditController


class LineEditCollectorController(object):
    def __init__(self, window: QWidget) -> None:
        """
        Controller class that uses a `LineEditController` to collect the values and files from the specified fields

        Args:
            window (QWidget):
                The window to pass to the `LineEditController` as its constructor argument.
        """
        # Attribute Construction.
        self._window = window
        self._line_edit_controller = LineEditController(window)

    def collect_file_paths(self) -> tuple[str, str, str] | None:
        """
         Collect the file paths for main dimensions, openings, and
        layouts.

         Returns:
             tuple[str, str, str] | None:
                 A tuple containing the collected values, unless a value is None then returns None.
        """
        # Collect the file paths from the UI
        main_dims_path = self._line_edit_controller.get_file_from_line_edit(
            "mainDimsLineEdit", "Main Dimensions PDF"
        )
        if main_dims_path is None:
            return None

        openings_path = self._line_edit_controller.get_file_from_line_edit(
            "openingsLineEdit", "Openings PDF"
        )
        if openings_path is None:
            return None

        layouts_path = self._line_edit_controller.get_file_from_line_edit(
            "layoutsLineEdit", "Layouts XML"
        )
        if layouts_path is None:
            return None

        return (main_dims_path, openings_path, layouts_path)

    def collect_user_defined_value(
        self,
    ) -> tuple[float, float, float, float, float, float] | int | None:
        """
        Collect the user defined values: subdivision length,
        light service draft, subdivision draft, light gm value, partial gm value,
        deep gm value.

        Returns:
            tuple[float, float, float, float, float, float]:
                A tuple containing the collected values

            int (-1):
                If the user said that the do not wish to leave one or more features empty or there was an invalid value inputted.

            None:
                If the user said that they wish to leave one or more features empty.
        """
        # If any value is None return immediately.
        try:
            subdivision_length = self._line_edit_controller.get_value_from_line_edit(
                "subdivLenLineEdit"
            )
            light_service_draft = self._line_edit_controller.get_value_from_line_edit(
                "lightServiceDraftLineEdit"
            )
            subdivision_draft = self._line_edit_controller.get_value_from_line_edit(
                "subdivDraftLineEdit"
            )
            light_gm_value = self._line_edit_controller.get_value_from_line_edit(
                "lightGMLineEdit"
            )
            partial_gm_value = self._line_edit_controller.get_value_from_line_edit(
                "partialGMLineEdit"
            )
            deep_gm_value = self._line_edit_controller.get_value_from_line_edit(
                "deepGMLineEdit"
            )
            empty_feature = (
                not subdivision_length
                or not light_service_draft
                or not subdivision_draft
                or not light_gm_value
                or not partial_gm_value
                or not deep_gm_value
            )
            if empty_feature:
                reply = QMessageBox.question(
                    self._window,
                    "Confirm Empty Value",
                    "Are you sure you want to leave the value of a feature blank and use the RTF file values instead?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    return None

                else:
                    return -1

        except ValueError:
            QMessageBox.information(
                self._window,
                "Invalid value inputted",
                "All values must be positive floating point numbers.\nMake sure you did not input any letters or negative numbers.",
            )
            return -1

        return (
            subdivision_length,
            light_service_draft,
            subdivision_draft,
            light_gm_value,
            partial_gm_value,
            deep_gm_value,
        )
