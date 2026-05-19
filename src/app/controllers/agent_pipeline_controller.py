# Import third party packages.
import pandas as pd
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QLabel, QFrame, QVBoxLayout

# Import local packages.
from src.app.backend import run_agent_pipeline
from src.app.controllers.line_edit_controller import LineEditController
from src.app.controllers.line_edit_collector_controller import (
    LineEditCollectorController,
)
from src.app.parsers.main_dimensions_parser import MainDimensionsParser
from src.app.parsers.layouts_parser import LayoutsParser
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
        prediction: float,
        lower: float,
        upper: float,
        r_comparison_result: str,
    ) -> None:
        """
        Load the results widget UI, update its labels with prediction data,
        and display it inside the results frame of the main window.

        Args:
            prediction (float):
                The model's prediction.

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
        prediction_label = results_widget.findChild(QLabel, "prediction")
        confidence_label = results_widget.findChild(QLabel, "confidence")
        required_index_compare_label = results_widget.findChild(
            QLabel, "requiredIndexComparison"
        )

        # Modify the content of the placeholder to be the actual values.
        if prediction_label:
            prediction_label.setText(str(round(prediction, 3)))

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

        # Check if user defined values exist.
        user_defined_values = self._collector_controller.collect_user_defined_value()
        if user_defined_values is None:
            return
        (
            ship_name,
            subdivision_length,
            light_service_draft,
            subdivision_draft,
            light_gm_value,
            partial_gm_value,
            deep_gm_value,
            pass_value,
        ) = user_defined_values

        value = self._controller.get_value_from_line_edit(
            "requiredIndexLineEdit", "Required Index R"
        )
        if value is not None:
            pass_value = float(value)

        # Import the data to a csv and pass it to the agent.
        # Parse the file paths.
        main_dimensions_df = MainDimensionsParser().parse_file(main_dimensions_path)
        layouts_df = LayoutsParser().parse_file(layouts_path)
        openings_df = OpeningsParser().parse_openings(openings_path)

        # Add the UI data to the df.
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
        df["Subdivision Length"] = subdivision_length
        df["Light Service Draft"] = light_service_draft
        df["Partial Subdivision"] = (light_service_draft - subdivision_draft) * 0.6
        df["Subdivision Draft"] = subdivision_draft
        df["Light GM Value"] = light_gm_value
        df["Partial GM Value"] = partial_gm_value
        df["Deep GM Value"] = deep_gm_value

        # Combine the Data Frames.
        df_final = pd.concat([df, main_dimensions_df, layouts_df, openings_df], axis=1)

        # Run the agent pipeline and collect results.
        prediction, lower, upper, pass_result = run_agent_pipeline(
            pass_value, ship_name, df_final
        )

        # Display the output.
        self._display_results(prediction, lower, upper, pass_result)
