# Import third party packages.
import pandas as pd
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

# Import local packages.
from src.app.backend import run_agent_pipeline
from src.app.controllers.line_edit_collector_controller import (
    LineEditCollectorController,
)
from src.app.controllers.line_edit_controller import LineEditController
from src.app.parsers.layouts_parser import LayoutsParser
from src.app.parsers.main_dimensions_parser import MainDimensionsParser
from src.app.parsers.openings_parser import OpeningsParser


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
        lower: float,
        upper: float,
        r_comparison_result: str,
    ) -> None:
        """
        Load the results widget UI, update its labels with prediction data,
        and display it inside the results frame of the main window.

        Args:
            prediction (list[float]):
                The model's predictions, being a list containing the prediction for all three loading conditions.

            lower (float):
                The lower end of the 95% CI of the model's prediction.

            upper (float):
                The upper end of the 95% CI of the model's prediction.
        """
        # Load the Results Widget.
        loader = QUiLoader()
        file = QFile("src/app/ui/resultsWidget.ui")
        file.open(QFile.OpenModeFlag.ReadOnly)
        results_widget = loader.load(file)
        file.close()

        # Get the target labels.
        light_prediction_label = results_widget.findChild(
            QLabel, "lightPredictionLabel"
        )
        partial_prediction_label = results_widget.findChild(
            QLabel, "partialPredictionLabel"
        )
        deepest_prediction_label = results_widget.findChild(
            QLabel, "deepestPredictionLabel"
        )
        confidence_label = results_widget.findChild(QLabel, "confidence")
        required_index_compare_label = results_widget.findChild(
            QLabel, "requiredIndexComparison"
        )

        # Modify the content of the placeholder to be the actual values.
        if light_prediction_label:
            light_prediction_label.setText(str(round(predictions[0], 3)))

        if partial_prediction_label:
            partial_prediction_label.setText(str(round(predictions[1], 3)))

        if deepest_prediction_label:
            deepest_prediction_label.setText(str(round(predictions[2], 3)))

        if confidence_label:
            confidence_label.setText(f"[{lower:.3f}, {upper:.3f}]")

        if required_index_compare_label:
            required_index_compare_label.setText(str(r_comparison_result))

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

    def handle_agent_pipeline(self) -> None:
        """
        Execute the AI agent pipeline: load data, run the trained model,
        and display prediction results in the UI.
        """
        # Check if file paths exist.
        file_paths = self._collector_controller.collect_file_paths()
        if file_paths is None:
            return

        main_dimensions_path, openings_path, layouts_path = file_paths

        # Columns and data frame for the user defined UI values.
        df_cols = [
            "Subdivision Length",
            "Light Service Draft",
            "Partial Subdivision",
            "Subdivision Draft",
            "Light GM Value",
            "Partial GM Value",
            "Deep GM Value",
        ]
        df = pd.DataFrame(columns=df_cols)

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
            df["Subdivision Length"] = subdivision_length
            df["Light Service Draft"] = light_service_draft
            df["Partial Subdivision"] = (light_service_draft - subdivision_draft) * 0.6
            df["Subdivision Draft"] = subdivision_draft
            df["Light GM Value"] = light_gm_value
            df["Partial GM Value"] = partial_gm_value
            df["Deep GM Value"] = deep_gm_value

        # Import the data to a csv and pass it to the agent.
        # Parse the file paths.
        main_dimensions_df = MainDimensionsParser().parse_file(main_dimensions_path)
        layouts_df = LayoutsParser().parse_file(layouts_path)
        openings_df = OpeningsParser().parse_file(openings_path)

        # Combine the Data Frames.
        df_final = pd.DataFrame()
        if user_defined_values is not None:
            df_final = pd.concat(
                [df, main_dimensions_df, layouts_df, openings_df], axis=1
            )
        else:
            df_final = pd.concat([main_dimensions_df, layouts_df, openings_df], axis=1)

        # Calculate the pass value using the given formulae.
        pass_value = 0

        # Run the agent pipeline and collect results.
        agent_result = run_agent_pipeline(pass_value, df_final)
        if agent_result:
            # Display the output.
            self._display_results(**agent_result)
