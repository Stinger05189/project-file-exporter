# src/logic/filter_engine.py
# Copyright (c) 2025 Google. All rights reserved.

import fnmatch
from typing import Dict, Any, List
import os

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
            """Checks if the path matches any of the given glob patterns,
            with custom handling for '**' to enable recursive directory matching.
            """
            # Normalize the relative_path to use forward slashes
            normalized_relative_path = relative_path.replace(os.sep, '/')
            
            # Determine if current node is a directory
            is_directory_node = os.path.isdir(os.path.join(root_path, relative_path))

            # Helper for directory matching patterns
            normalized_relative_path_for_dir_patterns = normalized_relative_path
            if is_directory_node and normalized_relative_path != "":
                 normalized_relative_path_for_dir_patterns += '/'
            elif normalized_relative_path == "": 
                 normalized_relative_path_for_dir_patterns = '/'

            for pattern in patterns:
                normalized_pattern = pattern.replace(os.sep, '/')

                # Efficient check for simple patterns
                if '**' not in normalized_pattern:
                    if fnmatch.fnmatch(normalized_relative_path, normalized_pattern) or \
                       fnmatch.fnmatch(normalized_relative_path_for_dir_patterns, normalized_pattern):
                        return True
                    continue

                # --- Manual Handling for Recursive '**' ---

                # Case 1: '**/file' (Suffix match)
                if normalized_pattern.startswith('**/'):
                    sub_pattern = normalized_pattern[3:]
                    # Match against entire path, or any path suffix
                    if fnmatch.fnmatch(normalized_relative_path, sub_pattern):
                        return True
                    
                    path_segments = normalized_relative_path.split('/')
                    for i in range(1, len(path_segments)):
                        suffix_to_check = '/'.join(path_segments[i:])
                        if fnmatch.fnmatch(suffix_to_check, sub_pattern):
                            return True
                    
                    if is_directory_node and fnmatch.fnmatch(normalized_relative_path_for_dir_patterns, normalized_pattern):
                        return True

                # Case 2: 'dir/**' (Prefix match)
                elif normalized_pattern.endswith('/**') or normalized_pattern.endswith('**/'):
                    prefix_to_match = normalized_pattern.rstrip('*/')
                    
                    if normalized_relative_path == prefix_to_match or \
                       normalized_relative_path.startswith(prefix_to_match + '/'):
                        return True
                    
                    if is_directory_node and normalized_relative_path_for_dir_patterns.startswith(prefix_to_match + '/'):
                        return True

                # Case 3: 'dir/**/file' (Middle match)
                else:
                    parts = normalized_pattern.split('**', 1)
                    prefix = parts[0] # e.g. "src/core/"
                    suffix = parts[1] # e.g. "/*.py"

                    # Ensure path starts with the prefix
                    if not normalized_relative_path.startswith(prefix.rstrip('/')):
                        continue

                    # Get the part after the prefix
                    # if prefix is 'src/core/', remove 'src/core/' from 'src/core/file.py' -> 'file.py'
                    # if prefix is 'src/core/', remove 'src/core/' from 'src/core/subdir/file.py' -> 'subdir/file.py'
                    
                    trimmed_prefix = prefix.rstrip('/')
                    if normalized_relative_path == trimmed_prefix:
                        remaining = ""
                    else:
                        remaining = normalized_relative_path[len(trimmed_prefix):]
                        # Remove leading slash if present
                        if remaining.startswith('/'):
                            remaining = remaining[1:]
                    
                    # Match remaining path against suffix.
                    # suffix is likely "/*.py" -> match "*.py"
                    clean_suffix = suffix.lstrip('/')
                    
                    # 1. Direct match (e.g. remaining="file.py", suffix="*.py")
                    if fnmatch.fnmatch(remaining, clean_suffix):
                        return True
                        
                    # 2. Suffix match (e.g. remaining="subdir/file.py", suffix="*.py")
                    remaining_segments = remaining.split('/')
                    for i in range(len(remaining_segments) + 1):
                        seg_suffix = '/'.join(remaining_segments[i:])
                        if fnmatch.fnmatch(seg_suffix, clean_suffix):
                            return True

            return False

        def _traverse(node: Dict[str, Any], parent_excluded: bool = False):
            """Inner recursive function to traverse and mark nodes."""
            relative_path = os.path.relpath(node["path"], root_path)
            
            # Treat '.' as the root directory itself for matching purposes
            if relative_path == ".":
                relative_path = ""

            is_excluded = False
            # Check if this node is excluded by a parent or by its own pattern
            if parent_excluded or _is_match(relative_path, exclusive_filters):
                is_excluded = True

            is_included = False
            if not is_excluded:
                if not inclusive_filters:
                    # If no inclusive filters, everything is included by default
                    is_included = True
                # Check if this node is included by an inclusive filter
                elif _is_match(relative_path, inclusive_filters):
                    is_included = True

            # For directories, if they aren't explicitly included, they are only
            # implicitly included if they contain an included child.
            if node["type"] == "directory":
                child_is_included = False
                for child in node["children"]:
                    # Recursively traverse children; child's status depends on current node's exclusion.
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
        # Using forward slashes for glob patterns
        norm_inclusive = [p.replace(os.sep, '/') for p in inclusive_filters]
        norm_exclusive = [p.replace(os.sep, '/') for p in exclusive_filters]

        _traverse(file_tree)
        return file_tree