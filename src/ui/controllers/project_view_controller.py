# src/ui/controllers/project_view_controller.py
# Copyright (c) 2025 Google. All rights reserved.

from PyQt6.QtCore import pyqtSignal, QObject, QTimer
from PyQt6.QtWidgets import (
    QFileDialog, QMessageBox, QMenu, QTreeWidgetItemIterator, QTreeWidgetItem
)
from PyQt6.QtGui import QAction
import os
import sys
import subprocess
import tempfile
from datetime import datetime
import copy
from PyQt6.QtCore import Qt
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.core.config_manager import ConfigManager
from src.core.project_config import ProjectConfig
from src.ui.views.project_view_window import ProjectViewWindow
from src.ui.views.help_dialog import HelpDialog
from src.logic.file_scanner import FileScanner
from src.logic.filter_engine import FilterEngine
from src.logic.export_manager import ExportManager
from src.ui.styling import apply_theme, save_theme_setting, load_theme_setting

# Signal bridge to safely communicate from watchdog's thread to the GUI thread.
class WatchdogEmitter(QObject):
    """Emits a signal when a file system event occurs."""
    file_changed = pyqtSignal()

class ProjectChangeHandler(FileSystemEventHandler):
    """A simple event handler that triggers a callback on any file system event."""
    def __init__(self, emitter: WatchdogEmitter):
        super().__init__()
        self.emitter = emitter

    def on_any_event(self, event):
        """On any file system event, emit the file_changed signal."""
        self.emitter.file_changed.emit()

class ProjectViewController(QObject):
    """Manages the state and interactions of the ProjectViewWindow."""

    view_closed = pyqtSignal()

    def __init__(self, project_config: ProjectConfig, config_manager: ConfigManager):
        super().__init__()
        self._project_config = project_config
        self._config_manager = config_manager
        self._view = ProjectViewWindow(self._project_config.project_name)
        
        self._filtered_tree = {}
        self._filtered_markdown_tree = {}
        # State for UI toggles
        self._show_full_path = False
        self._hide_excluded = False

        # File watcher for automatic refreshes
        self._observer = None
        
        # Setup for thread-safe signal-based watcher
        self._watchdog_emitter = WatchdogEmitter()
        self._watchdog_emitter.file_changed.connect(self._request_refresh)

        # Debounce timer for file watcher to prevent excessive refreshes
        self._refresh_timer = QTimer()
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(500) # 500 ms delay
        self._refresh_timer.timeout.connect(lambda: self._on_apply_filters(is_auto_refresh=True))

        self._connect_signals()

    def show(self):
        """Populates the view with initial data and shows the window."""
        self._view.set_blacklisted_paths_text(self._project_config.blacklisted_paths)
        self._view.set_filters_text(
            self._project_config.inclusive_filters,
            self._project_config.exclusive_filters
        )
        self._view.set_extension_overrides_text(self._project_config.extension_overrides)
        # Load new tree config
        self._view.set_tree_filters_text(self._project_config.tree_exclusive_filters)
        self._view.set_use_gitignore_state(self._project_config.tree_use_gitignore)
        
        # Load and apply UI toggle states from config
        self._show_full_path = self._project_config.ui_state.get("show_full_path", False)
        self._hide_excluded = self._project_config.ui_state.get("hide_excluded", False)
        self._view.toggle_path_action.setChecked(self._show_full_path)
        self._view.hide_excluded_action.setChecked(self._hide_excluded)

        # Set the correct theme radio button based on the saved setting
        current_theme = load_theme_setting()
        if current_theme == "dark":
            self._view.dark_theme_action.setChecked(True)
        elif current_theme == "light":
            self._view.light_theme_action.setChecked(True)
        else:
            self._view.auto_theme_action.setChecked(True)

        # Pass a flag to indicate this is the first load
        self._on_apply_filters(is_initial_load=True)
        self._view.show()
        # Apply window geometry, splitter state etc. after showing the window
        self._view.apply_ui_state(self._project_config.ui_state)

        self._start_file_watcher()
    
    def _connect_signals(self):
        """Connects signals from the view to controller methods."""
        self._view.apply_filters_button.clicked.connect(self._on_apply_filters)
        self._view.back_action.triggered.connect(self._on_back)
        self._view.export_button.clicked.connect(self._on_export)
        self._view.open_root_action.triggered.connect(self._on_open_root_path)
        self._view.open_export_action.triggered.connect(self._on_open_export_path)
        self._view.help_action.triggered.connect(self._show_help_dialog)
        self._view.toggle_path_action.triggered.connect(self._on_toggle_path_view)
        self._view.hide_excluded_action.triggered.connect(self._on_toggle_hide_excluded)
        self._view.file_tree_widget.customContextMenuRequested.connect(self._on_context_menu)
        # New connections
        self._view.markdown_tree_widget.customContextMenuRequested.connect(self._on_context_menu)
        self._view.main_tab_widget.currentChanged.connect(self._on_tab_changed)
        self._view.use_gitignore_checkbox.stateChanged.connect(self._on_apply_filters)
        
        self._view.closeEvent = self._on_close_event
        self._view.theme_action_group.triggered.connect(self._on_theme_changed)

    def _on_theme_changed(self, action: QAction):
        """Applies and saves the selected theme."""
        theme_text = action.text()
        theme_map = {
            "Dark": "dark",
            "Light": "light",
            "Auto (System)": "auto"
        }
        theme = theme_map.get(theme_text, "auto")
        
        apply_theme(theme)
        save_theme_setting(theme)
        pass

    def _request_refresh(self):
        """Safely starts the refresh timer from the main GUI thread."""
        self._refresh_timer.start()
        pass

    def _on_tab_changed(self, index: int):
        """Swaps the configuration panel view when the main tab changes."""
        self._view.config_stack.setCurrentIndex(index)

    def _on_toggle_path_view(self, checked: bool):
        """Handles the 'Show Full Paths' toggle action."""
        self._show_full_path = checked
        self._on_apply_filters()

    def _on_toggle_hide_excluded(self, checked: bool):
        """Handles the 'Hide Excluded Items' toggle action."""
        self._hide_excluded = checked
        self._on_apply_filters()

    def _on_apply_filters(self, is_initial_load: bool = False, is_auto_refresh: bool = False):
        """Scans files, applies filters, and updates the tree view."""
        if not is_initial_load:
            # 1. Preserve the expanded state of both trees on refresh
            expanded_paths = self._view.get_expanded_item_paths()
            markdown_expanded_paths = self._view.get_markdown_expanded_item_paths()
        else:
            # On initial load, restore state from the config file
            ui_state = self._project_config.ui_state
            expanded_paths = set(ui_state.get("expanded_paths", []))
            markdown_expanded_paths = set(ui_state.get("markdown_expanded_paths", []))

        # Only read from UI and save if the action was triggered by the user
        if not is_auto_refresh:
            # Save state from UI for File Export
            self._project_config.blacklisted_paths = self._view.get_blacklisted_paths()
            self._project_config.inclusive_filters, self._project_config.exclusive_filters = self._view.get_filters()
            self._project_config.extension_overrides = self._view.get_extension_overrides()
            # Save state from UI for Tree Export
            self._project_config.tree_exclusive_filters = self._view.get_tree_filters()
            self._project_config.tree_use_gitignore = self._view.get_use_gitignore_state()
            
            self._config_manager.save_project(self._project_config)

        try:
            raw_tree, gitignore_rules = FileScanner.scan_directory(
                self._project_config.root_path,
                self._project_config.blacklisted_paths
            )

            # --- Process File Export Tree (Tab 1) ---
            self._filtered_tree = FilterEngine.apply_filters(
                copy.deepcopy(raw_tree),
                self._project_config.root_path,
                self._project_config.inclusive_filters,
                self._project_config.exclusive_filters
            )
            self._view.populate_file_tree(
                self._filtered_tree, self._project_config.extension_overrides,
                self._project_config.root_path, self._show_full_path, self._hide_excluded
            )
    
            # --- Process Markdown Export Tree (Tab 2) ---
            tree_exclude_filters = self._project_config.tree_exclusive_filters
            if self._project_config.tree_use_gitignore:
                tree_exclude_filters = tree_exclude_filters + gitignore_rules

            self._filtered_markdown_tree = FilterEngine.apply_filters(
                copy.deepcopy(raw_tree), self._project_config.root_path,
                [], # No inclusive filters for the markdown tree
                tree_exclude_filters
            )
            self._view.populate_markdown_tree(self._filtered_markdown_tree, self._hide_excluded)

            # --- Restore UI State and Update Stats ---
            self._view.apply_expanded_state(expanded_paths)
            self._view.apply_markdown_expanded_state(markdown_expanded_paths)
            included, excluded, size = self._calculate_export_stats(self._filtered_tree)
            self._view.update_status_bar(included, excluded, size)
            
            if not is_auto_refresh:
                 self._project_config.last_known_included_count = included

        except ValueError as e:
            QMessageBox.critical(self._view, "Error Scanning Directory", str(e))
            self._filtered_tree = {}
            self._filtered_markdown_tree = {}
            self._view.populate_file_tree({}, {}, self._project_config.root_path, self._show_full_path, self._hide_excluded)
            self._view.populate_markdown_tree({}, self._hide_excluded)
            self._view.update_status_bar(0, 0, 0)
    
    def _on_export(self):
        """Handles the 'Export' action for both files and the markdown tree."""
        if not self._filtered_tree:
            QMessageBox.warning(self._view, "Export Failed", "No files to export. Try applying filters first.")
            return

        try:
            # 1. Export the files as usual
            temp_dir = ExportManager.export_files(
                self._filtered_tree,
                self._project_config.root_path,
                self._project_config.extension_overrides
            )
            
            # 2. Export the markdown tree to the same directory
            ExportManager.export_markdown_tree(self._filtered_markdown_tree, temp_dir)
            
            # 3. Update metadata and open the folder
            self._project_config.export_count += 1
            self._config_manager.save_project(self._project_config)
            
            if sys.platform == "win32":
                os.startfile(temp_dir)
            elif sys.platform == "darwin": # macOS
                subprocess.run(["open", temp_dir], check=True)
            else: # Linux
                subprocess.run(["xdg-open", temp_dir], check=True)

        except Exception as e:
            QMessageBox.critical(self._view, "Export Error", f"An unexpected error occurred during export:\n{e}")

    def _on_open_root_path(self):
        """Opens the project's root source directory."""
        try:
            root_path = self._project_config.root_path
            if sys.platform == "win32":
                os.startfile(root_path)
            elif sys.platform == "darwin": # macOS
                subprocess.run(["open", root_path], check=True)
            else: # Linux
                subprocess.run(["xdg-open", root_path], check=True)
        except Exception as e:
            QMessageBox.critical(self._view, "Error", f"Could not open root directory:\n{e}")
        pass
    def _on_open_export_path(self):
        """Creates and opens the target export directory."""
        try:
            temp_dir = os.path.join(tempfile.gettempdir(), "ProjectFileExporter_Export")
            os.makedirs(temp_dir, exist_ok=True)
            
            if sys.platform == "win32":
                os.startfile(temp_dir)
            elif sys.platform == "darwin": # macOS
                subprocess.run(["open", temp_dir], check=True)
            else: # Linux
                subprocess.run(["xdg-open", temp_dir], check=True)
        except Exception as e:
            QMessageBox.critical(self._view, "Error", f"Could not open export directory:\n{e}")
        pass
        
    def _on_back(self):
        """Handles the 'Back to Projects' action."""
        self._view.close() # Triggers the closeEvent
        pass

    def _on_close_event(self, event):
        """Emits a signal when the window is closed."""
        self._stop_file_watcher()
        # Save the current UI state before closing
        current_state = self._view.get_ui_state()
        current_state["show_full_path"] = self._show_full_path
        current_state["hide_excluded"] = self._hide_excluded
        
        # Add markdown tree state to the config
        markdown_expanded = self._view.get_markdown_expanded_item_paths()
        current_state["markdown_expanded_paths"] = sorted(list(markdown_expanded))

        self._project_config.ui_state = current_state
        # Save new tree config state
        self._project_config.tree_exclusive_filters = self._view.get_tree_filters()
        self._project_config.tree_use_gitignore = self._view.get_use_gitignore_state()

        self._config_manager.save_project(self._project_config)
        self.view_closed.emit()
        event.accept()

    def _on_context_menu(self, point):
        """Shows a context menu for the clicked tree item, aware of the active tab."""
        active_tab_index = self._view.main_tab_widget.currentIndex()
        if active_tab_index == 0:
            tree = self._view.file_tree_widget
        else:
            tree = self._view.markdown_tree_widget
            
        item = tree.itemAt(point)
        if not item:
            return
        
        # This logic ensures that if you right-click an unselected item, it becomes
        # the *only* selected item. If you right-click an already selected item,
        # the selection remains unchanged.
        if not item.isSelected():
            tree.clearSelection()
            item.setSelected(True)

        # Retrieve data from the item that was actually clicked
        item_path = item.data(4, Qt.ItemDataRole.UserRole)
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if not item_path:
            return

        menu = QMenu()
        
        # Add expand/collapse options for directories, only if a single directory is selected
        if item_type == "directory" and len(tree.selectedItems()) == 1:
            if item.isExpanded():
                collapse_action = menu.addAction("Collapse All")
                collapse_action.triggered.connect(lambda: self._on_expand_collapse_all(item, expand=False))
            else:
                expand_action = menu.addAction("Expand All")
                expand_action.triggered.connect(lambda: self._on_expand_collapse_all(item, expand=True))
            menu.addSeparator()

        exclude_action = menu.addAction("Exclude from Export")
        include_action = menu.addAction("Include in Export")
    
        # Connect actions to handlers that operate on the entire selection
        exclude_action.triggered.connect(self._on_context_exclude)
        include_action.triggered.connect(self._on_context_include)
        
        menu.exec(tree.mapToGlobal(point))

    def _on_expand_collapse_all(self, start_item: QTreeWidgetItem, expand: bool):
        """Recursively expands or collapses all children of a given item."""
        start_item.setExpanded(expand)
        iterator = QTreeWidgetItemIterator(start_item)
        while iterator.value():
            item = iterator.value()
            item.setExpanded(expand)
            iterator += 1
        pass

    def _on_context_exclude(self):
        """Adds paths of selected items to the appropriate exclusive filter list."""
        active_tab_index = self._view.main_tab_widget.currentIndex()
        if active_tab_index == 0:
            tree = self._view.file_tree_widget
            inclusive, exclusive = self._view.get_filters()
        else:
            tree = self._view.markdown_tree_widget
            inclusive = [] # Not used for markdown tree
            exclusive = self._view.get_tree_filters()

        selected_items = tree.selectedItems()
        if not selected_items:
            return

        exclusive_set = set(exclusive)
        paths_were_added = False

        for item in selected_items:
            full_path = item.data(4, Qt.ItemDataRole.UserRole)
            item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if not full_path: continue
            relative_path = os.path.relpath(full_path, self._project_config.root_path)
            path_to_add = relative_path.replace(os.sep, '/')
            if item_type == "directory": path_to_add += '/'
            if path_to_add not in exclusive_set:
                exclusive_set.add(path_to_add)
                paths_were_added = True

        if paths_were_added:
            if active_tab_index == 0:
                self._view.set_filters_text(inclusive, sorted(list(exclusive_set)))
            else:
                self._view.set_tree_filters_text(sorted(list(exclusive_set)))
            self._on_apply_filters()

    def _on_context_include(self):
        """Removes paths of selected items from the appropriate exclusive filter list."""
        active_tab_index = self._view.main_tab_widget.currentIndex()
        if active_tab_index == 0:
            tree = self._view.file_tree_widget
            inclusive, exclusive = self._view.get_filters()
        else:
            tree = self._view.markdown_tree_widget
            inclusive = [] # Not used
            exclusive = self._view.get_tree_filters()

        selected_items = tree.selectedItems()
        if not selected_items:
            return
            
        # Collect all possible path formats to remove for the selected items
        paths_to_remove = set()
        for item in selected_items:
            full_path = item.data(4, Qt.ItemDataRole.UserRole)
            if not full_path: continue
            relative_path = os.path.relpath(full_path, self._project_config.root_path)
            path_as_file = relative_path.replace(os.sep, '/')
            path_as_dir = path_as_file + '/'
            paths_to_remove.add(path_as_file)
            paths_to_remove.add(path_as_dir)
        
        original_count = len(exclusive)
        updated_exclusive = [p for p in exclusive if p not in paths_to_remove]
        
        if len(updated_exclusive) < original_count:
            if active_tab_index == 0:
                self._view.set_filters_text(inclusive, updated_exclusive)
            else:
                self._view.set_tree_filters_text(updated_exclusive)
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
        pass

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
        pass

    def _start_file_watcher(self):
        """Initializes and starts the file system observer."""
        if self._observer:
            self._stop_file_watcher() # Ensure any existing observer is stopped

        # Pass the thread-safe emitter to the handler.
        handler = ProjectChangeHandler(self._watchdog_emitter)
        self._observer = Observer()
        self._observer.schedule(handler, self._project_config.root_path, recursive=True)
        try:
            self._observer.start()
        except Exception as e:
            print(f"Error starting file watcher: {e}")
        pass

    def _stop_file_watcher(self):
        """Stops and cleans up the file system observer."""
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()
        self._observer = None
        pass