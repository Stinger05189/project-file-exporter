# src/ui/controllers/landing_controller.py
# Copyright (c) 2025 Google. All rights reserved.

"""
Controller for the main landing window.
"""

import os
import json
from datetime import datetime
from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QLabel, QWidget, QHBoxLayout, QPushButton, QMessageBox

from src.core.config_manager import ConfigManager
from src.ui.views.landing_window import LandingWindow
from src.ui.views.project_edit_dialog import ProjectEditDialog
from src.ui.controllers.project_browser_controller import ProjectBrowserController
from src.ui.controllers.project_view_controller import ProjectViewController

class LandingController(QObject):
    """Manages the state and interactions of the LandingWindow."""

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self._config_manager = config_manager
        self._view = LandingWindow()
        
        self._project_view_controller = None
        self._project_browser_controller = None

        self._connect_signals()

    def show(self):
        """Loads initial data and shows the landing window."""
        # The config manager still needs to be loaded once at startup
        # for other parts of the app to use its cache.
        self._config_manager.load_projects()
        self._update_recent_projects()
        self._view.show()

    def _connect_signals(self):
        """Connects signals from the view to controller methods."""
        self._view.browse_projects_button.clicked.connect(self._on_browse_projects)
        self._view.create_project_button.clicked.connect(self._on_create_project)

    def _update_recent_projects(self):
        """
        Fetches the 3 most recently modified project files from disk
        and populates the view.
        """
        # Clear existing recent projects
        layout = self._view.recent_projects_layout
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        try:
            # 1. Get all project file paths
            proj_dir = self._config_manager.projects_directory
            all_files = [
                os.path.join(proj_dir, f)
                for f in os.listdir(proj_dir)
                if f.endswith(".json") and os.path.isfile(os.path.join(proj_dir, f))
            ]

            # 2. Sort file paths by last modification time (most recent first)
            all_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
            
            # 3. Take the top 3
            recent_project_files = all_files[:3]

            if not recent_project_files:
                layout.addWidget(QLabel("No recent projects found. Create one to get started!"))
                return

            # 4. Load data for only the top 3 and create widgets
            for project_path in recent_project_files:
                with open(project_path, 'r') as f:
                    data = json.load(f)
                    project_name = data.get("project_name", "Unknown Project")
                    root_path = data.get("root_path", "N/A")

                # Create a widget for each recent project
                project_widget = QWidget()
                h_layout = QHBoxLayout(project_widget)
                
                name_label = QLabel(f"<b>{project_name}</b>")
                path_label = QLabel(f"<i>{root_path}</i>")
                path_label.setStyleSheet("color: #aaaaaa;")
                
                open_button = QPushButton("Open")
                edit_button = QPushButton("Edit")

                # Use a lambda to capture the current project name for the slot
                open_button.clicked.connect(lambda _, p=project_name: self._on_open_project(p))
                edit_button.clicked.connect(lambda _, p=project_name: self._on_edit_project(p))

                h_layout.addWidget(name_label)
                h_layout.addWidget(path_label)
                h_layout.addStretch()
                h_layout.addWidget(edit_button)
                h_layout.addWidget(open_button)

                layout.addWidget(project_widget)

        except (OSError, json.JSONDecodeError) as e:
            layout.addWidget(QLabel(f"Error loading recent projects: {e}"))


    def _on_open_project(self, project_name: str):
        """Handles opening a project."""
        try:
            # The config manager's cache should be up-to-date from the show() method.
            project_config = self._config_manager.get_project(project_name)
            
            # Update and save the last opened time immediately on the open action.
            # This action updates the file's modification time, which is what we now use for sorting.
            project_config.last_opened = datetime.utcnow().isoformat()
            self._config_manager.save_project(project_config)

            self._project_view_controller = ProjectViewController(project_config, self._config_manager)
            self._project_view_controller.view_closed.connect(self.show)
            self._project_view_controller.show()
            self._view.hide()
        except KeyError:
            QMessageBox.warning(self._view, "Error", f"Could not find project '{project_name}'.")

    def _on_edit_project(self, project_name: str):
        """Handles editing a project's name."""
        try:
            project_to_edit = self._config_manager.get_project(project_name)
            dialog = ProjectEditDialog(self._view, project_to_edit.project_name, project_to_edit.root_path)
            details = dialog.get_details()

            if details:
                new_name, _ = details
                if new_name and new_name != project_name:
                    self._config_manager.rename_project(project_name, new_name)
                    # A rename modifies the file, so this will update the recent list correctly.
                    self._update_recent_projects()
        except (ValueError, KeyError) as e:
            QMessageBox.warning(self._view, "Error", str(e))

    def _on_create_project(self):
        """Handles creating a new project."""
        dialog = ProjectEditDialog(self._view)
        details = dialog.get_details()
        if details:
            name, path = details
            if name and path:
                try:
                    self._config_manager.add_project(name, path)
                    # Creating a project modifies the directory, so this updates the list.
                    self._update_recent_projects()
                except ValueError as e:
                    QMessageBox.warning(self._view, "Error", str(e))
            else:
                QMessageBox.warning(self._view, "Error", "Project name and root path cannot be empty.")

    def _on_browse_projects(self):
        """Shows the project browser window."""
        self._project_browser_controller = ProjectBrowserController(self._config_manager)
        self._project_browser_controller.view_closed.connect(self.show)
        self._project_browser_controller.show()
        self._view.hide()