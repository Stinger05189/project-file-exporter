# src/ui/controllers/project_view_controller.py
# Copyright (c) 2025 Google. All rights reserved.

import fnmatch

from PyQt6.QtCore import pyqtSignal, QObject, QTimer, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFileDialog, QMessageBox, QMenu, QTreeWidgetItemIterator, QTreeWidgetItem, 
    QApplication, QInputDialog, QListWidgetItem
)
import os
import sys
import subprocess
import tempfile
import json
from datetime import datetime, timezone
import copy
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
        # 1. Load Global Settings
        self._view.set_blacklisted_paths_text(self._project_config.blacklisted_paths)
        
        # 2. Load Active State (matches the active preset unless modified and not saved)
        self._view.set_all_filter_ui_state(
            inclusive=self._project_config.inclusive_filters,
            exclusive=self._project_config.exclusive_filters,
            tree_exclusive=self._project_config.tree_exclusive_filters,
            overrides=self._project_config.extension_overrides,
            use_gitignore=self._project_config.tree_use_gitignore
        )

        # 3. Load UI Toggle States
        self._show_full_path = self._project_config.ui_state.get("show_full_path", False)
        self._hide_excluded = self._project_config.ui_state.get("hide_excluded", False)
        self._view.toggle_path_action.setChecked(self._show_full_path)
        self._view.hide_excluded_action.setChecked(self._hide_excluded)

        # 4. Load Theme
        current_theme = load_theme_setting()
        if current_theme == "dark":
            self._view.dark_theme_action.setChecked(True)
        elif current_theme == "light":
            self._view.light_theme_action.setChecked(True)
        else:
            self._view.auto_theme_action.setChecked(True)

        # 5. Populate Presets
        self._populate_presets_combo()

        # 6. Initial Refresh & Show
        self._refresh_history_ui()
        self._on_apply_filters(is_initial_load=True)
        self._view.show()
        
        # Apply window geometry, splitter state etc. after showing the window
        self._view.apply_ui_state(self._project_config.ui_state)

        self._start_file_watcher()

    def _connect_signals(self):
        """Connects signals from the view to controller methods."""
        # Config & Export
        self._view.apply_filters_button.clicked.connect(self._on_apply_filters)
        self._view.export_button.clicked.connect(self._on_export)
        self._view.export_selection_btn.clicked.connect(self._on_export_selection_clicked)
        self._view.clipboard_export_button.clicked.connect(self._on_clipboard_export)
        self._view.copy_prompt_button.clicked.connect(self._on_copy_prompt)
        self._view.history_list_widget.itemDoubleClicked.connect(self._on_history_item_double_clicked)
        self._view.history_list_widget.itemSelectionChanged.connect(self._on_history_item_selected)
        
        # Preset Management
        self._view.preset_combo.currentIndexChanged.connect(self._on_preset_selection_changed)
        self._view.save_preset_btn.clicked.connect(self._on_save_preset_clicked)
        self._view.add_preset_btn.clicked.connect(self._on_add_preset_clicked)
        self._view.del_preset_btn.clicked.connect(self._on_delete_preset_clicked)

        # Toolbar Actions
        self._view.back_action.triggered.connect(self._on_back)
        self._view.open_root_action.triggered.connect(self._on_open_root_path)
        self._view.open_export_action.triggered.connect(self._on_open_export_path)
        self._view.help_action.triggered.connect(self._show_help_dialog)
        self._view.toggle_path_action.triggered.connect(self._on_toggle_path_view)
        self._view.hide_excluded_action.triggered.connect(self._on_toggle_hide_excluded)
        self._view.theme_action_group.triggered.connect(self._on_theme_changed)

        # Trees & Tabs
        self._view.file_tree_widget.customContextMenuRequested.connect(self._on_context_menu)
        self._view.markdown_tree_widget.customContextMenuRequested.connect(self._on_context_menu)
        self._view.main_tab_widget.currentChanged.connect(self._on_tab_changed)
        self._view.use_gitignore_checkbox.stateChanged.connect(self._on_apply_filters)
        self._view.file_tree_widget.itemSelectionChanged.connect(self._on_tree_selection_changed)
        
        # Window
        self._view.closeEvent = self._on_close_event

    # --- Preset Management Methods ---

    def _populate_presets_combo(self):
        """Fills the combo box with available presets and selects the active one."""
        self._view.preset_combo.blockSignals(True) # Prevent triggering selection logic
        self._view.preset_combo.clear()
        
        preset_names = sorted(self._project_config.presets.keys())
        # Ensure Default is always first
        if "Default" in preset_names:
            preset_names.remove("Default")
            preset_names.insert(0, "Default")
            
        self._view.preset_combo.addItems(preset_names)
        
        # Select active preset
        index = self._view.preset_combo.findText(self._project_config.active_preset_name)
        if index >= 0:
            self._view.preset_combo.setCurrentIndex(index)
            
        self._update_preset_buttons_state()
        self._view.preset_combo.blockSignals(False)

    def _update_preset_buttons_state(self):
        """Enables/Disables preset buttons based on selection."""
        current_preset = self._view.preset_combo.currentText()
        # Protect the Default preset from deletion
        if current_preset == "Default":
            self._view.del_preset_btn.setEnabled(False)
        else:
            self._view.del_preset_btn.setEnabled(True)

    def _on_preset_selection_changed(self):
        """Handles switching presets: Loads data, updates UI, saves config, refreshes tree."""
        new_preset_name = self._view.preset_combo.currentText()
        if not new_preset_name: return

        # 1. Update Active Name
        self._project_config.active_preset_name = new_preset_name
        
        # 2. Retrieve Data
        data = self._project_config.presets.get(new_preset_name, {})
        
        # 3. Update UI
        self._view.set_all_filter_ui_state(
            inclusive=data.get("inclusive_filters", []),
            exclusive=data.get("exclusive_filters", []),
            tree_exclusive=data.get("tree_exclusive_filters", []),
            overrides=data.get("extension_overrides", {}),
            use_gitignore=data.get("tree_use_gitignore", True)
        )
        
        self._update_preset_buttons_state()
        
        # 4. Update Internal Active State (The working copy)
        # This overwrites any unsaved "dirty" changes from the previous preset!
        self._project_config.inclusive_filters = data.get("inclusive_filters", [])
        self._project_config.exclusive_filters = data.get("exclusive_filters", [])
        self._project_config.tree_exclusive_filters = data.get("tree_exclusive_filters", [])
        self._project_config.tree_use_gitignore = data.get("tree_use_gitignore", True)
        self._project_config.extension_overrides = data.get("extension_overrides", {})

        # 5. Persist the change of selection
        self._config_manager.save_project(self._project_config)
        
        # 6. Auto-Refresh the tree and history UI
        self._refresh_history_ui()
        self._on_apply_filters(is_auto_refresh=True)

    def _on_save_preset_clicked(self):
        """Explicitly saves the current UI input values to the currently selected preset."""
        current_preset = self._view.preset_combo.currentText()
        
        # 1. Scrape UI
        inc, exc = self._view.get_filters()
        tree_exc = self._view.get_tree_filters()
        overrides = self._view.get_extension_overrides()
        use_git = self._view.get_use_gitignore_state()
        
        # 2. Update Preset Dictionary
        self._project_config.presets[current_preset] = {
            "inclusive_filters": inc,
            "exclusive_filters": exc,
            "tree_exclusive_filters": tree_exc,
            "tree_use_gitignore": use_git,
            "extension_overrides": overrides
        }
        
        # 3. Update Active Working Copy
        self._project_config.inclusive_filters = inc
        self._project_config.exclusive_filters = exc
        self._project_config.tree_exclusive_filters = tree_exc
        self._project_config.tree_use_gitignore = use_git
        self._project_config.extension_overrides = overrides

        # 4. Save to Disk
        self._config_manager.save_project(self._project_config)
        
        # 5. Refresh Tree
        self._on_apply_filters(is_auto_refresh=True)
        
        self._view.statusBar().showMessage(f"Preset '{current_preset}' saved successfully.", 3000)

    def _on_add_preset_clicked(self):
        """Creates a new preset based on the current UI settings."""
        name, ok = QInputDialog.getText(self._view, "New Preset", "Preset Name:")
        if ok and name:
            name = name.strip()
            if not name: return
            if name in self._project_config.presets:
                QMessageBox.warning(self._view, "Error", f"Preset '{name}' already exists.")
                return

            # Scrape UI
            inc, exc = self._view.get_filters()
            tree_exc = self._view.get_tree_filters()
            overrides = self._view.get_extension_overrides()
            use_git = self._view.get_use_gitignore_state()

            # Create Entry
            self._project_config.presets[name] = {
                "inclusive_filters": inc,
                "exclusive_filters": exc,
                "tree_exclusive_filters": tree_exc,
                "tree_use_gitignore": use_git,
                "extension_overrides": overrides
            }
            
            # Switch to new preset
            self._project_config.active_preset_name = name
            
            # Save
            self._config_manager.save_project(self._project_config)
            
            # Update UI (Re-populates combo and triggers selection logic)
            self._populate_presets_combo()
            self._view.statusBar().showMessage(f"Preset '{name}' created.", 3000)

    def _on_delete_preset_clicked(self):
        """Deletes the selected preset and reverts to Default."""
        current_preset = self._view.preset_combo.currentText()
        
        if current_preset == "Default":
            QMessageBox.warning(self._view, "Error", "Cannot delete the Default preset.")
            return

        confirm = QMessageBox.question(
            self._view, 
            "Confirm Delete", 
            f"Are you sure you want to delete preset '{current_preset}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            # Remove
            del self._project_config.presets[current_preset]
            
            # Revert to Default
            self._project_config.active_preset_name = "Default"
            
            # Save
            self._config_manager.save_project(self._project_config)
            
            # Update UI
            self._populate_presets_combo()
            self._view.statusBar().showMessage(f"Preset '{current_preset}' deleted.", 3000)

    # --- General Application Logic ---

    def _on_copy_prompt(self):
        """Copies the instruction prompt for the AI to the clipboard."""
        prompt_text = """I am using a "Sparse Context" tool to load only the specific files relevant to our current task. 
Please analyze the request and generate a JSON manifest object with the following schema:

```json
{
    "comment": "Brief description of the context load",
    "include": [
        "src/core",                 // Includes entire directory
        "src/main.py",              // Includes specific file
        "src/utils/**/*.json"       // Glob patterns are supported
    ],
    "exclude": [
        "src/core/legacy.py"        // Excludes specific files from the included set
    ],
    "filter_extensions": [".py", ".md"] // Optional: If provided, limits directory includes to these extensions
}
```

**Rules:**
1. Only include files strictly necessary for the current task to save context window space.
2. The `include` array is additive.
3. The `exclude` array subtracts from the included set.
4. Output ONLY the JSON object."""
        
        QApplication.clipboard().setText(prompt_text)
        self._view.statusBar().showMessage("AI Prompt copied to clipboard!", 3000)

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

    def _request_refresh(self):
        """Safely starts the refresh timer from the main GUI thread."""
        self._refresh_timer.start()

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
        # Note: We do NOT save to the preset dictionary here. We only save the 
        # "Active State" (root level config) for current session persistence.
        if not is_auto_refresh:
            # Global Settings (Consistent across presets)
            self._project_config.blacklisted_paths = self._view.get_blacklisted_paths()
            
            # Active Session Settings (May act as dirty state for the current preset)
            self._project_config.inclusive_filters, self._project_config.exclusive_filters = self._view.get_filters()
            self._project_config.extension_overrides = self._view.get_extension_overrides()
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

    def _on_tree_selection_changed(self):
        """Calculates size and count of selected items for sparse export."""
        selected_items = self._view.file_tree_widget.selectedItems()
        selected_file_paths = set()

        def _collect(item):
            item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item_type == "file":
                path = item.data(4, Qt.ItemDataRole.UserRole)
                if path:
                    size = item.data(1, Qt.ItemDataRole.UserRole) or 0
                    selected_file_paths.add((path, size))
            else:
                for i in range(item.childCount()):
                    _collect(item.child(i))

        for item in selected_items:
            _collect(item)
            
        total_size = sum(size for _, size in selected_file_paths)
        file_count = len(selected_file_paths)
            
        self._view.selection_stats_label.setText(f"Selected: {file_count} files ({self._view._format_size(total_size)})")
        self._view.export_selection_btn.setEnabled(file_count > 0)

    def _on_export_selection_clicked(self):
        """Gathers paths from manual tree selection and triggers sparse export."""
        selected_items = self._view.file_tree_widget.selectedItems()
        if not selected_items:
            return

        include_paths = []
        for item in selected_items:
            full_path = item.data(4, Qt.ItemDataRole.UserRole)
            item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if not full_path:
                continue
            
            relative_path = os.path.relpath(full_path, self._project_config.root_path).replace(os.sep, '/')
            
            if item_type == "directory":
                # Standard recursive glob pattern to include all files within the folder
                include_paths.append(f"{relative_path}/**/*")
                # Include the folder itself explicitly in case it's empty or needed for tree building
                include_paths.append(f"{relative_path}/")
            else:
                include_paths.append(relative_path)
            
        self._execute_sparse_export(include_paths, "Manual")

    def _on_clipboard_export(self):
        """Exports files based on a JSON manifest in the clipboard."""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        
        try:
            manifest = json.loads(text)
        except json.JSONDecodeError:
            QMessageBox.warning(self._view, "Invalid Manifest", "Clipboard does not contain valid JSON.")
            return

        if "include" not in manifest or not isinstance(manifest["include"], list):
             QMessageBox.warning(self._view, "Invalid Manifest", "JSON must contain an 'include' array.")
             return

        # Handle extensions formatting mapping for the unified sparse exporter
        man_inc = manifest.get("include", [])
        extensions = manifest.get("filter_extensions", [])
        final_inclusive = []
        
        if extensions:
            for path in man_inc:
                clean_path = os.path.normpath(path).replace(os.sep, '/')
                if os.path.splitext(clean_path)[1]: 
                    final_inclusive.append(clean_path)
                else:
                    for ext in extensions:
                        final_inclusive.append(f"{clean_path}/**/*{ext}")
        else:
            for path in man_inc:
                clean_path = os.path.normpath(path).replace(os.sep, '/')
                
                # Check if it was explicitly a folder OR if it lacks a file extension
                is_dir_like = path.endswith('/') or path.endswith('\\') or not os.path.splitext(clean_path)[1]
                
                if is_dir_like and not clean_path.endswith('*'):
                    # Include contents, the folder node, and the literal name (for extensionless files like "Makefile")
                    final_inclusive.append(f"{clean_path}/**/*")
                    final_inclusive.append(f"{clean_path}/")
                    final_inclusive.append(clean_path) 
                else:
                    final_inclusive.append(clean_path)

        # Extend temporary exclusive filters
        temp_exclusive = manifest.get("exclude", [])

        self._execute_sparse_export(
            include_paths=final_inclusive, 
            export_type="Manifest", 
            comment=manifest.get("comment", ""),
            temp_exclusive=temp_exclusive
        )

    def _execute_sparse_export(self, include_paths: list, export_type: str, comment: str = "", temp_exclusive: list = None):
        """Unified method for generating a sparse export from a list of paths."""
        if not include_paths:
            QMessageBox.warning(self._view, "Empty Selection", "No paths provided for export.")
            return

        if temp_exclusive is None:
            temp_exclusive = []

        final_exclusive = self._project_config.exclusive_filters + temp_exclusive


        # 1. Get Raw Tree (Fix: Capture gitignore_rules)
        try:
            raw_tree, gitignore_rules = FileScanner.scan_directory(
                self._project_config.root_path,
                self._project_config.blacklisted_paths
            )
        except ValueError as e:
            QMessageBox.critical(self._view, "Error Scanning", str(e))
            return

        # 2. Pass 1: Content Tree
        content_tree = FilterEngine.apply_filters(
            copy.deepcopy(raw_tree),
            self._project_config.root_path,
            include_paths,
            final_exclusive 
        )
        
        # Check if files were matched
        loaded_paths = set()
        def collect_paths(node):
            if node.get("status") == "included" and node["type"] == "file":
                loaded_paths.add(node["path"])
            for child in node.get("children", []):
                collect_paths(child)
        collect_paths(content_tree)

        if not loaded_paths:
            QMessageBox.warning(self._view, "Empty Export", "The selection/manifest matched 0 files.")
            return

        # 3. Pass 2: Atlas Tree (Fix: Conditionally include gitignore_rules)
        tree_exclude_filters = self._project_config.tree_exclusive_filters
        if self._project_config.tree_use_gitignore:
            tree_exclude_filters = tree_exclude_filters + gitignore_rules

        atlas_tree = FilterEngine.apply_filters(
            copy.deepcopy(raw_tree),
            self._project_config.root_path,
            [], 
            tree_exclude_filters # Use the updated variable here
        )
        
        # 4. Export
        try:
            temp_dir = ExportManager.export_files(
                content_tree,
                self._project_config.root_path,
                self._project_config.extension_overrides
            )
            ExportManager.export_markdown_tree(atlas_tree, temp_dir, loaded_paths)
            
            # Save History
            history_item = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": export_type,
                "file_count": len(loaded_paths),
                "paths": include_paths,
                "comment": comment,
                "temp_exclusive": temp_exclusive
            }
            active = self._project_config.active_preset_name
            if "export_history" not in self._project_config.presets[active]:
                self._project_config.presets[active]["export_history"] = []
                
            self._project_config.presets[active]["export_history"].insert(0, history_item)
            self._project_config.presets[active]["export_history"] = self._project_config.presets[active]["export_history"][:15]
            
            self._project_config.export_count += 1
            self._config_manager.save_project(self._project_config)
            self._refresh_history_ui()
            
            if sys.platform == "win32":
                os.startfile(temp_dir)
            elif sys.platform == "darwin": # macOS
                subprocess.run(["open", temp_dir], check=True)
            else: # Linux
                subprocess.run(["xdg-open", temp_dir], check=True)

        except Exception as e:
            QMessageBox.critical(self._view, "Export Error", f"An unexpected error occurred during export:\n{e}")

    def _refresh_history_ui(self):
        """Populates the history list with the active preset's context exports."""
        self._view.history_list_widget.clear()
        active = self._project_config.active_preset_name
        history = self._project_config.presets.get(active, {}).get("export_history", [])
        
        for item in history:
            try:
                # Parse the naive UTC time string
                dt_naive = datetime.fromisoformat(item["timestamp"])
                
                # Assign it the UTC time zone, then convert to local system time
                dt_utc = dt_naive.replace(tzinfo=timezone.utc)
                dt_local = dt_utc.astimezone()
                
                # Format to Year-Month-Day Hour:Minute AM/PM
                time_str = dt_local.strftime("%Y-%m-%d %I:%M %p")
            except ValueError:
                time_str = "Unknown"
                
            comment_str = f" - {item['comment']}" if item.get('comment') else ""
            display_text = f"[{time_str}] {item['type']} ({item['file_count']} files){comment_str}"
            
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self._view.history_list_widget.addItem(list_item)

    def _on_history_item_double_clicked(self, item):
        """Re-runs a historical export when double-clicked."""
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self._execute_sparse_export(
                include_paths=data.get("paths", []),
                export_type=data.get("type", "History"),
                comment=data.get("comment", ""),
                temp_exclusive=data.get("temp_exclusive", [])
            )

    def _on_history_item_selected(self):
        """Visualizes a history item's selection in the file tree."""
        selected_items = self._view.history_list_widget.selectedItems()
        if not selected_items:
            return
            
        # Get the history data
        data = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if not data:
            return
            
        include_paths = data.get("paths", [])
        
        # Block signals to prevent _on_tree_selection_changed from firing repeatedly
        self._view.file_tree_widget.blockSignals(True)
        self._view.file_tree_widget.clearSelection()
        
        iterator = QTreeWidgetItemIterator(self._view.file_tree_widget)
        while iterator.value():
            item = iterator.value()
            full_path = item.data(4, Qt.ItemDataRole.UserRole)
            item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            
            if full_path:
                rel_path = os.path.relpath(full_path, self._project_config.root_path).replace(os.sep, '/')
                if item_type == "directory":
                    rel_path += '/'
                    
                # Check for match against the history patterns
                is_match = False
                for pattern in include_paths:
                    # 1. Exact match
                    if rel_path == pattern:
                        is_match = True
                        break
                    
                    # 2. Handle the recursive directory pattern (e.g., src/core/**/*)
                    if pattern.endswith('**/*'):
                        base_dir = pattern[:-4] 
                        if rel_path.startswith(base_dir):
                            is_match = True
                            break
                            
                    # 3. Generic glob matching for manifest extensions (e.g., *.py)
                    if fnmatch.fnmatch(rel_path.rstrip('/'), pattern):
                        is_match = True
                        break
                        
                if is_match:
                    item.setSelected(True)
                    # Expand parent folders so the newly selected items are visible
                    parent = item.parent()
                    while parent:
                        parent.setExpanded(True)
                        parent = parent.parent()
                        
            iterator += 1
            
        self._view.file_tree_widget.blockSignals(False)
        
        # Trigger the stat calculation manually once the batch selection is finished
        self._on_tree_selection_changed()

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

    def _on_back(self):
        """Handles the 'Back to Projects' action."""
        self._view.close() # Triggers the closeEvent

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
        
        # We also ensure the active session state is saved, so next open matches this close
        self._project_config.tree_exclusive_filters = self._view.get_tree_filters()
        self._project_config.tree_use_gitignore = self._view.get_use_gitignore_state()
        self._project_config.inclusive_filters, self._project_config.exclusive_filters = self._view.get_filters()
        self._project_config.extension_overrides = self._view.get_extension_overrides()

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
        
        if not item.isSelected():
            tree.clearSelection()
            item.setSelected(True)

        item_path = item.data(4, Qt.ItemDataRole.UserRole)
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if not item_path:
            return

        menu = QMenu()
        
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

    def _on_context_exclude(self):
        """Adds paths of selected items to the appropriate exclusive filter list."""
        active_tab_index = self._view.main_tab_widget.currentIndex()
        if active_tab_index == 0:
            tree = self._view.file_tree_widget
            inclusive, exclusive = self._view.get_filters()
        else:
            tree = self._view.markdown_tree_widget
            inclusive = []
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
            inclusive = []
            exclusive = self._view.get_tree_filters()

        selected_items = tree.selectedItems()
        if not selected_items:
            return
            
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
                    pass
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
*   **Exclusive filters always take precedence.**
*   If **no inclusive filters** are provided, all files are included by default.
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

    def _start_file_watcher(self):
        """Initializes and starts the file system observer."""
        if self._observer:
            self._stop_file_watcher()

        handler = ProjectChangeHandler(self._watchdog_emitter)
        self._observer = Observer()
        self._observer.schedule(handler, self._project_config.root_path, recursive=True)
        try:
            self._observer.start()
        except Exception as e:
            print(f"Error starting file watcher: {e}")

    def _stop_file_watcher(self):
        """Stops and cleans up the file system observer."""
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join()
        self._observer = None