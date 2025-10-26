# src/main.py
# Copyright (c) 2025 Google. All rights reserved.

import sys
# os is no longer needed here

# The sys.path modification is no longer needed with corrected imports.

from PyQt6.QtWidgets import QApplication

from src.core.config_manager import ConfigManager
from src.ui.controllers.project_list_controller import ProjectListController

def main():
    """The main entry point for the application."""
    # Initialize the Qt Application
    app = QApplication(sys.argv)

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