# src/ui/views/project_view_window.py
# Copyright (c) 2025 Google. All rights reserved.

from typing import Dict, Any, Tuple, List
import os
import qtawesome as qta 

from PyQt6.QtGui import QAction, QColor, QBrush, QPainter, QTextDocument, QIcon, QActionGroup
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QSplitter, QLabel,
    QFormLayout, QStyledItemDelegate, QTreeWidgetItemIterator, QAbstractItemView,
    QSizePolicy, QMenu, QToolButton, QTabWidget, QStackedWidget, QCheckBox,
    QComboBox, QListWidget
)
from PyQt6.QtCore import Qt, QRectF, QByteArray
from src.utils import resource_path

class NameDelegate(QStyledItemDelegate):
    """A delegate to render HTML in the 'Name' column of the QTreeWidget."""
    def paint(self, painter: QPainter, option, index):
        if index.column() == 0: # Name column
            painter.save()
            
            doc = QTextDocument()
            doc.setHtml(index.model().data(index))
            
            option.text = ""
            self.parent().style().drawControl(self.parent().style().ControlElement.CE_ItemViewItem, option, painter, self.parent())

            text_rect = QRectF(option.rect)
            text_rect.adjust(5, 0, 0, 0) 
            
            painter.translate(text_rect.topLeft())
            doc.drawContents(painter)
            
            painter.restore()
        else:
            super().paint(painter, option, index)

class PathDelegate(QStyledItemDelegate):
    """A delegate to render HTML in a specific column of the QTreeWidget."""
    def paint(self, painter: QPainter, option, index):
        if index.column() == 4: # Path column
            painter.save()
            doc = QTextDocument()
            doc.setHtml(index.model().data(index))
            option.text = "" 
            self.parent().style().drawControl(self.parent().style().ControlElement.CE_ItemViewItem, option, painter, self.parent())
            text_rect = QRectF(option.rect)
            text_rect.adjust(5, 0, 0, 0) 
            painter.translate(text_rect.topLeft())
            doc.drawContents(painter)
            painter.restore()
        else:
            super().paint(painter, option, index)

class ProjectViewWindow(QMainWindow):
    """Defines the UI for the main project workspace."""

    def __init__(self, project_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Project View - {project_name}")
        self.setMinimumSize(900, 700)
        self.setWindowIcon(QIcon(resource_path("assets/icon.ico")))

        # --- Toolbar ---
        toolbar = self.addToolBar("Main Toolbar")
        self.back_action = QAction("Back to Projects", self)
        self.export_button = QPushButton("Export Files...")
        self.export_button.setObjectName("exportButton")

        self.copy_prompt_button = QPushButton("📋 Copy AI Prompt")
        self.copy_prompt_button.setToolTip("Copy the system prompt to instruct AI on how to generate manifests")
        self.copy_prompt_button.setObjectName("copyPromptButton")

        self.open_root_action = QAction("Open Root Folder", self)
        self.open_export_action = QAction("Open Export Folder", self)
        
        self.toggle_path_action = QAction("Show Full Paths", self)
        self.toggle_path_action.setCheckable(True)

        self.hide_excluded_action = QAction("Hide Excluded Items", self)
        self.hide_excluded_action.setCheckable(True)

        self.help_action = QAction("Help", self)
        toolbar.addAction(self.back_action)
        toolbar.addSeparator()
        toolbar.addWidget(self.export_button)
        toolbar.addWidget(self.copy_prompt_button)
        toolbar.addAction(self.open_root_action)
        toolbar.addAction(self.open_export_action)
        toolbar.addSeparator()
        toolbar.addAction(self.toggle_path_action)
        toolbar.addAction(self.hide_excluded_action)
        toolbar.addSeparator()
        toolbar.addAction(self.help_action)
        toolbar.addSeparator()

        theme_menu = QMenu("Theme", self)
        self.dark_theme_action = QAction("Dark", self)
        self.light_theme_action = QAction("Light", self)
        self.auto_theme_action = QAction("Auto (System)", self)
        
        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.setExclusive(True)
        
        actions = [self.dark_theme_action, self.light_theme_action, self.auto_theme_action]
        for action in actions:
            action.setCheckable(True)
            self.theme_action_group.addAction(action)
            theme_menu.addAction(action)

        theme_button = QToolButton()
        theme_button.setObjectName("themeButton") 
        theme_button.setText("Theme")
        theme_button.setMenu(theme_menu)
        theme_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        theme_button.setStyleSheet("""
            QToolButton#themeButton { padding-right: 10px; }
            QToolButton#themeButton::menu-indicator { subcontrol-position: middle right; right: 5px; }
        """)

        toolbar.addWidget(theme_button)

        # --- Central Widget & Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- Splitter for two-pane layout ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        # --- Left Pane: Configuration ---
        config_panel = QWidget()
        config_layout = QVBoxLayout(config_panel)
        
        self.apply_filters_button = QPushButton("Apply Filters & Refresh Tree")
        self.apply_filters_button.setObjectName("applyButton")
        
        # --- PRESET TOOLBAR (NEW) ---
        preset_layout = QHBoxLayout()
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(5) # Add a little spacing between buttons
        
        preset_label = QLabel("Preset:")
        self.preset_combo = QComboBox()
        self.preset_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Define a consistent styling for the icons
        # "fa5s" = FontAwesome 5 Solid. "color='white'" ensures high contrast in dark mode.
        # You might want a slightly off-white (#eeeeee) for softer contrast.
        icon_color = "#eeeeee" 

        self.save_preset_btn = QToolButton()
        self.save_preset_btn.setIcon(qta.icon('fa5s.save', color=icon_color))
        self.save_preset_btn.setToolTip("Save changes to current preset")
        
        self.add_preset_btn = QToolButton()
        self.add_preset_btn.setIcon(qta.icon('fa5s.plus', color=icon_color))
        self.add_preset_btn.setToolTip("Add new preset from current settings")
        
        self.del_preset_btn = QToolButton()
        self.del_preset_btn.setIcon(qta.icon('fa5s.trash-alt', color=icon_color))
        self.del_preset_btn.setToolTip("Delete current preset")

        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(self.save_preset_btn)
        preset_layout.addWidget(self.add_preset_btn)
        preset_layout.addWidget(self.del_preset_btn)

        config_layout.addLayout(preset_layout)
        config_layout.addWidget(self.apply_filters_button)
        
        # Create stacked widget for config panels
        self.config_stack = QStackedWidget()

        # Page 1: File Export Configuration
        file_export_config_widget = QWidget()
        file_export_form_layout = QFormLayout(file_export_config_widget)
        self.blacklisted_paths_textbox = QTextEdit()
        self.inclusive_filters_textbox = QTextEdit()
        self.exclusive_filters_textbox = QTextEdit()
        self.extension_overrides_textbox = QTextEdit()
        
        for textbox in [self.blacklisted_paths_textbox, self.inclusive_filters_textbox, self.exclusive_filters_textbox, self.extension_overrides_textbox]:
            textbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        file_export_form_layout.addRow(QLabel("Blacklisted Directory Names:"), self.blacklisted_paths_textbox)
        file_export_form_layout.addRow(QLabel("Inclusive Filters:"), self.inclusive_filters_textbox)
        file_export_form_layout.addRow(QLabel("Exclusive Filters:"), self.exclusive_filters_textbox)
        file_export_form_layout.addRow(QLabel("Extension Overrides:"), self.extension_overrides_textbox)

        self.selection_stats_label = QLabel("Selected: 0 files (0 B)")
        self.export_selection_btn = QPushButton("Export Selection")
        self.export_selection_btn.setEnabled(False)
        self.export_selection_btn.setObjectName("exportSelectionButton")
        
        self.clipboard_export_button = QPushButton("📄 Export from Manifest")
        self.clipboard_export_button.setToolTip("Export files based on a JSON manifest in your clipboard")
        self.clipboard_export_button.setObjectName("clipboardExportButton")
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.export_selection_btn)
        btn_layout.addWidget(self.clipboard_export_button)
        
        self.history_list_widget = QListWidget()
        self.history_list_widget.setMinimumHeight(100)
        
        file_export_form_layout.addRow(self.selection_stats_label)
        file_export_form_layout.addRow(btn_layout)
        file_export_form_layout.addRow(QLabel("Recent Context Exports:"), self.history_list_widget)
        
        # Page 2: Tree Markdown Export Configuration
        tree_export_config_widget = QWidget()
        tree_export_form_layout = QFormLayout(tree_export_config_widget)
        self.tree_exclusive_filters_textbox = QTextEdit()
        self.tree_exclusive_filters_textbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.use_gitignore_checkbox = QCheckBox("Apply .gitignore Rules")
        
        tree_export_form_layout.addRow(self.use_gitignore_checkbox)
        tree_export_form_layout.addRow(QLabel("Tree Exclusive Filters (one per line):"), self.tree_exclusive_filters_textbox)

        # Add pages to stack and then stack to layout
        self.config_stack.addWidget(file_export_config_widget)
        self.config_stack.addWidget(tree_export_config_widget)
        config_layout.addWidget(self.config_stack)

        # --- Right Pane: Tabbed Tree Views ---
        self.main_tab_widget = QTabWidget()

        # Tab 1: File Tree
        self.file_tree_widget = QTreeWidget()
        self.file_tree_widget.setHeaderLabels(["Name", "Size", "Override", "Status", "Path"])
        self.file_tree_widget.setColumnWidth(0, 300)
        self.file_tree_widget.setColumnWidth(1, 100)
        self.file_tree_widget.setColumnWidth(2, 100)
        self.file_tree_widget.setColumnWidth(3, 80)
        self.file_tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_tree_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_tree_widget.setStyleSheet("QTreeWidget::item { border-bottom: 1px solid #4a4a4a; }")
        
        # Apply the custom delegates
        self.file_tree_widget.setItemDelegateForColumn(0, NameDelegate(self.file_tree_widget))
        self.file_tree_widget.setItemDelegateForColumn(4, PathDelegate(self.file_tree_widget))
        
        # Tab 2: Markdown Tree
        self.markdown_tree_widget = QTreeWidget()
        self.markdown_tree_widget.setHeaderHidden(True)
        self.markdown_tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.markdown_tree_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # Add widgets to tabs
        self.main_tab_widget.addTab(self.file_tree_widget, "File Export")
        self.main_tab_widget.addTab(self.markdown_tree_widget, "Tree Markdown Export")

        # Add panes to splitter
        self.splitter.addWidget(config_panel)
        self.splitter.addWidget(self.main_tab_widget)
        self.splitter.setSizes([350, 550])

        # Colors for styling
        self.path_slash_color = "#808080"
        self.path_ext_color = "#FFC66D"

        # --- Status Bar ---
        self.statusBar()
        self.included_label = QLabel("Included: 0")
        self.excluded_label = QLabel("Excluded: 0")
        self.size_label = QLabel("Total Size: 0 B")
        self.statusBar().addPermanentWidget(self.included_label)
        self.statusBar().addPermanentWidget(self.excluded_label)
        self.statusBar().addPermanentWidget(self.size_label)

    def get_filters(self) -> Tuple[List[str], List[str]]:
        """Returns the current text from the filter textboxes as lists of strings."""
        inclusive = self.inclusive_filters_textbox.toPlainText().splitlines()
        exclusive = self.exclusive_filters_textbox.toPlainText().splitlines()
        inclusive = [line.strip() for line in inclusive if line.strip()]
        exclusive = [line.strip() for line in exclusive if line.strip()]
        return inclusive, exclusive

    def set_filters_text(self, inclusive: list[str], exclusive: list[str]):
        """Sets the text in the filter boxes."""
        self.inclusive_filters_textbox.setPlainText("\n".join(inclusive))
        self.exclusive_filters_textbox.setPlainText("\n".join(exclusive))

    def get_tree_filters(self) -> List[str]:
        """Returns the current text from the tree exclusive filter textbox."""
        exclusive = self.tree_exclusive_filters_textbox.toPlainText().splitlines()
        return [line.strip() for line in exclusive if line.strip()]

    def set_tree_filters_text(self, exclusive: list[str]):
        """Sets the text in the tree exclusive filter box."""
        self.tree_exclusive_filters_textbox.setPlainText("\n".join(exclusive))

    def get_use_gitignore_state(self) -> bool:
        """Returns the checked state of the .gitignore checkbox."""
        return self.use_gitignore_checkbox.isChecked()

    def set_use_gitignore_state(self, state: bool):
        """Sets the checked state of the .gitignore checkbox."""
        self.use_gitignore_checkbox.setChecked(state)

    def get_blacklisted_paths(self) -> List[str]:
        """Returns the current text from the blacklist textbox as a list of strings."""
        paths = self.blacklisted_paths_textbox.toPlainText().splitlines()
        return [line.strip() for line in paths if line.strip()]

    def set_blacklisted_paths_text(self, paths: list[str]):
        """Sets the text in the blacklist box."""
        self.blacklisted_paths_textbox.setPlainText("\n".join(paths))

    def get_extension_overrides(self) -> Dict[str, str]:
        """Parses the extension overrides textbox and returns a dictionary."""
        overrides = {}
        lines = self.extension_overrides_textbox.toPlainText().splitlines()
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                source_ext = parts[0].strip().lower()
                target_ext = parts[1].strip().lower()
                if source_ext and target_ext:
                    overrides[source_ext] = target_ext
        return overrides

    def set_extension_overrides_text(self, overrides: Dict[str, str]):
        """Sets the text in the extension overrides box from a dictionary."""
        lines = [f"{source}:{target}" for source, target in overrides.items()]
        self.extension_overrides_textbox.setPlainText("\n".join(lines))

    # --- New Helper for Batch Updating UI ---
    def set_all_filter_ui_state(self, 
                                inclusive: list[str], 
                                exclusive: list[str], 
                                tree_exclusive: list[str], 
                                overrides: dict[str, str], 
                                use_gitignore: bool):
        """Updates all filter input fields at once."""
        self.set_filters_text(inclusive, exclusive)
        self.set_tree_filters_text(tree_exclusive)
        self.set_extension_overrides_text(overrides)
        self.set_use_gitignore_state(use_gitignore)

    def _format_size(self, size_bytes: int) -> str:
        """Formats a size in bytes to a human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes / 1024**2:.2f} MB"
        else:
            return f"{size_bytes / 1024**3:.2f} GB"

    def populate_file_tree(self, filtered_tree: Dict[str, Any], overrides: Dict[str, str], root_path: str, show_full_path: bool, hide_excluded: bool):
        """Clears and rebuilds the file tree widget based on filtered data."""
        self.file_tree_widget.clear()
        if not filtered_tree:
            return
        
        self.file_tree_widget.setColumnHidden(3, hide_excluded)
        self._add_tree_item(None, filtered_tree, overrides, root_path, show_full_path, hide_excluded)
        self.file_tree_widget.expandToDepth(0)

    def _add_tree_item(self, parent_item: QTreeWidgetItem | None, node: Dict[str, Any], overrides: Dict[str, str], root_path: str, show_full_path: bool, hide_excluded: bool):
        """Recursively adds an item to the tree widget."""
        if hide_excluded and node.get("status") == "excluded":
            return

        if parent_item is None:
            tree_item = QTreeWidgetItem(self.file_tree_widget)
        else:
            tree_item = QTreeWidgetItem(parent_item)
            
        tree_item.setText(3, node.get("status", "unknown"))

        tree_item.setData(0, Qt.ItemDataRole.UserRole + 1, node["type"])
        tree_item.setData(4, Qt.ItemDataRole.UserRole, node["path"])

        size_bytes = node.get("size", 0)
        tree_item.setData(1, Qt.ItemDataRole.UserRole, size_bytes)

        size_str = self._format_size(size_bytes)
        tree_item.setText(1, size_str)
        tree_item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight)

        if show_full_path:
            path_to_display = node["path"]
        else:
            path_to_display = os.path.relpath(node["path"], root_path)
            if path_to_display == ".":
                path_to_display = node["name"]

        html_path = ""
        if node["type"] == "file":
            path_dir, file_name = os.path.split(path_to_display)
            name, ext = os.path.splitext(file_name)
            
            colored_dir = path_dir.replace(os.sep, f"<font color='{self.path_slash_color}'>{os.sep}</font>")
            
            html_path += f"{colored_dir}"
            if path_dir:
                html_path += f"<font color='{self.path_slash_color}'>{os.sep}</font>"
            html_path += f"{name}"
            
            if ext:
                html_path += f"<font color='{self.path_ext_color}'>{ext}</font>"
        else:
            colored_path = path_to_display.replace(os.sep, f"<font color='{self.path_slash_color}'>{os.sep}</font>")
            html_path = f"{colored_path}"
        
        tree_item.setText(4, html_path)

        if node["type"] == "file":
            name, ext = os.path.splitext(node["name"])
            html_name = f"{name}<font color='{self.path_ext_color}'>{ext}</font>"
            tree_item.setText(0, html_name)
        else: 
            tree_item.setText(0, node['name'])

        if node.get("status") == "excluded":
            tree_item.setDisabled(True)
        
        if node["type"] == "file":
            _name_root, original_ext = os.path.splitext(node["name"])
            clean_ext = original_ext.lstrip('.').lower()
            if clean_ext in overrides:
                target_ext = overrides[clean_ext]
                tree_item.setText(2, f"{original_ext} -> .{target_ext}")
        
        for child_node in node.get("children", []):
            self._add_tree_item(tree_item, child_node, overrides, root_path, show_full_path, hide_excluded)

    def populate_markdown_tree(self, filtered_tree: Dict[str, Any], hide_excluded: bool):
        """Clears and rebuilds the markdown tree widget."""
        self.markdown_tree_widget.clear()
        if not filtered_tree:
            return
        self._add_markdown_tree_item(None, filtered_tree, hide_excluded)
        self.markdown_tree_widget.expandToDepth(0)

    def _add_markdown_tree_item(self, parent_item: QTreeWidgetItem | None, node: Dict[str, Any], hide_excluded: bool):
        """Recursively adds an item to the markdown tree widget."""
        if hide_excluded and node.get("status") == "excluded":
            return

        if parent_item is None:
            tree_item = QTreeWidgetItem(self.markdown_tree_widget)
        else:
            tree_item = QTreeWidgetItem(parent_item)

        tree_item.setText(0, node["name"])
        tree_item.setData(0, Qt.ItemDataRole.UserRole + 1, node["type"])
        tree_item.setData(4, Qt.ItemDataRole.UserRole, node["path"])

        if node.get("status") == "excluded":
            tree_item.setDisabled(True)

        sorted_children = sorted(
            node.get("children", []),
            key=lambda x: (x["type"] != "directory", x["name"].lower())
        )
        for child_node in sorted_children:
            self._add_markdown_tree_item(tree_item, child_node, hide_excluded)
    
    def get_expanded_item_paths(self) -> set[str]:
        """Returns a set of raw paths for all currently expanded items in the file tree."""
        expanded_paths = set()
        iterator = QTreeWidgetItemIterator(self.file_tree_widget)
        while iterator.value():
            item = iterator.value()
            if item.isExpanded():
                path = item.data(4, Qt.ItemDataRole.UserRole)
                if path:
                    expanded_paths.add(path)
            iterator += 1
        return expanded_paths

    def apply_expanded_state(self, expanded_paths: set[str]):
        """Expands all file tree items whose raw paths are in the provided set."""
        iterator = QTreeWidgetItemIterator(self.file_tree_widget)
        while iterator.value():
            item = iterator.value()
            raw_path = item.data(4, Qt.ItemDataRole.UserRole)
            if raw_path in expanded_paths:
                item.setExpanded(True)
            iterator += 1

    def get_markdown_expanded_item_paths(self) -> set[str]:
        """Returns a set of raw paths for all currently expanded items in the markdown tree."""
        expanded_paths = set()
        iterator = QTreeWidgetItemIterator(self.markdown_tree_widget)
        while iterator.value():
            item = iterator.value()
            if item.isExpanded():
                path = item.data(4, Qt.ItemDataRole.UserRole)
                if path:
                    expanded_paths.add(path)
            iterator += 1
        return expanded_paths

    def apply_markdown_expanded_state(self, expanded_paths: set[str]):
        """Expands all markdown tree items whose raw paths are in the provided set."""
        iterator = QTreeWidgetItemIterator(self.markdown_tree_widget)
        while iterator.value():
            item = iterator.value()
            raw_path = item.data(4, Qt.ItemDataRole.UserRole)
            if raw_path in expanded_paths:
                item.setExpanded(True)
            iterator += 1
    
    def update_status_bar(self, included_count: int, excluded_count: int, total_size_bytes: int):
        """Updates the labels in the status bar with the latest file stats."""
        green_value_color = "#98fb98"
        self.included_label.setText(f"Included: <font color='{green_value_color}'>{included_count}</font>")
        self.excluded_label.setText(f"Excluded: <font color='{green_value_color}'>{excluded_count}</font>")
        
        size_str = self._format_size(total_size_bytes)
        
        self.size_label.setText(f"Total Size: <font color='{green_value_color}'>{size_str}</font>")
    
    def get_ui_state(self) -> Dict[str, Any]:
        """Gathers the current UI state into a dictionary for serialization."""
        return {
            "window_geometry": self.saveGeometry().toHex().data().decode('ascii'),
            "splitter_sizes": self.splitter.sizes(),
            "tree_header_state": self.file_tree_widget.header().saveState().toHex().data().decode('ascii'),
            "expanded_paths": sorted(list(self.get_expanded_item_paths()))
        }

    def apply_ui_state(self, state: Dict[str, Any]):
        """Applies a saved UI state dictionary to the window and its widgets."""
        if state:
            geometry = state.get("window_geometry")
            if geometry:
                self.restoreGeometry(QByteArray.fromHex(geometry.encode('ascii')))
            
            splitter_sizes = state.get("splitter_sizes")
            if splitter_sizes and len(splitter_sizes) == 2:
                self.splitter.setSizes(splitter_sizes)

            header_state = state.get("tree_header_state")
            if header_state:
                self.file_tree_widget.header().restoreState(QByteArray.fromHex(header_state.encode('ascii')))