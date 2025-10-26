# src/ui/controllers/project_view_controller.py
# Copyright (c) 2025 Google. All rights reserved.

from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QFileDialog, QMessageBox, QMenu, QTreeWidgetItemIterator, QTreeWidgetItem
)
import os
import sys
import subprocess
from PyQt6.QtCore import Qt

from src.core.config_manager import ConfigManager
from src.core.project_config import ProjectConfig
from src.ui.views.project_view_window import ProjectViewWindow
from src.ui.views.help_dialog import HelpDialog
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
        self._show_full_path = False # New state for path view
        self._connect_signals()

    def show(self):
        """Populates the view with initial data and shows the window."""
        self._view.set_blacklisted_paths_text(self._project_config.blacklisted_paths)
        self._view.set_filters_text(
            self._project_config.inclusive_filters,
            self._project_config.exclusive_filters
        )
        self._view.set_extension_overrides_text(self._project_config.extension_overrides)
        # Pass a flag to indicate this is the first load
        self._on_apply_filters(is_initial_load=True)
        self._view.show()
        # Apply window geometry, splitter state etc. after showing the window
        self._view.apply_ui_state(self._project_config.ui_state)
        self._view.toggle_path_action.setChecked(self._show_full_path)
    
    def _connect_signals(self):
        """Connects signals from the view to controller methods."""
        self._view.apply_filters_button.clicked.connect(self._on_apply_filters)
        self._view.back_action.triggered.connect(self._on_back)
        self._view.export_action.triggered.connect(self._on_export)
        self._view.help_action.triggered.connect(self._show_help_dialog)
        self._view.toggle_path_action.triggered.connect(self._on_toggle_path_view)
        self._view.file_tree_widget.customContextMenuRequested.connect(self._on_context_menu)
        self._view.closeEvent = self._on_close_event

    def _on_toggle_path_view(self, checked: bool):
        """Handles the 'Show Full Paths' toggle action."""
        self._show_full_path = checked
        # Re-populate the tree to reflect the change
        self._on_apply_filters()

    def _on_apply_filters(self, is_initial_load: bool = False):
        """Scans files, applies filters, and updates the tree view."""
        if not is_initial_load:
            # 1. Preserve the expanded state of the tree on refresh
            expanded_paths = self._view.get_expanded_item_paths()
        else:
            # On initial load, we will restore state from the config file
            expanded_paths = set(self._project_config.ui_state.get("expanded_paths", []))

        blacklist = self._view.get_blacklisted_paths()
        self._project_config.blacklisted_paths = blacklist

        inclusive, exclusive = self._view.get_filters()
        self._project_config.inclusive_filters = inclusive
        self._project_config.exclusive_filters = exclusive

        overrides = self._view.get_extension_overrides()
        self._project_config.extension_overrides = overrides

        # Save the updated filters back to the config file
        self._config_manager.save_project(self._project_config)

        try:
            raw_tree = FileScanner.scan_directory(
                self._project_config.root_path,
                self._project_config.blacklisted_paths
            )
            self._filtered_tree = FilterEngine.apply_filters(
                raw_tree,
                self._project_config.root_path,
                inclusive,
                exclusive
            )
            # 2. Repopulate the tree, passing overrides and path view state
            self._view.populate_file_tree(
                self._filtered_tree,
                overrides,
                self._project_config.root_path,
                self._show_full_path
            )

            # 3. Restore the expanded state
            self._view.apply_expanded_state(expanded_paths)

            # 4. Calculate stats and update status bar
            included, excluded, size = self._calculate_export_stats(self._filtered_tree)
            self._view.update_status_bar(included, excluded, size)
        except ValueError as e:
            QMessageBox.critical(self._view, "Error Scanning Directory", str(e))
            self._filtered_tree = {}
            self._view.populate_file_tree({}, {}, self._project_config.root_path, self._show_full_path)
            self._view.update_status_bar(0, 0, 0)
    
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
            
            # Automatically open the folder without a dialog
            if sys.platform == "win32":
                os.startfile(temp_dir)
            elif sys.platform == "darwin": # macOS
                subprocess.run(["open", temp_dir], check=True)
            else: # Linux
                subprocess.run(["xdg-open", temp_dir], check=True)

        except Exception as e:
            QMessageBox.critical(self._view, "Export Error", f"An unexpected error occurred during export:\n{e}")

    def _on_back(self):
        """Handles the 'Back to Projects' action."""
        self._view.close() # Triggers the closeEvent

    def _on_close_event(self, event):
        """Emits a signal when the window is closed."""
        # Save the current UI state before closing
        current_state = self._view.get_ui_state()
        self._project_config.ui_state = current_state
        self._config_manager.save_project(self._project_config)
        self.view_closed.emit()
        event.accept()

    def _on_context_menu(self, point):
        """Shows a context menu for the clicked tree item."""
        item = self._view.file_tree_widget.itemAt(point)
        if not item:
            return

        # Path is stored in UserRole on the path column (index 3)
        item_path = item.data(3, Qt.ItemDataRole.UserRole)
        # Type is stored in a custom UserRole on the name column (index 0)
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if not item_path:
            return
        
        relative_path = os.path.relpath(item_path, self._project_config.root_path)

        menu = QMenu()
        
        # Add expand/collapse options for directories
        if item_type == "directory":
            if item.isExpanded():
                collapse_action = menu.addAction("Collapse All")
                collapse_action.triggered.connect(lambda: self._on_expand_collapse_all(item, expand=False))
            else:
                expand_action = menu.addAction("Expand All")
                expand_action.triggered.connect(lambda: self._on_expand_collapse_all(item, expand=True))
            menu.addSeparator()

        exclude_action = menu.addAction("Exclude from Export")
        include_action = menu.addAction("Include in Export")

        exclude_action.triggered.connect(lambda: self._on_context_exclude(relative_path))
        include_action.triggered.connect(lambda: self._on_context_include(relative_path))
        
        menu.exec(self._view.file_tree_widget.mapToGlobal(point))

    def _on_expand_collapse_all(self, start_item: QTreeWidgetItem, expand: bool):
        """Recursively expands or collapses all children of a given item."""
        start_item.setExpanded(expand)
        iterator = QTreeWidgetItemIterator(start_item)
        while iterator.value():
            item = iterator.value()
            item.setExpanded(expand)
            iterator += 1

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

    def _calculate_export_stats(self, node: dict) -> tuple[int, int, int]:
        """Recursively traverses the filtered tree to calculate file stats."""
        included_count = 0
        excluded_count = 0
        total_size = 0

        if node["type"] == "file":
            if node.get("status") == "included":
                included_count += 1
                try:
                    total_size += os.path.getsize(node["path"])
                except OSError:
                    pass # File might be inaccessible
            else:
                excluded_count += 1
        
        for child in node.get("children", []):
            i_count, e_count, size = self._calculate_export_stats(child)
            included_count += i_count
            excluded_count += e_count
            total_size += size
            
        return included_count, excluded_count, total_size

    def _show_help_dialog(self):
        """Displays a dialog with information on how to use filters."""
        help_text = """
# Filter Syntax Guide

Filters use **glob patterns** to include or exclude files and directories from the export.

---

### Key Rules
*   **Exclusive filters always take precedence.** If a file matches both an inclusive and an exclusive pattern, it will be **excluded**.
*   If **no inclusive filters** are provided, all files are considered included by default (before exclusion rules are applied).
*   To match a directory, end the pattern with a forward slash (e.g., `__pycache__/`).

---

### Common Patterns

| Pattern | Description                                        |
| :------ | :------------------------------------------------- |
| `*`       | Matches any sequence of characters in a name.      |
| `?`       | Matches any single character.                      |
| `[abc]`   | Matches one character from the set (a, b, or c).   |
| `**`      | Matches directories recursively (e.g. `src/**/*.ui`). |

---

### Examples
-   `*.py` &mdash; Matches all files ending with `.py`.
-   `assets/*.png` &mdash; Matches all PNGs directly inside the `assets` folder.
-   `.git/` &mdash; Excludes the Git metadata directory.
-   `*.log` &mdash; Excludes all log files.
"""
        dialog = HelpDialog(help_text, self._view)
        dialog.exec()