# Import third party packages.
import pandas as pd
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QFrame, QLabel, QMessageBox, QVBoxLayout, QWidget

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
        self._collector_controller = LineEditCollectorController(window)

    def _display_results(
        self,
        predictions: list[float],
        confidence_intervals: list[tuple],
        pass_results: list[str],
        required_index: float,
    ) -> None:
        """
        Load the results widget UI, update its labels with prediction data,
        and display it inside the results frame of the main window.

        Args:
            predictions (list[float]):
                A list of the model's predictions per loading condition.

            confidence_intervals (list[tuple]):
                A list of the 95% CI per loading condition.

            pass_results (list[str]):
                A list of whether the model passed or failed the A vs R comparison at each loading condition.

            required_index (float):
                The value of the Required Index (R).
        """
        # Load the Results Widget.
        loader = QUiLoader()
        file = QFile("src/app/ui/resultsWidget.ui")
        file.open(QFile.OpenModeFlag.ReadOnly)
        results_widget = loader.load(file)
        file.close()

        # Get the target labels.
        attained_indices_label = results_widget.findChild(QLabel, "attainedIndices")
        confidence_intervals_label = results_widget.findChild(
            QLabel, "confidenceIntervals"
        )
        pass_results_label = results_widget.findChild(QLabel, "passResults")
        overall_summary_label = results_widget.findChild(QLabel, "overallSummary")

        # Modify the content of the placeholder to be the actual values.
        if attained_indices_label:
            light_prediction = predictions[0]
            partial_prediction = predictions[1]
            deepest_prediction = predictions[2]
            attained_indices_text = f"{round(light_prediction, 3)}, {round(partial_prediction, 3)}, {round(deepest_prediction, 3)}"
            attained_indices_label.setText(attained_indices_text)

        if confidence_intervals_label:
            light_ci = confidence_intervals[0]
            partial_ci = confidence_intervals[1]
            deepest_ci = confidence_intervals[2]
            confidence_intervals_text = f"[{light_ci[0]}, {light_ci[1]}], [{partial_ci[0]}, {partial_ci[1]}], [{deepest_ci[0]}, {deepest_ci[1]}]"
            confidence_intervals_label.setText(confidence_intervals_text)

        if pass_results_label:
            light_pass_result = pass_results[0]
            partial_pass_result = pass_results[1]
            deepest_pass_result = pass_results[2]
            pass_results_text = (
                f"{light_pass_result}, {partial_pass_result}, {deepest_pass_result}"
            )
            pass_results_label.setText(pass_results_text)

        if overall_summary_label:
            # A = 0.2 * LIGHT_A + 0.4 * PARTIAL_A + 0.4 * DEEPEST_A.
            weighted_attained_index = (
                0.2 * predictions[0] + 0.4 * predictions[1] + 0.4 * predictions[1]
            )
            overall_summary_text = f"Attained Index (A): {weighted_attained_index} Required Index (R): {required_index}"
            if weighted_attained_index >= required_index:
                overall_summary_text += " PASSED"
            else:
                overall_summary_text += " FAILED"
            overall_summary_label.setText(overall_summary_text)

        # Put the widget to the Results Frame in the Main Window.
        results_frame = self._window.findChild(QFrame, "resultsFrame")
        if results_frame:
            if results_frame.layout() is None:
                layout = QVBoxLayout()
                results_frame.setLayout(layout)
            else:
                layout = results_frame.layout()

            if layout:
                # Clear previous widgets.
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
            "Deep GM Value",
        ]
        user_df = pd.DataFrame(columns=user_df_cols)

        # Collect the user defined values from the UI.
        user_defined_values = self._collector_controller.collect_user_defined_value()

        # If the user left accidentally something blank or they inputted an invalid value.
        if isinstance(user_defined_values, int):
            return

        # If the user confirmed that they prefer to use the RTF defined values.
        if user_defined_values is None:
            pass

        # No blanks where left.
        else:
            (
                subdivision_length,
                light_service_draft,
                subdivision_draft,
                light_gm_value,
                partial_gm_value,
                deep_gm_value,
            ) = user_defined_values

            # Add the UI data to the df.
            user_df["Subdivision Length"] = subdivision_length
            user_df["Light Service Draft"] = light_service_draft
            user_df["Partial Subdivision"] = (
                light_service_draft - subdivision_draft
            ) * 0.6
            user_df["Subdivision Draft"] = subdivision_draft
            user_df["Light GM Value"] = light_gm_value
            user_df["Partial GM Value"] = partial_gm_value
            user_df["Deep GM Value"] = deep_gm_value

        # Import the data to a csv and pass it to the agent.
        # Parse the file paths - if the parsing process raises an Exception show it to the user.
        try:
            main_dimensions_df = MainDimensionsParser().parse_file(main_dimensions_path)
            layouts_df = LayoutsParser().parse_file(layouts_path)

        except Exception as e:
            QMessageBox.warning(
                self._window, "There was an error parsing one of the files", str(e)
            )
            return

        # Combine the Data Frames.
        df = pd.DataFrame()
        if user_defined_values is not None:
            df = pd.concat([user_df, main_dimensions_df, layouts_df], axis=1)
        else:
            df = pd.concat([main_dimensions_df, layouts_df], axis=1)

        # Calculate the Required Index (R) using the given formulae.
        try:
            required_index = self._calculate_required_index(main_dimensions_df["loa"])

        except ValueError as error:
            QMessageBox.warning(self._window, "Invalid Ship Length", str(error))
            return

        # Run the agent pipeline and collect results.
        agent_result = run_agent_pipeline(self._window, required_index, df)
        if agent_result:
            predictions, confidence_intervals, pass_results = agent_result

            # Display the output.
            self._display_results(
                predictions, confidence_intervals, pass_results, required_index
            )
