# src/logic/file_scanner.py
# Copyright (c) 2025 Google. All rights reserved.

import os
from typing import Dict, Any, List, Set

class FileScanner:
    """Scans the file system and builds a representation of the directory tree."""

    @staticmethod
    def scan_directory(root_path: str, blacklisted_paths: List[str] = None) -> Dict[str, Any]:
        """
        Recursively traverses a given root_path and builds a hierarchical dictionary.

        Args:
            root_path (str): The absolute path to the directory to scan.
            blacklisted_paths (List[str], optional): A list of directory/file names to ignore completely. Defaults to None.

        Returns:
            Dict[str, Any]: A nested dictionary representing the file tree.
        """
        if not os.path.isdir(root_path):
            raise ValueError(f"Provided path '{root_path}' is not a valid directory.")

        # Use a set for O(1) average time complexity lookups.
        blacklist_set: Set[str] = set(blacklisted_paths) if blacklisted_paths else set()

        def _scan(path: str) -> Dict[str, Any]:
            """Inner recursive scanner that uses the parent's blacklist_set."""
            node: Dict[str, Any] = {
                "path": path,
                "name": os.path.basename(path),
                "type": "directory",
                "children": [],
                "size": 0
            }
            total_size = 0
            try:
                for entry in os.scandir(path):
                    # Performance improvement: completely skip blacklisted paths
                    if entry.name in blacklist_set:
                        continue
                    
                    if entry.is_dir():
                        child_node = _scan(entry.path)
                        total_size += child_node.get("size", 0)
                        node["children"].append(child_node)
                    else:
                        try:
                            file_size = entry.stat().st_size
                        except OSError:
                            file_size = 0
                        
                        total_size += file_size
                        node["children"].append({
                            "path": entry.path,
                            "name": entry.name,
                            "type": "file",
                            "size": file_size,
                            "children": []
                        })
            except OSError as e:
                print(f"Error scanning directory {path}: {e}")
            
            node["size"] = total_size
            return node

        return _scan(root_path)