# src/ui/controllers/project_view_controller.py
# Copyright (c) 2025 Google. All rights reserved.

from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QMenu
import os
import sys
import subprocess
from PyQt6.QtCore import Qt

from src.core.config_manager import ConfigManager
from src.core.project_config import ProjectConfig
from src.ui.views.project_view_window import ProjectViewWindow
from src.logic.file_scanner import FileScanner
from src.logic.filter_engine import FilterEngine
from src.logic.export_manager import ExportManager

class ProjectViewController(QObject):
    """Manages the state and interactions of the ProjectViewWindow."""
    
    view_closed = pyqtSignal()

    def __init__(self, project_config: ProjectConfig, config_manager: ConfigManager):
        super().__init__()
        self._project_config = project_config
        self._config_manager = config_manager
        self._view = ProjectViewWindow(self._project_config.project_name)
        
        self._filtered_tree = {}
        self._connect_signals()

    def show(self):
        """Populates the view with initial data and shows the window."""
        self._view.set_filters_text(
            self._project_config.inclusive_filters,
            self._project_config.exclusive_filters
        )
        self._view.set_extension_overrides_text(self._project_config.extension_overrides)
        self._on_apply_filters()
        self._view.show()
    
    def _connect_signals(self):
        """Connects signals from the view to controller methods."""
        self._view.apply_filters_button.clicked.connect(self._on_apply_filters)
        self._view.back_action.triggered.connect(self._on_back)
        self._view.export_action.triggered.connect(self._on_export)
        self._view.file_tree_widget.customContextMenuRequested.connect(self._on_context_menu)
        self._view.closeEvent = self._on_close_event

    def _on_apply_filters(self):
        """Scans files, applies filters, and updates the tree view."""
        inclusive, exclusive = self._view.get_filters()
        self._project_config.inclusive_filters = inclusive
        self._project_config.exclusive_filters = exclusive

        overrides = self._view.get_extension_overrides()
        self._project_config.extension_overrides = overrides

        # Save the updated filters back to the config file
        self._config_manager.save_project(self._project_config)

        try:
            raw_tree = FileScanner.scan_directory(self._project_config.root_path)
            self._filtered_tree = FilterEngine.apply_filters(
                raw_tree,
                self._project_config.root_path,
                inclusive,
                exclusive
            )
            self._view.populate_file_tree(self._filtered_tree)
        except ValueError as e:
            QMessageBox.critical(self._view, "Error Scanning Directory", str(e))
            self._filtered_tree = {}
            self._view.populate_file_tree({})
    
    def _on_export(self):
        """Handles the 'Export' action."""
        if not self._filtered_tree:
            QMessageBox.warning(self._view, "Export Failed", "No files to export. Try applying filters first.")
            return

        try:
            temp_dir = ExportManager.export_files(
                self._filtered_tree,
                self._project_config.root_path,
                self._project_config.extension_overrides
            )
            
            msg_box = QMessageBox(self._view)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText("Export Complete")
            msg_box.setInformativeText(f"Files have been exported to:\n{temp_dir}")
            open_button = msg_box.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
            msg_box.addButton(QMessageBox.StandardButton.Ok)
            msg_box.exec()

            if msg_box.clickedButton() == open_button:
                if sys.platform == "win32":
                    os.startfile(temp_dir)
                elif sys.platform == "darwin": # macOS
                    subprocess.run(["open", temp_dir])
                else: # Linux
                    subprocess.run(["xdg-open", temp_dir])

        except Exception as e:
            QMessageBox.critical(self._view, "Export Error", f"An unexpected error occurred during export:\n{e}")

    def _on_back(self):
        """Handles the 'Back to Projects' action."""
        self._view.close() # Triggers the closeEvent

    def _on_close_event(self, event):
        """Emits a signal when the window is closed."""
        self.view_closed.emit()
        event.accept()

    def _on_context_menu(self, point):
        """Shows a context menu for the clicked tree item."""
        item = self._view.file_tree_widget.itemAt(point)
        if not item:
            return

        # Path is in the 3rd column (index 2)
        item_path = item.text(2)
        relative_path = os.path.relpath(item_path, self._project_config.root_path)

        menu = QMenu()
        exclude_action = menu.addAction("Exclude from Export")
        include_action = menu.addAction("Include in Export")

        exclude_action.triggered.connect(lambda: self._on_context_exclude(relative_path))
        include_action.triggered.connect(lambda: self._on_context_include(relative_path))
        
        menu.exec(self._view.file_tree_widget.mapToGlobal(point))

    def _on_context_exclude(self, relative_path_to_exclude: str):
        """Adds an item's path to the exclusive filters."""
        # Normalize path for consistency
        path_to_add = relative_path_to_exclude.replace(os.sep, '/')
        if os.path.isdir(os.path.join(self._project_config.root_path, relative_path_to_exclude)):
            path_to_add += '/' # Add trailing slash for directories

        inclusive, exclusive = self._view.get_filters()
        
        if path_to_add not in exclusive:
            exclusive.append(path_to_add)
            self._view.set_filters_text(inclusive, exclusive)
            self._on_apply_filters()

    def _on_context_include(self, relative_path_to_include: str):
        """Removes an item's path from the exclusive filters."""
        path_to_remove = relative_path_to_include.replace(os.sep, '/')
        dir_path_to_remove = path_to_remove + '/'

        inclusive, exclusive = self._view.get_filters()

        # Check for both file and directory formats and remove them
        updated_exclusive = [p for p in exclusive if p != path_to_remove and p != dir_path_to_remove]
        
        if len(updated_exclusive) < len(exclusive):
            self._view.set_filters_text(inclusive, updated_exclusive)
            self._on_apply_filters()