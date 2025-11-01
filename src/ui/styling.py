# src/ui/styling.py
# Copyright (c) 2025 Google. All rights reserved.

"""
Manages the application's visual theme using the pyqtdarktheme library.

This module provides functionalities to load, apply, and save the user's theme
preference (Dark, Light, or Auto-sync with OS). The settings are persisted
in a `settings.json` file in the application's configuration directory.
"""

import json
import os
import sys
from typing import Literal

import qdarktheme

# Define the valid theme names for type hinting and validation
Theme = Literal["dark", "light", "auto"]

def _get_settings_path() -> str:
    """
    Determines the path to the application's settings file.
    
    The path is OS-dependent to follow platform conventions for user config data.
    """
    app_name = "ProjectFileExporter"
    if sys.platform == "win32":
        # Windows: %APPDATA%\ProjectFileExporter\settings.json
        config_dir = os.path.join(os.environ['APPDATA'], app_name)
    else:
        # macOS/Linux: ~/.config/ProjectFileExporter/settings.json
        config_dir = os.path.join(os.path.expanduser('~'), '.config', app_name)
    
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "settings.json")

def save_theme_setting(theme: Theme):
    """Saves the chosen theme string to the settings file."""
    path = _get_settings_path()
    try:
        with open(path, "w") as f:
            json.dump({"theme": theme}, f)
    except IOError as e:
        print(f"Error saving theme setting: {e}")

def load_theme_setting() -> Theme:
    """
    Loads the chosen theme from the settings file.
    
    Defaults to 'auto' if the file doesn't exist, is corrupted, or contains
    an invalid value.
    """
    path = _get_settings_path()
    if not os.path.exists(path):
        return "auto"
    
    try:
        with open(path, "r") as f:
            settings = json.load(f)
            theme = settings.get("theme", "auto")
            if theme in ["dark", "light", "auto"]:
                return theme
            return "auto" # Fallback for invalid value
    except (json.JSONDecodeError, IOError):
        return "auto" # Fallback for corrupted file

def apply_theme(theme: Theme):
    """Applies the specified theme to the entire Qt application."""
    qdarktheme.setup_theme(theme)

def setup_app_theme():
    """
    The main entry point for theming. Loads the saved theme and applies it.
    
    This function should be called once on application startup.
    """
    current_theme = load_theme_setting()
    apply_theme(current_theme)