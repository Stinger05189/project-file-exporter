# src/logic/filter_engine.py
# Copyright (c) 2025 Google. All rights reserved.

import fnmatch
from typing import Dict, Any, List

class FilterEngine:
    """Applies inclusive and exclusive filters to a file tree data structure."""

    @staticmethod
    def apply_filters(
        file_tree: Dict[str, Any],
        root_path: str,
        inclusive_filters: List[str],
        exclusive_filters: List[str]
    ) -> Dict[str, Any]:
        """
        Recursively applies filters to the file tree, marking each node's inclusion status.

        Args:
            file_tree (Dict[str, Any]): The file tree from FileScanner.
            root_path (str): The absolute root path of the project for relative matching.
            inclusive_filters (List[str]): List of glob patterns to include.
            exclusive_filters (List[str]): List of glob patterns to exclude.

        Returns:
            Dict[str, Any]: The file tree with an added 'status' key for each node.
        """
        
        def _is_match(relative_path: str, patterns: List[str]) -> bool:
            """Checks if the path matches any of the given glob patterns."""
            # Add directory matching for patterns like `__pycache__/`
            path_to_check = relative_path + ('/' if os.path.isdir(os.path.join(root_path, relative_path)) else '')
            return any(fnmatch.fnmatch(path_to_check, pattern) or fnmatch.fnmatch(relative_path, pattern) for pattern in patterns)

        def _traverse(node: Dict[str, Any], parent_excluded: bool = False):
            """Inner recursive function to traverse and mark nodes."""
            relative_path = os.path.relpath(node["path"], root_path)
            
            # Treat '.' as the root directory itself for matching purposes
            if relative_path == ".":
                relative_path = ""

            is_excluded = False
            if parent_excluded or _is_match(relative_path, exclusive_filters):
                is_excluded = True

            is_included = False
            if not is_excluded:
                if not inclusive_filters:
                    # If no inclusive filters, everything is included by default
                    is_included = True
                elif _is_match(relative_path, inclusive_filters):
                    is_included = True

            # For directories, if they aren't explicitly included, they are only
            # implicitly included if they contain an included child.
            if node["type"] == "directory":
                child_is_included = False
                for child in node["children"]:
                    # The child's status depends on the current node's exclusion status
                    child_status = _traverse(child, parent_excluded=is_excluded)
                    if child_status == "included":
                        child_is_included = True

                if is_included or child_is_included:
                    node["status"] = "included"
                else:
                    node["status"] = "excluded"
            else: # It's a file
                node["status"] = "included" if is_included else "excluded"

            return node["status"]

        # Normalize paths in filters for consistency
        norm_inclusive = [os.path.normpath(p) for p in inclusive_filters]
        norm_exclusive = [os.path.normpath(p) for p in exclusive_filters]

        _traverse(file_tree)
        return file_tree