# src/ui/controllers/project_view_controller.py
# Copyright (c) 2025 Google. All rights reserved.

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog
from PyQt6.QtCore import Qt

from src.core.config_manager import ConfigManager
from src.core.project_config import ProjectConfig
from src.ui.views.project_view_window import ProjectViewWindow
from src.logic.file_scanner import FileScanner
from src.logic.filter_engine import FilterEngine
from src.logic.export_manager import ExportManager

class ProjectViewController:
    """Manages the state and interactions of the ProjectViewWindow."""
    
    view_closed = pyqtSignal()

    def __init__(self, project_config: ProjectConfig, config_manager: ConfigManager):
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
        self._on_apply_filters()
        self._view.show()
    
    def _connect_signals(self):
        """Connects signals from the view to controller methods."""
        self._view.apply_filters_button.clicked.connect(self._on_apply_filters)
        self._view.back_action.triggered.connect(self._on_back)
        self._view.export_action.triggered.connect(self._on_export)
        self._view.closeEvent = self._on_close_event

    def _on_apply_filters(self):
        """Scans files, applies filters, and updates the tree view."""
        inclusive, exclusive = self._view.get_filters()
        self._project_config.inclusive_filters = inclusive
        self._project_config.exclusive_filters = exclusive

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

        dest_path = QFileDialog.getExistingDirectory(self._view, "Select Export Destination Directory")
        if not dest_path:
            return
        
        # This can be a long process, so a progress dialog is appropriate
        progress = QProgressDialog("Exporting files...", "Cancel", 0, 100, self._view)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)
        
        exporter = ExportManager.export_files(
            self._filtered_tree,
            self._project_config.root_path,
            dest_path
        )
        
        # A simple way to show progress without counting all files beforehand
        i = 0
        for _ in exporter:
            i = (i + 1) % 100 # Cycle the progress bar
            progress.setValue(i)
            if progress.wasCanceled():
                break

        progress.setValue(100)
        QMessageBox.information(self._view, "Export Complete", f"Files have been exported to:\n{dest_path}")

    def _on_back(self):
        """Handles the 'Back to Projects' action."""
        self._view.close() # Triggers the closeEvent

    def _on_close_event(self, event):
        """Emits a signal when the window is closed."""
        self.view_closed.emit()
        event.accept()