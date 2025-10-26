# src/logic/file_scanner.py
# Copyright (c) 2025 Google. All rights reserved.

import os
from typing import Dict, Any, List

class FileScanner:
    """Scans the file system and builds a representation of the directory tree."""

    @staticmethod
    def scan_directory(root_path: str) -> Dict[str, Any]:
        """
        Recursively traverses a given root_path and builds a hierarchical dictionary.

        Args:
            root_path (str): The absolute path to the directory to scan.

        Returns:
            Dict[str, Any]: A nested dictionary representing the file tree.
        """
        if not os.path.isdir(root_path):
            raise ValueError(f"Provided path '{root_path}' is not a valid directory.")

        tree: Dict[str, Any] = {
            "path": root_path,
            "name": os.path.basename(root_path),
            "type": "directory",
            "children": []
        }

        try:
            for entry in os.scandir(root_path):
                if entry.is_dir():
                    tree["children"].append(FileScanner.scan_directory(entry.path))
                else:
                    tree["children"].append({
                        "path": entry.path,
                        "name": entry.name,
                        "type": "file",
                        "children": []
                    })
        except OSError as e:
            print(f"Error scanning directory {root_path}: {e}")
        
        return tree