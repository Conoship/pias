# Import standard library packages.
from typing import cast

# Import third party packages.
import pandas as pd
from PySide6.QtCore import QFile, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QFrame,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Import local packages.
from src.app.backend import run_agent_pipeline
from src.app.controllers.line_edit_collector_controller import (
    LineEditCollectorController,
)
from src.app.controllers.line_edit_controller import LineEditController
from src.app.parsers.layouts_parser import LayoutsParser
from src.app.parsers.main_dimensions_parser import MainDimensionsParser


class AgentPipelineController(object):
    def __init__(self, window: QWidget) -> None:
        """
        Controller class to run the Agent Pipeline and perform all the necessary actions related to it.

        Args:
            window (QWidget):
                The main application window that contains the target results frame.
        """
        self._window = window
        self._controller = LineEditController(window)
        self._collector_controller = LineEditCollectorController(
            window, self._controller
        )

    def _display_results(
        self,
        predictions: list[float],
        confidence_intervals: list[tuple],
        pass_results: list[str],
        required_index: float,
        partial_subdivision: float,
    ) -> None:
        """
        Method to display the results in the table.

        Args:
            predictions (list[float]):
                A list of all the model's predictions for the Attained Index (A) per loading condition.

            confidence_intervals (list[tuple]):
                A list of all the model's 95% CIs for the Attained Index (A) per loading condition.

            pass_results (list[str]):
                A list of all the pass results for the Attained Index (A) and Required Index (R) per loading condition comparisons.
                If A_LC >= 0.5 * R, where A_LC is the attained index at any Loading Condition then the value is Pass, else Fail.

            required_index (float):
                The value of the Required Index (R).
        """
        # Show the Partial Subdivision calculated value.
        partial_subdivision_line_edit = self._window.findChild(
            QLineEdit, "partialSubdivisionLineEdit"
        )
        if partial_subdivision_line_edit:
            partial_subdivision_line_edit.setText(str(round(partial_subdivision, 3)))

        # Load the Results Widget.
        loader = QUiLoader()
        file = QFile("src/app/ui/resultsWidget.ui")
        file.open(QFile.OpenModeFlag.ReadOnly)
        results_widget = loader.load(file)
        file.close()

        # Get the results table.
        results_table = results_widget.findChild(QTableWidget, "resultsTable")

        if results_table:
            # Row names.
            row_names = ["Light", "Partial", "Deepest", "Overall Pass/Fail"]
            for row, name in enumerate(row_names):
                item = QTableWidgetItem(name)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                results_table.setItem(row, 0, item)

            # Attained indices.
            for row, prediction in enumerate(predictions):
                item = QTableWidgetItem(str(round(prediction, 3)))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                results_table.setItem(row, 1, item)

            # Confidence intervals.
            for row, ci in enumerate(confidence_intervals):
                ci_text = f"[{round(ci[0], 3)}, {round(ci[1], 3)}]"
                item = QTableWidgetItem(ci_text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                results_table.setItem(row, 2, item)

            # Pass/Fail results.
            for row, pass_result in enumerate(pass_results):
                item = QTableWidgetItem(pass_result)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                results_table.setItem(row, 3, item)

            # Overall Pass/Fail row (row 3) — spans cols 1-3.
            # A = 20% * A_LIGHT + 40% * A_PARTIAL + 40% * A_DEEPEST
            weighted_attained_index = (
                0.2 * predictions[0] + 0.4 * predictions[1] + 0.4 * predictions[2]
            )
            overall_text = (
                f"A: {round(weighted_attained_index, 3)}  |  "
                f"R: {round(required_index, 3)}  |  "
                f"{'PASSED' if weighted_attained_index >= required_index else 'FAILED'}"
            )
            results_table.setSpan(3, 1, 1, 3)
            item = QTableWidgetItem(overall_text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            results_table.setItem(3, 1, item)

        # Put the widget in the Results Frame.
        results_frame = self._window.findChild(QFrame, "resultsFrame")
        if results_frame:
            if results_frame.layout() is None:
                layout = QVBoxLayout()
                results_frame.setLayout(layout)
            else:
                layout = results_frame.layout()

            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    if item:
                        widget = item.widget()
                        if widget:
                            widget.deleteLater()
                layout.addWidget(results_widget)

    def _calculate_required_index(self, ship_length: float) -> float:
        """
        Method to calculate the Required Index (R), according to the SOLAS requirements.

        Args:
            ship_length (float):
                The length of the ship.

        Raises:
            ValueError:
                If `ship_length` is less than 80.

        Returns:
            required_index (float):
                The Required Index (R).
        """
        required_index = 0.0
        if ship_length < 80:
            raise ValueError(
                "SOLAS Subdivision requirements apply to ships that are >= 80 m"
            )

        if ship_length > 100:
            required_index = 1 - (128 / (ship_length + 152))
        else:
            r_0 = 1 - (128 / (ship_length + 152))
            required_index = 1 - (1 / ((ship_length / 100) * (r_0 / (1 - r_0))))

        return required_index

    def _get_layouts_ship_name(self, layouts_df: pd.DataFrame) -> str:
        """
        Gets the single ship name from the layouts DataFrame.

        Args:
            layouts_df (pd.DataFrame):
                The parsed layouts DataFrame.

        Raises:
            ValueError:
                If no ship name or multiple ship names are present.

        Returns:
            str:
                The ship name from the layouts DataFrame.
        """
        ship_names = layouts_df["ship"].dropna().astype(str).str.strip().unique()
        ship_names = [ship_name for ship_name in ship_names if ship_name]

        if len(ship_names) == 0:
            raise ValueError("The Layouts file does not contain a ship name.")

        if len(ship_names) > 1:
            raise ValueError(
                "The Layouts file contains multiple ship names: "
                f"{', '.join(ship_names)}."
            )

        return ship_names[0]

    def handle_agent_pipeline(self) -> None:
        """
        Execute the AI agent pipeline: load data, run the trained model,
        and display prediction results in the UI.
        """
        # Check if file paths exist.
        file_paths = self._collector_controller.collect_file_paths()
        if file_paths is None:
            return

        main_dimensions_path, layouts_path = file_paths

        # Columns and data frame for the user defined UI values.
        user_df_cols = [
            "Subdivision Length",
            "Light Service Draft",
            "Partial Subdivision",
            "Subdivision Draft",
            "Light GM Value",
            "Partial GM Value",
            "Deepest GM Value",
            "Light Displacement",
            "Partial Displacement",
            "Deepest Displacement",
            "Light Trim",
            "Partial Trim",
            "Deepest Trim",
        ]

        # Collect the user defined values from the UI.
        user_defined_values = self._collector_controller.collect_user_defined_value()

        # If the user left accidentally something blank or they inputted an invalid value.
        if isinstance(user_defined_values, int):
            return

        (
            light_service_draft,
            subdivision_draft,
            light_gm_value,
            partial_gm_value,
            deepest_gm_value,
            subdivision_length,
            light_displacement,
            partial_displacement,
            deepest_displacement,
        ) = user_defined_values

        # Add the UI data to the df.
        user_df = pd.DataFrame(
            [
                {
                    "Subdivision Length": subdivision_length,
                    "Light Service Draft": light_service_draft,
                    "Partial Subdivision": (
                        (subdivision_draft - light_service_draft) * 0.6
                    )
                    + light_service_draft,
                    "Subdivision Draft": subdivision_draft,
                    "Light GM Value": light_gm_value,
                    "Partial GM Value": partial_gm_value,
                    "Deepest GM Value": deepest_gm_value,
                    "Light Displacement": light_displacement,
                    "Partial Displacement": partial_displacement,
                    "Deepest Displacement": deepest_displacement,
                    "Light Trim": 0,
                    "Partial Trim": 0,
                    "Deepest Trim": 0,
                }
            ],
            columns=user_df_cols,
        )

        # Import the data to a csv and pass it to the agent.
        # Parse the file paths - if the parsing process raises an Exception show it to the user.
        try:
            main_dimensions_df = MainDimensionsParser().parse_file(main_dimensions_path)
            layouts_df = LayoutsParser().parse_file(layouts_path)
            main_dimensions_ship = str(main_dimensions_df.at[0, "name"]).strip()
            layouts_ship = self._get_layouts_ship_name(layouts_df)
            if main_dimensions_ship.lower() != layouts_ship.lower():
                raise Exception(
                    f"The selected files appear to be for different ships. Main Dimensions RTF ship: {main_dimensions_ship}. Layouts XML ship: {layouts_ship}."
                )

        except Exception as e:
            QMessageBox.warning(self._window, "Input file problem", str(e))
            return

        # Use the user defined subdivision length as the ship length when provided.
        if subdivision_length is not None:
            main_dimensions_df["loa"] = subdivision_length

        # Combine the Data Frames.
        df = pd.concat([user_df, main_dimensions_df, layouts_df], axis=1)

        # Calculate the Required Index (R) using the given formulae.
        try:
            ship_length = cast(float, main_dimensions_df.at[0, "loa"])
            required_index = self._calculate_required_index(ship_length)

        except ValueError as error:
            QMessageBox.warning(self._window, "Invalid Ship Length", str(error))
            return

        # Run the agent pipeline and collect results.
        agent_result = run_agent_pipeline(self._window, required_index, df)
        if agent_result:
            predictions, confidence_intervals, pass_results = agent_result
            partial_subdivision = cast(float, user_df.at[0, "Partial Subdivision"])

            # Display the output.
            self._display_results(
                predictions,
                confidence_intervals,
                pass_results,
                required_index,
                partial_subdivision,
            )
