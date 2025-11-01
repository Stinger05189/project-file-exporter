# src/logic/file_scanner.py
# Copyright (c) 2025 Google. All rights reserved.

import os
from typing import Dict, Any, List, Set, Tuple

class FileScanner:
    """Scans the file system and builds a representation of the directory tree."""

    @staticmethod
    def scan_directory(root_path: str, blacklisted_paths: List[str] = None) -> Tuple[Dict[str, Any], List[str]]:
        """
        Recursively traverses a given root_path and builds a hierarchical dictionary.
        Also finds and parses all .gitignore files.

        Args:
            root_path (str): The absolute path to the directory to scan.
            blacklisted_paths (List[str], optional): A list of directory/file names to ignore completely. Defaults to None.

        Returns:
            Tuple[Dict[str, Any], List[str]]: A tuple containing the file tree and a list of all gitignore patterns.
        """
        if not os.path.isdir(root_path):
            raise ValueError(f"Provided path '{root_path}' is not a valid directory.")

        # Use a set for O(1) average time complexity lookups.
        blacklist_set: Set[str] = set(blacklisted_paths) if blacklisted_paths else set()

        def _scan(path: str, relative_to_root: str) -> Tuple[Dict[str, Any], List[str]]:
            """Inner recursive scanner that uses the parent's blacklist_set."""
            node: Dict[str, Any] = {
                "path": path,
                "name": os.path.basename(path),
                "type": "directory",
                "children": [],
                "size": 0
            }
            total_size = 0
            gitignore_rules = []
            
            # 1. Look for a .gitignore file in the current directory
            gitignore_path = os.path.join(path, ".gitignore")
            if os.path.isfile(gitignore_path):
                try:
                    with open(gitignore_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            stripped_line = line.strip()
                            if stripped_line and not stripped_line.startswith('#'):
                                # Prepend the current relative path to the rule
                                rule_path = os.path.join(relative_to_root, stripped_line).replace(os.sep, '/')
                                gitignore_rules.append(rule_path)
                except IOError as e:
                    print(f"Could not read .gitignore at {gitignore_path}: {e}")

            try:
                for entry in os.scandir(path):
                    # 2. Performance improvement: completely skip blacklisted paths
                    if entry.name in blacklist_set:
                        continue
                    
                    if entry.is_dir():
                        child_node, child_rules = _scan(
                            entry.path, 
                            os.path.join(relative_to_root, entry.name)
                        )
                        total_size += child_node.get("size", 0)
                        node["children"].append(child_node)
                        gitignore_rules.extend(child_rules) # 3. Aggregate rules from children
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
            return node, gitignore_rules

        return _scan(root_path, "")