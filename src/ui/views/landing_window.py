# src/ui/views/landing_window.py
# Copyright (c) 2025 Google. All rights reserved.

"""
The main landing window for the application, showing recent projects and main actions.
"""

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt
from src.utils import resource_path

class LandingWindow(QMainWindow):
    """Defines the UI for the application's welcome screen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Project-Based File Exporter")
        self.setMinimumSize(500, 300)
        self.setWindowIcon(QIcon(resource_path("assets/icon.ico")))

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("Recent Projects")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        main_layout.addWidget(title_label)
        main_layout.addSpacing(15)

        # Recent projects container
        self.recent_projects_layout = QVBoxLayout()
        main_layout.addLayout(self.recent_projects_layout)
        main_layout.addStretch()

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)

        # Main action buttons
        button_layout = QHBoxLayout()
        self.browse_projects_button = QPushButton("Browse All Projects")
        self.create_project_button = QPushButton("Create New Project")
        button_layout.addStretch()
        button_layout.addWidget(self.browse_projects_button)
        button_layout.addWidget(self.create_project_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)