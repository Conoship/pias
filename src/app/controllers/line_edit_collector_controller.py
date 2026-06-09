# Import third party packages.
from PySide6.QtWidgets import QMessageBox, QWidget

# Import local packages.
from src.app.controllers.line_edit_controller import LineEditController


class LineEditCollectorController(object):
    def __init__(
        self, window: QWidget, line_edit_controller: LineEditController
    ) -> None:
        """
        Controller class that uses a `LineEditController` to collect the values and files from the specified fields

        Args:
            window (QWidget):
                The main application window, used to provide all validation warnings.

            line_edit_controller (LineEditController):
                The LineEditController instance to use for accessing the Line Edits.
        """
        # Attribute Construction.
        self._window = window
        self._line_edit_controller = line_edit_controller

    def collect_file_paths(self) -> tuple[str, str] | None:
        """
        Collect the file paths for main dimensions and layouts.

        Returns:
            tuple[str, str] | None:
                A tuple containing the collected values, unless a value is None then returns None.
        """
        # Collect the file paths from the UI
        main_dims_path = self._line_edit_controller.get_file_from_line_edit(
            "mainDimsLineEdit", "Main Dimensions RTF"
        )
        if main_dims_path is None:
            return None

        layouts_path = self._line_edit_controller.get_file_from_line_edit(
            "layoutsLineEdit", "Layouts XML"
        )
        if layouts_path is None:
            return None

        return main_dims_path, layouts_path

    def _collect_required_user_defined_values(
        self,
    ) -> tuple[float, float, float, float, float] | int:
        """
        Collect the required user defined values from the UI.

        Returns:
            tuple[float, float, float, float, float]:
                A tuple containing the collected values.

            int (-1):
                If one or more required values are empty.
        """
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
        deepest_gm_value = self._line_edit_controller.get_value_from_line_edit(
            "deepestGMLineEdit"
        )

        empty_required_value = (
            light_service_draft is None
            or subdivision_draft is None
            or light_gm_value is None
            or partial_gm_value is None
            or deepest_gm_value is None
        )

        if empty_required_value:
            QMessageBox.warning(
                self._window,
                "Missing required value",
                "Please input all required user defined values.",
            )
            return -1

        assert light_service_draft is not None
        assert subdivision_draft is not None
        assert light_gm_value is not None
        assert partial_gm_value is not None
        assert deepest_gm_value is not None

        return (
            light_service_draft,
            subdivision_draft,
            light_gm_value,
            partial_gm_value,
            deepest_gm_value,
        )

    def _collect_optional_user_defined_values(
        self,
    ) -> tuple[float | None, float | None, float | None, float | None] | int:
        """
        Collect the optional user defined values from the UI.

        Returns:
            tuple[float | None, float | None, float | None, float | None]:
                A tuple containing the collected optional values. Empty fields are returned as None.

            int (-1):
                If the user does not confirm leaving one or more optional values empty.
        """
        subdivision_length = self._line_edit_controller.get_value_from_line_edit(
            "subdivLenLineEdit"
        )
        light_displacement = self._line_edit_controller.get_value_from_line_edit(
            "lightDisplacementLineEdit"
        )
        partial_displacement = self._line_edit_controller.get_value_from_line_edit(
            "partialDisplacementLineEdit"
        )
        deepest_displacement = self._line_edit_controller.get_value_from_line_edit(
            "deepestDisplacementLineEdit"
        )

        empty_optional_value = (
            light_displacement is None
            or partial_displacement is None
            or deepest_displacement is None
        )

        if empty_optional_value:
            reply = QMessageBox.warning(
                self._window,
                "Confirm Empty Displacement Values",
                "Are you sure you want to leave the displacement values empty? This will negatively affect the accuracy of the prediction.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return -1

        return (
            subdivision_length,
            light_displacement,
            partial_displacement,
            deepest_displacement,
        )

    def collect_user_defined_value(
        self,
    ) -> (
        tuple[
            float,
            float,
            float,
            float,
            float,
            float | None,
            float | None,
            float | None,
            float | None,
        ]
        | int
    ):
        """
        Collect the user defined values:
        - Light Service Draft
        - Subdivision Draft
        - Light GM
        - Partial GM
        - Deep GM
        - Subdivision Length
        - Light Displacement
        - Partial Displacement
        - Deepest Displacement

        Returns:
            tuple[float, float, float, float, float, float | None, float | None, float | None, float | None]:
                A tuple containing the collected values.

            int (-1):
                If one or more required values are empty or there was an invalid value inputted.
        """
        # Try to retrieve the values, unless the LineEditController raised a ValueError.
        try:
            required_values = self._collect_required_user_defined_values()
            if isinstance(required_values, int):
                return required_values

            optional_values = self._collect_optional_user_defined_values()
            if isinstance(optional_values, int):
                return optional_values

            return required_values + optional_values

        except ValueError:
            QMessageBox.information(
                self._window,
                "Invalid value",
                "All values must be positive decimal values.\nUse a dot for decimals instead of a comma.\nMake sure you did not enter any letters or negative numbers.",
            )
            return -1
