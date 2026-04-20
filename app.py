# Import standard library packages.
import sys

# Import third party packages.
from PySide6.QtGui import QIcon
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication


def main():
    # Create the App and load the UI.
    app = QApplication(sys.argv)
    loader = QUiLoader()
    file = QFile("ui/agentMainWindow.ui")
    file.open(QFile.OpenModeFlag.ReadOnly)
    window = loader.load(file)
    window.setWindowTitle("AI Agent to predict Damage Stability")
    window.setWindowIcon(QIcon("assets/icon.png"))

    # Close the file and run the app.
    file.close()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
