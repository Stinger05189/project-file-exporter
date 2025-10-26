# src/core/project_config.py
# Copyright (c) 2025 Google. All rights reserved.

from typing import Dict, List, Any, Type

# Sensible defaults for directories to ignore completely during the scan phase.
DEFAULT_BLACKLIST = [
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "build",
    "dist",
    "dist_electron",
    "Binaries",
    "obj",
    "Bin",
    "Intermediate",
    "Saved",
]

class ProjectConfig:
    """Data model for a single project's configuration."""

    def __init__(self, name: str, root_path: str):
        """Initializes a new project configuration."""
        self.project_name: str = name
        self.root_path: str = root_path
        self.inclusive_filters: List[str] = []
        self.exclusive_filters: List[str] = []
        # Add the new blacklisted paths with defaults
        self.blacklisted_paths: List[str] = DEFAULT_BLACKLIST[:]
        self.config_file_path: str = ""
        self.extension_overrides: Dict[str, str] = {}
        self.ui_state: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the project's configuration into a dictionary."""
        return {
            "project_name": self.project_name,
            "root_path": self.root_path,
            "inclusive_filters": self.inclusive_filters,
            "exclusive_filters": self.exclusive_filters,
            "blacklisted_paths": self.blacklisted_paths, # Serialize new field
            "extension_overrides": self.extension_overrides,
            "ui_state": self.ui_state,
        }

    @classmethod
    def from_dict(cls: Type['ProjectConfig'], data: Dict[str, Any], file_path: str) -> 'ProjectConfig':
        """Creates a ProjectConfig instance from a dictionary."""
        project = cls(data["project_name"], data["root_path"])
        project.inclusive_filters = data.get("inclusive_filters", [])
        project.exclusive_filters = data.get("exclusive_filters", [])
        # Deserialize, providing defaults for backward compatibility
        project.blacklisted_paths = data.get("blacklisted_paths", DEFAULT_BLACKLIST[:])
        project.extension_overrides = data.get("extension_overrides", {})
        project.ui_state = data.get("ui_state", {})
        project.config_file_path = file_path
        return project