# src/logic/export_manager.py
# Copyright (c) 2025 Google. All rights reserved.

import os
import shutil
from typing import Dict, Any, Generator, List
import tempfile

class ExportManager:
    """Handles the file copying process based on a filtered file tree."""

    @staticmethod
    def export_files(
        filtered_tree: Dict[str, Any],
        source_root: str,
        extension_overrides: Dict[str, str]
    ) -> str:
        """
        Copies 'included' files to a cleared temporary directory with a flat structure.
        Handles name collisions and extension overrides.

        Args:
            filtered_tree (Dict[str, Any]): The file tree after filters have been applied.
            source_root (str): The absolute root path of the source project.
            extension_overrides (Dict[str, str]): A map of source extensions to target extensions.

        Returns:
            str: The path to the temporary directory containing the exported files.
        """
        # 1. Create and clear a consistent temporary directory
        temp_dir = os.path.join(tempfile.gettempdir(), "ProjectFileExporter_Export")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        # 2. Flatten the tree to get a list of all files to be copied
        files_to_copy = []
        def _collect_files(node: Dict[str, Any]):
            if node.get("status") == "included":
                if node["type"] == "file":
                    files_to_copy.append(node)
                for child in node.get("children", []):
                    _collect_files(child)
        _collect_files(filtered_tree)

        # 3. Process and copy each file
        used_names = set()
        for node in files_to_copy:
            source_path = node["path"]
            base_name = node["name"]
            
            # a. Apply extension override if applicable
            name_root, original_ext = os.path.splitext(base_name)
            clean_ext = original_ext.lstrip('.').lower() # e.g., '.svg' -> 'svg'
            
            if clean_ext in extension_overrides:
                new_ext = extension_overrides[clean_ext]
                dest_name = f"{name_root}.{new_ext}"
            else:
                dest_name = base_name

            # b. Handle name collisions
            if dest_name in used_names:
                # Create a unique name using the relative path
                relative_path = os.path.relpath(source_path, source_root)
                path_root, path_ext = os.path.splitext(relative_path)
                sanitized_path = path_root.replace(os.sep, '_')
                
                final_root, final_ext = os.path.splitext(dest_name)
                dest_name = f"{final_root} ({sanitized_path}){final_ext}"

            # c. Copy the file
            try:
                shutil.copy2(source_path, os.path.join(temp_dir, dest_name))
                used_names.add(dest_name)
            except OSError as e:
                print(f"Error copying file {source_path}: {e}")
        
        return temp_dir