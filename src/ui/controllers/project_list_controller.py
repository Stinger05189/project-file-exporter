# src/ui/controllers/project_list_controller.py
# Copyright (c) 2025 Google. All rights reserved.

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QInputDialog

from src.core.config_manager import ConfigManager
from src.ui.views.project_list_window import ProjectListWindow
from src.ui.controllers.project_view_controller import ProjectViewController

class ProjectListController:
    """Manages the state and interactions of the ProjectListWindow."""

    def __init__(self, config_manager: ConfigManager):
        self._config_manager = config_manager
        self._view = ProjectListWindow()
        self._project_view_controller = None  # To hold the reference

        self._connect_signals()

    def show(self):
        """Loads initial data and shows the project list window."""
        self._update_project_list()
        self._view.show()

    def _connect_signals(self):
        """Connects signals from the view to controller methods."""
        self._view.add_project_button.clicked.connect(self._on_add_project)
        self._view.remove_project_button.clicked.connect(self._on_remove_project)
        self._view.open_project_button.clicked.connect(self._on_open_project)

    def _update_project_list(self):
        """Fetches all project names from the manager and updates the view."""
        project_names = [p.project_name for p in self._config_manager.get_all_projects()]
        self._view.populate_project_list(project_names)

    def _on_add_project(self):
        """Handles the 'Add Project' button click."""
        project_name, ok = QInputDialog.getText(self._view, "New Project", "Enter project name:")
        if ok and project_name:
            try:
                # Check if project name already exists
                if project_name in [p.project_name for p in self._config_manager.get_all_projects()]:
                     raise ValueError(f"A project with the name '{project_name}' already exists.")

                root_path = QFileDialog.getExistingDirectory(self._view, "Select Project Root Directory")
                if root_path:
                    self._config_manager.add_project(project_name, root_path)
                    self._update_project_list()
            except ValueError as e:
                QMessageBox.warning(self._view, "Error", str(e))

    def _on_remove_project(self):
        """Handles the 'Remove Project' button click."""
        project_names = self._view.get_selected_project_names()
        if not project_names:
            return

        # Adjust confirmation message for single vs. multiple projects
        if len(project_names) == 1:
            title = "Confirm Deletion"
            message = f"Are you sure you want to permanently delete the project '{project_names[0]}'?"
        else:
            title = "Confirm Multiple Deletions"
            message = f"Are you sure you want to permanently delete these {len(project_names)} projects?"

        reply = QMessageBox.question(
            self._view,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            errors = []
            for project_name in project_names:
                try:
                    self._config_manager.remove_project(project_name)
                except ValueError as e:
                    errors.append(str(e))
            
            self._update_project_list()

            if errors:
                QMessageBox.warning(self._view, "Error", "Some projects could not be removed:\n\n" + "\n".join(errors))

    def _on_open_project(self):
        """Handles the 'Open Project' button click."""
        project_name = self._view.get_selected_project_name()
        if not project_name:
            return

        try:
            project_config = self._config_manager.get_project(project_name)
            
            # Create and show the project view
            self._project_view_controller = ProjectViewController(project_config, self._config_manager)
            self._project_view_controller.show()
            self._project_view_controller.view_closed.connect(self.show) # Show this window again when the other closes
            self._view.hide()

        except KeyError:
            QMessageBox.warning(self._view, "Error", f"Could not find project '{project_name}'.")