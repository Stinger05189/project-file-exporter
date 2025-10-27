# src/ui/views/project_edit_dialog.py
# Copyright (c) 2025 Google. All rights reserved.

"""
A dialog for creating a new project or editing an existing one's name.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QPushButton, QFormLayout,
    QDialogButtonBox, QFileDialog, QHBoxLayout
)

class ProjectEditDialog(QDialog):
    """A dialog to get project details from the user."""

    def __init__(self, parent=None, current_name="", current_path=""):
        super().__init__(parent)
        self.is_new_project = not bool(current_name)
        
        if self.is_new_project:
            self.setWindowTitle("Create New Project")
        else:
            self.setWindowTitle(f"Edit Project '{current_name}'")

        self.setMinimumWidth(400)

        # Widgets
        self.name_textbox = QLineEdit(current_name)
        self.path_textbox = QLineEdit(current_path)
        self.browse_button = QPushButton("Browse...")

        # Layout for path selection
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_textbox)
        path_layout.addWidget(self.browse_button)

        # Main layout
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.addRow("Project Name:", self.name_textbox)
        form_layout.addRow("Root Path:", path_layout)
        main_layout.addLayout(form_layout)

        # Dialog Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        main_layout.addWidget(self.button_box)

        # Configure widgets based on mode (new vs. edit)
        if not self.is_new_project:
            self.path_textbox.setReadOnly(True)
            self.browse_button.setEnabled(False)

        # Signals
        self.browse_button.clicked.connect(self._on_browse)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def _on_browse(self):
        """Opens a directory dialog to select the project's root path."""
        directory = QFileDialog.getExistingDirectory(self, "Select Project Root Directory")
        if directory:
            self.path_textbox.setText(directory)

    def get_details(self) -> tuple[str, str] | None:
        """Returns the project details if accepted."""
        if self.exec() == QDialog.DialogCode.Accepted:
            return self.name_textbox.text().strip(), self.path_textbox.text().strip()
        return None