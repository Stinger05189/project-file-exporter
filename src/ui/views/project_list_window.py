# src/ui/views/project_list_window.py
# Copyright (c) 2025 Google. All rights reserved.

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QListWidget,
    QHBoxLayout, QPushButton, QListWidgetItem
)

class ProjectListWindow(QMainWindow):
    """Defines the UI for the main project management screen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Project-Based File Exporter - Select a Project")
        self.setMinimumSize(400, 300)

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # UI Components
        self.project_list_widget = QListWidget()
        self.project_list_widget.setAlternatingRowColors(True)

        self.add_project_button = QPushButton("Add Project")
        self.remove_project_button = QPushButton("Remove Project")
        self.open_project_button = QPushButton("Open Project")
        self.open_project_button.setEnabled(False) # Disabled until a project is selected

        # Layout for buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_project_button)
        button_layout.addWidget(self.remove_project_button)
        button_layout.addStretch()
        button_layout.addWidget(self.open_project_button)

        # Add widgets to the main layout
        main_layout.addWidget(self.project_list_widget)
        main_layout.addLayout(button_layout)

        # Connect internal signals
        self.project_list_widget.currentItemChanged.connect(self._on_selection_changed)
        self.project_list_widget.itemDoubleClicked.connect(lambda: self.open_project_button.click())

    def _on_selection_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        """Enables or disables buttons based on item selection."""
        self.open_project_button.setEnabled(current is not None)
        self.remove_project_button.setEnabled(current is not None)

    def populate_project_list(self, project_names: list[str]):
        """Clears and fills the project list widget."""
        self.project_list_widget.clear()
        self.project_list_widget.addItems(project_names)
        self._on_selection_changed(None, None) # Reset button state

    def get_selected_project_name(self) -> str | None:
        """Returns the name of the currently selected project."""
        selected_item = self.project_list_widget.currentItem()
        return selected_item.text() if selected_item else None