# Import standard library packages.
import sys
import pickle

# Import third party packages.
import pandas as pd
from PySide6.QtGui import QIcon
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QFileDialog,
    QLineEdit,
    QPushButton,
    QLabel,
    QFrame,
    QVBoxLayout,
)


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


def display_results(window: QWidget, prediction: float, confidence: int):
    """
    Load the results widget UI, update its labels with prediction data,
    and display it inside the results frame of the main window.

    Args:
        window (QWidget):
            The main application window that contains the target results frame.

        prediction (float):
            The predicted value to display in the results widget.

        confidence (int):
            The confidence percentage to display in the results widget.
    """
    # Load the Results Widget.
    loader = QUiLoader()
    file = QFile("ui/resultsWidget.ui")
    file.open(QFile.OpenModeFlag.ReadOnly)
    results_widget = loader.load(file)
    file.close()

    # Get the target labels.
    prediction_label = results_widget.findChild(QLabel, "prediction")
    confidence_label = results_widget.findChild(QLabel, "confidence")

    # Modify the content of the placeholder to be the actual values.
    if prediction_label:
        prediction_label.setText(str(prediction))

    if confidence_label:
        confidence_label.setText(f"{confidence}%")

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


def run_agent_pipeline(window: QWidget):
    """
    Execute the AI agent pipeline: load data, run the trained model,
    and display prediction results in the UI.

    Args:
        window (QWidget):
            The main application window used to locate UI elements
            where results will be displayed.
    """
    # Step 1: Parse the files to make CSVs (RTF Parser or RTF -> PDF).

    # Step 2: Collect User Defined Value from the UI.

    # Step 3: Put the data in a single CSV.
    df = pd.read_csv("C:/Users/student02/data/all_ships_all_conditions_v4.csv")
    cols_to_drop = [
        "target_margin",
        "target_attained_index",
        "ship_version_id",
        "condition_code",
    ]

    # Step 4: Load the model.
    with open("models/model.pkl", "rb") as file:
        model = pickle.load(file)

    # Step 5: Feed the data to the model.
    X = df.select_dtypes(include=["number"]).drop(columns=cols_to_drop, errors="ignore")
    prediction = model.predict(X)

    # TODO: Get the actual value of the confidence in the model's prediction.
    confidence = 0

    # Step 6: Display the output.
    display_results(window, prediction, confidence)


def main():
    # Create the App and load the UI.
    app = QApplication(sys.argv)
    loader = QUiLoader()
    file = QFile("ui/agentMainWindow.ui")
    file.open(QFile.OpenModeFlag.ReadOnly)

    # Main Window Configuration.
    window = loader.load(file)
    window.setWindowTitle("AI Agent to predict Damage Stability")
    window.setWindowIcon(QIcon("assets/icon.png"))

    # Connect Main Dimensions Button with searching for PDFs.
    connect_file_browse_button(
        button_name="mainDimsBtn",
        window=window,
        caption="Browse Main Dimensions PDF",
        file_type="PDF Files (*.pdf)",
        line_edit_name="mainDimsLineEdit",
    )

    # Connect Openings Button with searching for PDFs.
    connect_file_browse_button(
        button_name="openingsBtn",
        window=window,
        caption="Browse Main Dimensions PDF",
        file_type="PDF Files (*.pdf)",
        line_edit_name="openingsLineEdit",
    )

    # Connect Internal Subdivision Button with searching for XMLs.
    connect_file_browse_button(
        button_name="internalSubdivBtn",
        window=window,
        caption="Browse Internal Subdivision XML",
        file_type="XML Files (*.xml)",
        line_edit_name="internalSubdivLineEdit",
    )

    # Connect the Run AI Agent pipeline.
    run_btn = window.findChild(QPushButton, "runBtn")
    if run_btn:
        run_btn.clicked.connect(lambda: run_agent_pipeline(window))

    # Close the file and run the app.
    file.close()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
