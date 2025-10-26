# src/core/project_config.py
# Copyright (c) 2025 Google. All rights reserved.

from typing import Dict, List, Any, Type

class ProjectConfig:
    """Data model for a single project's configuration."""

    def __init__(self, name: str, root_path: str):
        """Initializes a new project configuration."""
        self.project_name: str = name
        self.root_path: str = root_path
        self.inclusive_filters: List[str] = []
        self.exclusive_filters: List[str] = []
        self.config_file_path: str = ""
        self.extension_overrides: Dict[str, str] = {}

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the project's configuration into a dictionary."""
        return {
            "project_name": self.project_name,
            "root_path": self.root_path,
            "inclusive_filters": self.inclusive_filters,
            "exclusive_filters": self.exclusive_filters,
            "extension_overrides": self.extension_overrides,
        }

    @classmethod
    def from_dict(cls: Type['ProjectConfig'], data: Dict[str, Any], file_path: str) -> 'ProjectConfig':
        """Creates a ProjectConfig instance from a dictionary."""
        project = cls(data["project_name"], data["root_path"])
        project.inclusive_filters = data.get("inclusive_filters", [])
        project.exclusive_filters = data.get("exclusive_filters", [])
        project.extension_overrides = data.get("extension_overrides", {})
        project.config_file_path = file_path
        return project