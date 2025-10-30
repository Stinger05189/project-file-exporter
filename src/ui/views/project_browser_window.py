# src/ui/views/project_browser_window.py
# Copyright (c) 2025 Google. All rights reserved.

"""
A window for browsing, managing, and opening all available projects.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTreeWidget,
    QHBoxLayout, QPushButton, QAbstractItemView
)
from PyQt6.QtGui import QIcon, QAction
from src.utils import resource_path

class ProjectBrowserWindow(QMainWindow):
    """Defines the UI for the project browser screen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Project Browser")
        self.setMinimumSize(800, 500)
        self.setWindowIcon(QIcon(resource_path("assets/icon.ico")))

        # --- Toolbar ---
        toolbar = self.addToolBar("Main Toolbar")
        self.back_action = QAction("Back to Landing", self)
        toolbar.addAction(self.back_action)

        # --- Central Widget ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- UI Components ---
        self.project_tree_widget = QTreeWidget()
        self.project_tree_widget.setHeaderLabels([
            "Project Name", "Last Opened", "Exports", "Files", "Root Path"
        ])
        self.project_tree_widget.setAlternatingRowColors(True)
        self.project_tree_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.project_tree_widget.setSortingEnabled(True)

        self.project_tree_widget.header().setStretchLastSection(False)
        self.project_tree_widget.setColumnWidth(0, 200)
        self.project_tree_widget.setColumnWidth(1, 150)
        self.project_tree_widget.setColumnWidth(2, 60)
        self.project_tree_widget.setColumnWidth(3, 60)
        self.project_tree_widget.setColumnWidth(4, 300)

        self.create_project_button = QPushButton("Create Project")
        self.remove_project_button = QPushButton("Remove Project(s)")
        self.edit_project_button = QPushButton("Edit Project")
        self.duplicate_project_button = QPushButton("Duplicate Project")
        self.open_project_button = QPushButton("Open Project")

        # --- Layouts ---
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.create_project_button)
        button_layout.addWidget(self.remove_project_button)
        button_layout.addWidget(self.edit_project_button)
        button_layout.addWidget(self.duplicate_project_button)
        button_layout.addStretch()
        button_layout.addWidget(self.open_project_button)

        main_layout.addWidget(self.project_tree_widget)
        main_layout.addLayout(button_layout)

        # --- Internal Signals ---
        self.project_tree_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.project_tree_widget.itemDoubleClicked.connect(lambda: self.open_project_button.click())
        
        # Initial button state
        self._on_selection_changed()

    def _on_selection_changed(self):
        """Enables/disables buttons based on item selection."""
        selected_count = len(self.project_tree_widget.selectedItems())
        self.open_project_button.setEnabled(selected_count == 1)
        self.edit_project_button.setEnabled(selected_count == 1)
        self.duplicate_project_button.setEnabled(selected_count == 1)
        self.remove_project_button.setEnabled(selected_count > 0)