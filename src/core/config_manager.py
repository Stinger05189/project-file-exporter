# src/core/config_manager.py
# Copyright (c) 2025 Google. All rights reserved.

import os
import json
from typing import Dict, List
import sys

from src.core.project_config import ProjectConfig

class ConfigManager:
    """Handles the loading, saving, and management of all project configuration files."""

    def __init__(self):
        """Initializes the ConfigManager."""
        self.projects_directory = self._get_app_config_dir()
        self.projects: Dict[str, ProjectConfig] = {}
        if not os.path.exists(self.projects_directory):
            os.makedirs(self.projects_directory)

    def _get_app_config_dir(self) -> str:
        """Returns the appropriate user-specific config directory for the OS."""
        app_name = "ProjectFileExporter"
        if sys.platform == "win32":
            # Windows: %APPDATA%\ProjectFileExporter\Projects
            return os.path.join(os.environ['APPDATA'], app_name, 'Projects')
        else:
            # macOS/Linux: ~/.config/ProjectFileExporter/Projects
            return os.path.join(os.path.expanduser('~'), '.config', app_name, 'Projects')

    def load_projects(self):
        """Scans the projects directory, parses .json files, and populates the projects dictionary."""
        self.projects.clear()
        for filename in os.listdir(self.projects_directory):
            if filename.endswith(".json"):
                file_path = os.path.join(self.projects_directory, filename)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        project = ProjectConfig.from_dict(data, file_path)
                        self.projects[project.project_name] = project
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Warning: Could not load project from {filename}. Error: {e}")

    def save_project(self, project_config: ProjectConfig):
        """Saves a single ProjectConfig instance to a .json file."""
        # Sanitize project name for use as a filename
        safe_filename = "".join(c for c in project_config.project_name if c.isalnum() or c in (' ', '_')).rstrip()
        file_path = os.path.join(self.projects_directory, f"{safe_filename}.json")
        
        project_config.config_file_path = file_path
        with open(file_path, 'w') as f:
            json.dump(project_config.to_dict(), f, indent=4)

    def add_project(self, name: str, root_path: str) -> ProjectConfig:
        """Creates a new ProjectConfig, saves it, and adds it to the manager."""
        if name in self.projects:
            raise ValueError(f"A project with the name '{name}' already exists.")
        
        project = ProjectConfig(name, root_path)
        self.save_project(project)
        self.projects[name] = project
        return project

    def remove_project(self, project_name: str):
        """Deletes the project's configuration file and removes it from the manager."""
        if project_name in self.projects:
            project = self.projects[project_name]
            if os.path.exists(project.config_file_path):
                os.remove(project.config_file_path)
            del self.projects[project_name]
        else:
            raise ValueError(f"No project found with the name '{project_name}'.")

    def rename_project(self, old_name: str, new_name: str):
        """Renames a project, updating its config file and internal state."""
        if new_name in self.projects and new_name != old_name:
            raise ValueError(f"A project with the name '{new_name}' already exists.")

        if old_name not in self.projects:
            raise ValueError(f"No project found with the name '{old_name}'.")

        # Get the project, remove the old file
        project = self.projects[old_name]
        if os.path.exists(project.config_file_path):
            os.remove(project.config_file_path)

        # Update the project object and save under a new name
        project.project_name = new_name
        self.save_project(project)

        # Update the internal dictionary
        del self.projects[old_name]
        self.projects[new_name] = project

    def get_project(self, project_name: str) -> ProjectConfig:
        """Retrieves a specific ProjectConfig object by name."""
        return self.projects[project_name]

    def get_all_projects(self) -> List[ProjectConfig]:
        """Returns a list of all loaded ProjectConfig objects."""
        return list(self.projects.values())