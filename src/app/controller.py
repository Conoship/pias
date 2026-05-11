# Import standard libarary packages.
import os

# Import third party packages.
from dotenv import load_dotenv
import psycopg
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QMessageBox,
    QWidget,
    QFileDialog,
    QLineEdit,
    QPushButton,
    QLabel,
    QFrame,
    QVBoxLayout,
)

# Import local packages.
from src.models.random_forest_baseline import RandomForestBaseline
from src.app.backend import run_agent_pipeline
from src.db.db import get_local_conn
from src.parsing.dimensions.parse_main_dimensions import import_main_dimensions
from src.parsing.layout.parse_layout import import_layout_xml
from src.parsing.openings.parse_openings import import_openings

load_dotenv()


def get_conn():
    return psycopg.connect(
        dbname=os.environ["PG_DBNAME"],
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
        host=os.environ["PG_HOST"],
        port=int(os.environ["PG_PORT"]),
    )


# Controller either forwards the data to the ui (app.py) or sends data to backend for processing.


def open_file(window: QWidget, caption: str, file_type: str, line_edit_name: str):
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
    button_name: str, window: QWidget, caption: str, file_type: str, line_edit_name: str
):
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
            lambda: open_file(window, caption, file_type, line_edit_name)
        )


def get_file_from_line_edit(
    window: QWidget, line_edit_name: str, file_name: str
) -> str | None:
    """
    Function to retrieve a file path from a QLineEdit widget.

    Args:
        window (QWidget):
            Parent widget containing the QLineEdit.

        object_name (str):
            The Qt objectName of the QLineEdit.

        file_name (str):
            The name of the file to be inputted, used to display the error message.

    Returns:
        file_path (float): The file path from the input field.
        int: -1 if user confirms leaving the field blank.
        None: If widget is missing or user cancels the dialog.
    """
    file_path = ""
    line_edit = window.findChild(QLineEdit, line_edit_name)
    if line_edit:
        file_path = line_edit.text().strip()
        if file_path == "":
            QMessageBox.warning(
                window,
                "Warning Empty File",
                f"Please input {file_name}.",
                QMessageBox.StandardButton.Ok,
            )
            return None

    return file_path


def get_ship_name_from_line_edit(window: QWidget, line_edit_name: str) -> str | None:
    """
    Function to retrieve the ship name from a QLineEdit widget.

    Args:
        window (QWidget):
            Parent widget containing the QLineEdit.

        object_name (str):
            The Qt objectName of the QLineEdit.

    Returns:
        ship_name (str): The ship's name from the input field.
        None: If widget is missing or user cancels the dialog.
    """
    ship_name = ""
    line_edit = window.findChild(QLineEdit, line_edit_name)
    if line_edit:
        ship_name = line_edit.text().strip()
        if ship_name == "":
            QMessageBox.warning(
                window,
                "Warning Empty value for Ship Name",
                "Please input the Ship Name.",
                QMessageBox.StandardButton.Ok,
            )
            return None

    return ship_name


def get_value_from_line_edit(
    window: QWidget, line_edit_name: str, feature_name: str
) -> float | None:
    """
    Function to retrieve a float value from a QLineEdit widget.
    If the field is empty, the user is prompted for confirmation before returning -1.

    Args:
        window (QWidget):
            Parent widget containing the QLineEdit.

        object_name (str):
            The Qt objectName of the QLineEdit.

        feature_name (str):
            The name of the feature, used to display the error message.

    Returns:
        value (float): Parsed float value from the input field.
        int: -1 if user confirms leaving the field blank.
        None: If widget is missing or user cancels the dialog.
    """
    value = 0.0
    line_edit = window.findChild(QLineEdit, line_edit_name)
    if line_edit:
        value = line_edit.text().strip()
        if value == "":
            reply = QMessageBox.question(
                window,
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


def display_results(
    window: QWidget,
    prediction: float,
    lower: float,
    upper: float,
    R_compare_result: str,
):
    """
    Load the results widget UI, update its labels with prediction data,
    and display it inside the results frame of the main window.

    Args:
        window (QWidget):
            The main application window that contains the target results frame.

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
        required_index_compare_label.setText(str(R_compare_result))

    # Put the widget to the Results Frame in the Main Window.
    results_frame = window.findChild(QFrame, "resultsFrame")
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


def collect_file_paths(window: QWidget):
    """
    Collect the file paths for main dimensions, openings, and
    internal subdivision.
    Return 1 if they do not exist and the file paths otherwise.

    Args:
        window (QWidget):
            The main application window used to locate UI elements
            where results will be displayed.
    """

    # Collect the file paths from the UI
    main_dims_path = get_file_from_line_edit(
        window, "mainDimsLineEdit", "Main Dimensions PDF"
    )
    if main_dims_path is None:
        return 1

    openings_path = get_file_from_line_edit(window, "openingsLineEdit", "Openings PDF")
    if openings_path is None:
        return 1

    internal_subdiv_path = get_file_from_line_edit(
        window, "internalSubdivLineEdit", "Internal Subdivision XML"
    )
    if internal_subdiv_path is None:
        return 1

    return (main_dims_path, openings_path, internal_subdiv_path)


def collect_user_defined_value(window: QWidget):
    """
    Collect the user defined values: ship name, subdivision length,
    light service draft, subdivision draft, light gm value, partial gm value,
    deep gm value.
    Return 1 if they do not exist and file values otherwise.

    Args:
        window (QWidget):
            The main application window used to locate UI elements
            where results will be displayed.
    """
    # If any value is None return immediately.
    ship_name = get_ship_name_from_line_edit(window, "shipNameLineEdit")
    if ship_name is None:
        return 1

    subdivision_length = get_value_from_line_edit(
        window, "subdivLenLineEdit", "Subdivision Length"
    )
    if subdivision_length is None:
        return 1

    light_service_draft = get_value_from_line_edit(
        window, "lightServiceDraftLineEdit", "Light Service Draft"
    )
    if light_service_draft is None:
        return 1

    subdivision_draft = get_value_from_line_edit(
        window, "subdivDraftLineEdit", "Subdivision Draft"
    )
    if subdivision_draft is None:
        return 1

    light_gm_value = get_value_from_line_edit(window, "lightGMLineEdit", "Light GM")
    if light_gm_value is None:
        return 1

    partial_gm_value = get_value_from_line_edit(
        window, "partialGMLineEdit", "Partial GM"
    )
    if partial_gm_value is None:
        return 1

    deep_gm_value = get_value_from_line_edit(window, "deepGMLineEdit", "Deep GM")
    if deep_gm_value is None:
        return 1

    pass_value = get_value_from_line_edit(
        window, "requiredIndexLineEdit", "Required Index R"
    )
    if pass_value is None:
        return 1

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


def handle_agent_pipeline(window: QWidget):
    """
    Execute the AI agent pipeline: load data, run the trained model,
    and display prediction results in the UI.

    Args:
        window (QWidget):
            The main application window used to locate UI elements
            where results will be displayed.
    """
    # Check if file paths exist.
    if collect_file_paths(window):
        return
    main_dimensions_path, openings_path, internal_subdiv_path = collect_file_paths(
        window
    )

    # Check if user defined values exist.
    if collect_user_defined_value(window):
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
    ) = collect_user_defined_value(window)

    value = get_value_from_line_edit(
        window, "requiredIndexLineEdit", "Required Index R"
    )
    pass_value = float(value)

    # Import the data to database from user-selected files:
    conn = get_local_conn()
    cur = conn.cursor()
    import_main_dimensions(main_dimensions_path)
    import_openings(openings_path)
    import_layout_xml(internal_subdiv_path)

    # Add user-inputted values to the db:
    cur.execute(
        """INSERT INTO probdam_conclusion (subdivision_length) 
                   VALUE (%f);""",
        (subdivision_length),
    )
    cur.execute(
        """INSERT INTO trim_gm  (condition_name, draft, gm) 
                   VALUE (%s, %f, %f);""",
        ("light", light_service_draft, light_gm_value),
    )
    cur.execute(
        """INSERT INTO trim_gm  (condition_name, gm) 
                   VALUE (%s, %f);""",
        ("partial", partial_gm_value),
    )
    cur.execute(
        """INSERT INTO trim_gm  (condition_name, gm) 
                   VALUE (%s, %f);""",
        ("deepest", deep_gm_value),
    )

    conn.commit()
    cur.close()
    conn.close()

    # Run the agent pipeline and collect results.
    prediction, lower, upper, pass_result = run_agent_pipeline(pass_value, ship_name)

    # Display the output.
    display_results(window, prediction, lower, upper, pass_result)
