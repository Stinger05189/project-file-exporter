# src/ui/views/help_dialog.py
# Copyright (c) 2025 Google. All rights reserved.

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser
from PyQt6.QtCore import Qt

class HelpDialog(QDialog):
    """A custom dialog to display Markdown-formatted help content."""

    def __init__(self, markdown_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filter Guide")
        self.setMinimumSize(600, 500)

        # Layout and Widgets
        layout = QVBoxLayout(self)
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setMarkdown(markdown_text)
        layout.addWidget(self.text_browser)

        # Make the dialog modal
        self.setWindowModality(Qt.WindowModality.ApplicationModal)