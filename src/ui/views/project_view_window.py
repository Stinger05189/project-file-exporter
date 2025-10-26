# src/ui/views/project_view_window.py
# Copyright (c) 2025 Google. All rights reserved.

from typing import Dict, Any, Tuple, List

from PyQt6.QtGui import QAction, QColor, QBrush
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QSplitter, QLabel,
    QFormLayout
)
from PyQt6.QtCore import Qt

class ProjectViewWindow(QMainWindow):
    """Defines the UI for the main project workspace."""

    def __init__(self, project_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Project View - {project_name}")
        self.setMinimumSize(800, 600)

        # --- Toolbar ---
        toolbar = self.addToolBar("Main Toolbar")
        self.back_action = QAction("Back to Projects", self)
        self.export_action = QAction("Export Files...", self)
        toolbar.addAction(self.back_action)
        toolbar.addAction(self.export_action)

        # --- Central Widget & Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- Splitter for two-pane layout ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # --- Left Pane: Configuration ---
        config_panel = QWidget()
        config_layout = QVBoxLayout(config_panel)
        
        form_layout = QFormLayout()
        self.inclusive_filters_textbox = QTextEdit()
        self.exclusive_filters_textbox = QTextEdit()
        form_layout.addRow(QLabel("Inclusive Filters (one per line):"), self.inclusive_filters_textbox)
        form_layout.addRow(QLabel("Exclusive Filters (one per line):"), self.exclusive_filters_textbox)
        
        self.apply_filters_button = QPushButton("Apply Filters & Refresh Tree")
        
        config_layout.addLayout(form_layout)
        config_layout.addWidget(self.apply_filters_button)
        config_layout.addStretch()

        # --- Right Pane: File Tree Visualization ---
        self.file_tree_widget = QTreeWidget()
        self.file_tree_widget.setHeaderLabels(["Name", "Status", "Path"])
        self.file_tree_widget.setColumnWidth(0, 250)
        self.file_tree_widget.setColumnWidth(1, 80)

        # Add panes to splitter
        splitter.addWidget(config_panel)
        splitter.addWidget(self.file_tree_widget)
        splitter.setSizes([250, 550])

        # Colors for excluded items
        self.excluded_brush = QBrush(QColor("gray"))

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

    def populate_file_tree(self, filtered_tree: Dict[str, Any]):
        """Clears and rebuilds the file tree widget based on filtered data."""
        self.file_tree_widget.clear()
        if not filtered_tree:
            return
        
        self._add_tree_item(None, filtered_tree)
        self.file_tree_widget.expandToDepth(0)

    def _add_tree_item(self, parent_item: QTreeWidgetItem | None, node: Dict[str, Any]):
        """Recursively adds an item to the tree widget."""
        if parent_item is None:
            tree_item = QTreeWidgetItem(self.file_tree_widget)
        else:
            tree_item = QTreeWidgetItem(parent_item)
            
        tree_item.setText(0, node["name"])
        tree_item.setText(1, node.get("status", "unknown"))
        tree_item.setText(2, node["path"])

        if node.get("status") == "excluded":
            for i in range(tree_item.columnCount()):
                tree_item.setForeground(i, self.excluded_brush)
        
        for child_node in node.get("children", []):
            self._add_tree_item(tree_item, child_node)