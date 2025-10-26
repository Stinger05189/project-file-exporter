# src/logic/export_manager.py
# Copyright (c) 2025 Google. All rights reserved.

import os
import shutil
from typing import Dict, Any, Generator

class ExportManager:
    """Handles the file copying process based on a filtered file tree."""

    @staticmethod
    def export_files(
        filtered_tree: Dict[str, Any],
        source_root: str,
        destination_path: str
    ) -> Generator[str, None, None]:
        """
        Copies files and directories marked as 'included' to the destination.

        This is a generator function that yields the path of each file being copied.

        Args:
            filtered_tree (Dict[str, Any]): The file tree after filters have been applied.
            source_root (str): The absolute root path of the source project.
            destination_path (str): The path to the temporary export directory.

        Yields:
            str: The path of the file currently being copied.
        """
        if not os.path.exists(destination_path):
            os.makedirs(destination_path)
        
        def _traverse(node: Dict[str, Any]):
            """Inner recursive function to process the tree."""
            if node.get("status") != "included":
                return
            
            relative_path = os.path.relpath(node["path"], source_root)
            dest_path = os.path.join(destination_path, relative_path)

            if node["type"] == "directory":
                if not os.path.exists(dest_path):
                    os.makedirs(dest_path)
                for child in node["children"]:
                    yield from _traverse(child)
            
            elif node["type"] == "file":
                try:
                    shutil.copy2(node["path"], dest_path)
                    yield node["path"]
                except OSError as e:
                    print(f"Error copying file {node['path']} to {dest_path}: {e}")

        yield from _traverse(filtered_tree)