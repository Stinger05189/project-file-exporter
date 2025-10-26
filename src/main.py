# src/main.py
# Copyright (c) 2025 Google. All rights reserved.

import sys
# os is no longer needed here

# The sys.path modification is no longer needed with corrected imports.

from PyQt6.QtWidgets import QApplication

from src.core.config_manager import ConfigManager
from src.ui.controllers.project_list_controller import ProjectListController

DARK_THEME_QSS = """
QWidget {
    background-color: #2b2b2b;
    color: #f0f0f0;
    font-size: 10pt;
    font-family: "Segoe UI", "Cantarell", "sans-serif";
}
QMainWindow {
    background-color: #3c3f41;
}
QPushButton {
    background-color: #555555;
    border: 1px solid #777777;
    padding: 6px;
    border-radius: 3px;
}
QPushButton:hover {
    background-color: #6a6a6a;
}
QPushButton:pressed {
    background-color: #4a4a4a;
}
QPushButton:disabled {
    background-color: #404040;
    color: #888888;
}
QTextEdit, QLineEdit {
    background-color: #3c3f41;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 4px;
    color: #f0f0f0;
}
QTextBrowser {
    background-color: #2b2b2b;
    border: 1px solid #555555;
    padding: 8px;
}
QListWidget {
    background-color: #3c3f41;
    border: 1px solid #555555;
    alternate-background-color: #45484a;
}
QTreeWidget {
    background-color: #3c3f41;
    border: 1px solid #555555;
    alternate-background-color: #45484a;
}
QHeaderView::section {
    background-color: #4a4a4a;
    border: 1px solid #555555;
    padding: 4px;
    font-weight: bold;
}
QToolBar {
    background-color: #3c3f41;
    border: none;
}
QMessageBox {
    background-color: #3c3f41;
}
QInputDialog {
    background-color: #3c3f41;
}
QSplitter::handle {
    background-color: #4a4a4a;
}
QSplitter::handle:hover {
    background-color: #6a6a6a;
}
QSplitter::handle:pressed {
    background-color: #787878;
}
QStatusBar {
    background-color: #3c3f41;
}
QStatusBar::item {
    border: none;
}
QLabel {
    color: #f0f0f0;
}
QMenu {
    background-color: #3c3f41;
    border: 1px solid #555555;
}
QMenu::item:selected {
    background-color: #5a5a5a;
}
"""

def main():
    """The main entry point for the application."""
    # Initialize the Qt Application
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME_QSS)

    # Initialize the core components
    config_manager = ConfigManager()
    config_manager.load_projects()

    # Initialize the main controller, which creates the main window
    main_controller = ProjectListController(config_manager)

    # Show the main window and start the application
    main_controller.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()