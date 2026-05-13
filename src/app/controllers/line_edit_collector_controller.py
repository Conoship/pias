# Import third party packages.
from PySide6.QtWidgets import QWidget

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
    ) -> tuple[str, float, float, float, float, float, float, float] | None:
        """
        Collect the user defined values: ship name, subdivision length,
        light service draft, subdivision draft, light gm value, partial gm value,
        deep gm value.

        Returns:
            tuple[float] | None:
                A tuple containing the collected values, unless a value is None then returns None.
        """
        # If any value is None return immediately.
        ship_name = self._line_edit_controller.get_ship_name_from_line_edit(
            "shipNameLineEdit"
        )
        if ship_name is None:
            return None

        subdivision_length = self._line_edit_controller.get_value_from_line_edit(
            "subdivLenLineEdit", "Subdivision Length"
        )
        if subdivision_length is None:
            return None

        light_service_draft = self._line_edit_controller.get_value_from_line_edit(
            "lightServiceDraftLineEdit", "Light Service Draft"
        )
        if light_service_draft is None:
            return None

        subdivision_draft = self._line_edit_controller.get_value_from_line_edit(
            "subdivDraftLineEdit", "Subdivision Draft"
        )
        if subdivision_draft is None:
            return None

        light_gm_value = self._line_edit_controller.get_value_from_line_edit(
            "lightGMLineEdit", "Light GM"
        )
        if light_gm_value is None:
            return None

        partial_gm_value = self._line_edit_controller.get_value_from_line_edit(
            "partialGMLineEdit", "Partial GM"
        )
        if partial_gm_value is None:
            return None

        deep_gm_value = self._line_edit_controller.get_value_from_line_edit(
            "deepGMLineEdit", "Deep GM"
        )
        if deep_gm_value is None:
            return None

        pass_value = self._line_edit_controller.get_value_from_line_edit(
            "requiredIndexLineEdit", "Required Index R"
        )
        if pass_value is None:
            return None

        return (
            ship_name,
            subdivision_length,
            light_service_draft,
            subdivision_draft,
            light_gm_value,
            partial_gm_value,
            deep_gm_value,
            pass_value,
        )
