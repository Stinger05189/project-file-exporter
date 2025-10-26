# src/utils.py
# Copyright (c) 2025 Google. All rights reserved.

import sys
import os

def resource_path(relative_path: str) -> str:
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If not running as a bundle, the base path is the project root
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)