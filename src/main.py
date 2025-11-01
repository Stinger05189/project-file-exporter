# src/main.py
# Copyright (c) 2025 Google. All rights reserved.

import sys

from PyQt6.QtWidgets import QApplication

from src.core.config_manager import ConfigManager
from src.ui.controllers.landing_controller import LandingController
from src.ui.styling import setup_app_theme

def main():
    """The main entry point for the application."""
    # Initialize the Qt Application
    app = QApplication(sys.argv)
    setup_app_theme()

    # Initialize the core components
    config_manager = ConfigManager()
    config_manager.load_projects()

    # Initialize the main controller, which creates the landing window
    main_controller = LandingController(config_manager)

    # Show the main window and start the application
    main_controller.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()