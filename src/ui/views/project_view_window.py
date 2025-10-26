# src/ui/views/project_view_window.py
# Copyright (c) 2025 Google. All rights reserved.

from typing import Dict, Any, Tuple, List
import os

from PyQt6.QtGui import QAction, QColor, QBrush, QPainter, QTextDocument, QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QSplitter, QLabel,
    QFormLayout, QStyledItemDelegate, QTreeWidgetItemIterator, QAbstractItemView
)
from PyQt6.QtCore import Qt, QRectF, QByteArray
from src.utils import resource_path

class PathDelegate(QStyledItemDelegate):
    """A delegate to render HTML in a specific column of the QTreeWidget."""
    def paint(self, painter: QPainter, option, index):
        if index.column() == 3: # Path column
            # To render rich text, we must handle the painting ourselves
            painter.save()
            
            doc = QTextDocument()
            doc.setHtml(index.model().data(index))
            
            # Ensure the document fits within the option rectangle
            option.text = "" # We draw the text ourselves
            self.parent().style().drawControl(self.parent().style().ControlElement.CE_ItemViewItem, option, painter, self.parent())

            # Adjust for padding and alignment
            text_rect = QRectF(option.rect)
            text_rect.adjust(5, 0, 0, 0) 
            
            painter.translate(text_rect.topLeft())
            doc.drawContents(painter)
            
            painter.restore()
        else:
            # For all other columns, use the default painter
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
        self.export_action = QAction("Export Files...", self)
        self.toggle_path_action = QAction("Show Full Paths", self)
        self.toggle_path_action.setCheckable(True)
        self.help_action = QAction("Help", self)
        toolbar.addAction(self.back_action)
        toolbar.addAction(self.export_action)
        toolbar.addAction(self.toggle_path_action)
        toolbar.addAction(self.help_action)

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
        
        form_layout = QFormLayout()
        
        self.blacklisted_paths_textbox = QTextEdit()
        form_layout.addRow(QLabel("Blacklisted Directory Names (one per line):"), self.blacklisted_paths_textbox)

        self.inclusive_filters_textbox = QTextEdit()
        self.exclusive_filters_textbox = QTextEdit()
        form_layout.addRow(QLabel("Inclusive Filters (one per line):"), self.inclusive_filters_textbox)
        form_layout.addRow(QLabel("Exclusive Filters (one per line):"), self.exclusive_filters_textbox)
        
        self.extension_overrides_textbox = QTextEdit()
        form_layout.addRow(QLabel("Extension Overrides (e.g., svg:xml):"), self.extension_overrides_textbox)

        self.apply_filters_button = QPushButton("Apply Filters & Refresh Tree")
        
        config_layout.addLayout(form_layout)
        config_layout.addWidget(self.apply_filters_button)
        config_layout.addStretch()

        # --- Right Pane: File Tree Visualization ---
        self.file_tree_widget = QTreeWidget()
        self.file_tree_widget.setHeaderLabels(["Name", "Override", "Status", "Path"])
        self.file_tree_widget.setColumnWidth(0, 280)
        self.file_tree_widget.setColumnWidth(1, 100)
        self.file_tree_widget.setColumnWidth(2, 80)
        self.file_tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        # Allow multiple items to be selected with Shift/Ctrl modifiers
        self.file_tree_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        # Apply the custom delegate to the Path column (index 3)
        self.file_tree_widget.setItemDelegateForColumn(3, PathDelegate(self.file_tree_widget))

        # Add panes to splitter
        self.splitter.addWidget(config_panel)
        self.splitter.addWidget(self.file_tree_widget)
        self.splitter.setSizes([300, 600])

        # Colors for styling
        self.excluded_brush = QBrush(QColor("#888888"))
        self.override_brush = QBrush(QColor("#00FFFF"))
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
        # Filter out empty lines
        inclusive = [line.strip() for line in inclusive if line.strip()]
        exclusive = [line.strip() for line in exclusive if line.strip()]
        return inclusive, exclusive

    def set_filters_text(self, inclusive: list[str], exclusive: list[str]):
        """Sets the text in the filter boxes."""
        self.inclusive_filters_textbox.setPlainText("\n".join(inclusive))
        self.exclusive_filters_textbox.setPlainText("\n".join(exclusive))

    def get_blacklisted_paths(self) -> List[str]:
        """Returns the current text from the blacklist textbox as a list of strings."""
        paths = self.blacklisted_paths_textbox.toPlainText().splitlines()
        # Filter out empty lines
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
        
    def populate_file_tree(self, filtered_tree: Dict[str, Any], overrides: Dict[str, str], root_path: str, show_full_path: bool):
        """Clears and rebuilds the file tree widget based on filtered data."""
        self.file_tree_widget.clear()
        if not filtered_tree:
            return
        
        self._add_tree_item(None, filtered_tree, overrides, root_path, show_full_path)
        self.file_tree_widget.expandToDepth(0)

    def _add_tree_item(self, parent_item: QTreeWidgetItem | None, node: Dict[str, Any], overrides: Dict[str, str], root_path: str, show_full_path: bool):
        """Recursively adds an item to the tree widget."""
        if parent_item is None:
            tree_item = QTreeWidgetItem(self.file_tree_widget)
        else:
            tree_item = QTreeWidgetItem(parent_item)
            
        tree_item.setText(0, node["name"])
        tree_item.setText(2, node.get("status", "unknown"))

        # Store extra data for context menu and path toggling
        tree_item.setData(0, Qt.ItemDataRole.UserRole + 1, node["type"]) # Store node type
        tree_item.setData(3, Qt.ItemDataRole.UserRole, node["path"]) # Store raw full path

        # Determine which path to display (full or relative)
        if show_full_path:
            path_to_display = node["path"]
        else:
            path_to_display = os.path.relpath(node["path"], root_path)
            if path_to_display == ".":
                path_to_display = node["name"] # Show root folder name instead of '.'

        base_color = self.palette().color(self.palette().ColorRole.Text).name()
        html_path = ""

        # Generate HTML for styled path
        if node["type"] == "file":
            path_dir, file_name = os.path.split(path_to_display)
            name, ext = os.path.splitext(file_name)
            
            colored_dir = path_dir.replace(os.sep, f"<font color='{self.path_slash_color}'>{os.sep}</font>")
            
            html_path += f"<font color='{base_color}'>{colored_dir}"
            if path_dir:
                html_path += f"<font color='{self.path_slash_color}'>{os.sep}</font>"
            html_path += f"{name}</font>"
            
            if ext:
                html_path += f"<font color='{self.path_ext_color}'>{ext}</font>"
        else: # It's a directory
            # For directories, only color the slashes
            colored_path = path_to_display.replace(os.sep, f"<font color='{self.path_slash_color}'>{os.sep}</font>")
            html_path = f"<font color='{base_color}'>{colored_path}</font>"
        
        tree_item.setText(3, html_path)

        if node.get("status") == "excluded":
            for i in range(tree_item.columnCount()):
                tree_item.setForeground(i, self.excluded_brush)
        
        # Handle Extension Overrides in the "Override" column
        if node["type"] == "file":
            _name_root, original_ext = os.path.splitext(node["name"])
            clean_ext = original_ext.lstrip('.').lower()
            if clean_ext in overrides:
                target_ext = overrides[clean_ext]
                tree_item.setText(1, f"{original_ext} -> .{target_ext}")
                tree_item.setForeground(1, self.override_brush)
        
        for child_node in node.get("children", []):
            # The parent of the next node is the item we just created.
            self._add_tree_item(tree_item, child_node, overrides, root_path, show_full_path)

    def get_expanded_item_paths(self) -> set[str]:
        """Returns a set of raw paths for all currently expanded items in the tree."""
        expanded_paths = set()
        iterator = QTreeWidgetItemIterator(self.file_tree_widget)
        while iterator.value():
            item = iterator.value()
            if item.isExpanded():
                path = item.data(3, Qt.ItemDataRole.UserRole)
                if path:
                    expanded_paths.add(path)
            iterator += 1
        return expanded_paths

    def apply_expanded_state(self, expanded_paths: set[str]):
        """Expands all tree items whose raw paths are in the provided set."""
        iterator = QTreeWidgetItemIterator(self.file_tree_widget)
        while iterator.value():
            item = iterator.value()
            raw_path = item.data(3, Qt.ItemDataRole.UserRole)
            if raw_path in expanded_paths:
                item.setExpanded(True)
            iterator += 1

    def update_status_bar(self, included_count: int, excluded_count: int, total_size_bytes: int):
        """Updates the labels in the status bar with the latest file stats."""
        self.included_label.setText(f"Included: {included_count}")
        self.excluded_label.setText(f"Excluded: {excluded_count}")
        
        if total_size_bytes < 1024:
            size_str = f"{total_size_bytes} B"
        elif total_size_bytes < 1024**2:
            size_str = f"{total_size_bytes / 1024:.2f} KB"
        elif total_size_bytes < 1024**3:
            size_str = f"{total_size_bytes / 1024**2:.2f} MB"
        else:
            size_str = f"{total_size_bytes / 1024**3:.2f} GB"
        
        self.size_label.setText(f"Total Size: {size_str}")

    def get_ui_state(self) -> Dict[str, Any]:
        """Gathers the current UI state into a dictionary for serialization."""
        return {
            "window_geometry": self.saveGeometry().toHex().data().decode('ascii'),
            "splitter_sizes": self.splitter.sizes(),
            "tree_header_state": self.file_tree_widget.header().saveState().toHex().data().decode('ascii'),
            "expanded_paths": sorted(list(self.get_expanded_item_paths())) # sort for consistent serialization
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