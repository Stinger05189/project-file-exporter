# src/ui/controllers/project_browser_controller.py
# Copyright (c) 2025 Google. All rights reserved.

"""
Controller for the project browser window.
"""

from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QTreeWidgetItem, QInputDialog

from src.core.config_manager import ConfigManager
from src.ui.views.project_browser_window import ProjectBrowserWindow
from src.ui.views.project_edit_dialog import ProjectEditDialog
from src.ui.controllers.project_view_controller import ProjectViewController

class ProjectBrowserController(QObject):
    """Manages the state and interactions of the ProjectBrowserWindow."""
    
    view_closed = pyqtSignal()

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self._config_manager = config_manager
        self._view = ProjectBrowserWindow()
        self._project_view_controller = None

        self._connect_signals()

    def show(self):
        """Loads project data and shows the window."""
        self._update_project_list()
        self._view.show()

    def _connect_signals(self):
        """Connects view signals to controller methods."""
        self._view.open_project_button.clicked.connect(self._on_open_project)
        self._view.edit_project_button.clicked.connect(self._on_edit_project)
        self._view.duplicate_project_button.clicked.connect(self._on_duplicate_project)
        self._view.remove_project_button.clicked.connect(self._on_remove_project)
        self._view.create_project_button.clicked.connect(self._on_create_project)
        self._view.back_action.triggered.connect(self._on_back)
        self._view.closeEvent = self._on_close_event

    def _update_project_list(self):
        """Fetches all projects and populates the tree widget."""
        self._view.project_tree_widget.clear()
        projects = self._config_manager.get_all_projects()
        
        for p in projects:
            try:
                # Parse ISO date for display
                last_opened_dt = datetime.fromisoformat(p.last_opened)
                last_opened_str = last_opened_dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                last_opened_str = "N/A"

            item = QTreeWidgetItem([
                p.project_name,
                last_opened_str,
                str(p.export_count),
                str(p.last_known_included_count),
                p.root_path
            ])
            self._view.project_tree_widget.addTopLevelItem(item)

    def _on_open_project(self):
        """Handles the 'Open Project' action."""
        selected_items = self._view.project_tree_widget.selectedItems()
        if not selected_items:
            return
        
        project_name = selected_items[0].text(0)
        try:
            project_config = self._config_manager.get_project(project_name)

            # Update and save the last opened time immediately on the open action.
            project_config.last_opened = datetime.utcnow().isoformat()
            self._config_manager.save_project(project_config)

            self._project_view_controller = ProjectViewController(project_config, self._config_manager)
            self._project_view_controller.view_closed.connect(self.show)
            self._project_view_controller.show()
            self._view.hide()
        except KeyError:
            QMessageBox.warning(self._view, "Error", f"Could not find project '{project_name}'.")

    def _on_edit_project(self):
        """Handles editing a selected project's name."""
        selected_items = self._view.project_tree_widget.selectedItems()
        if not selected_items:
            return

        project_name = selected_items[0].text(0)
        try:
            project_to_edit = self._config_manager.get_project(project_name)
            dialog = ProjectEditDialog(self._view, project_to_edit.project_name, project_to_edit.root_path)
            details = dialog.get_details()

            if details:
                new_name, _ = details
                if new_name and new_name != project_name:
                    self._config_manager.rename_project(project_name, new_name)
                    self._update_project_list()
        except (ValueError, KeyError) as e:
            QMessageBox.warning(self._view, "Error", str(e))

    def _on_duplicate_project(self):
        """Handles duplicating a selected project."""
        selected_items = self._view.project_tree_widget.selectedItems()
        if not selected_items:
            return

        original_name = selected_items[0].text(0)
        
        new_name, ok = QInputDialog.getText(
            self._view,
            "Duplicate Project",
            f"Enter a new name for the duplicated project:",
            text=f"{original_name} (copy)"
        )

        if ok and new_name:
            try:
                self._config_manager.duplicate_project(original_name, new_name.strip())
                self._update_project_list()
            except ValueError as e:
                QMessageBox.warning(self._view, "Error", str(e))

    def _on_remove_project(self):
        """Handles removing one or more selected projects."""
        selected_items = self._view.project_tree_widget.selectedItems()
        if not selected_items:
            return

        project_names = [item.text(0) for item in selected_items]
        
        title = f"Confirm Deletion"
        message = f"Are you sure you want to permanently delete these {len(project_names)} project(s)?"
        reply = QMessageBox.question(self._view, title, message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            for name in project_names:
                self._config_manager.remove_project(name)
            self._update_project_list()
    
    def _on_create_project(self):
        """Handles creating a new project."""
        dialog = ProjectEditDialog(self._view)
        details = dialog.get_details()
        if details:
            name, path = details
            if name and path:
                try:
                    self._config_manager.add_project(name, path)
                    self._update_project_list()
                except ValueError as e:
                    QMessageBox.warning(self._view, "Error", str(e))
            else:
                QMessageBox.warning(self._view, "Error", "Project name and root path cannot be empty.")

    def _on_back(self):
        """Closes the browser and returns to the landing page."""
        self._view.close()

    def _on_close_event(self, event):
        """Emits a signal when the window is closed."""
        self.view_closed.emit()
        event.accept()