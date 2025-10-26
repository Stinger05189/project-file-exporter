# src/core/config_manager.py
# Copyright (c) 2025 Google. All rights reserved.

import os
import json
from typing import Dict, List

from src.core.project_config import ProjectConfig

class ConfigManager:
    """Handles the loading, saving, and management of all project configuration files."""

    def __init__(self, projects_dir: str = "projects"):
        """
        Initializes the ConfigManager.

        Args:
            projects_dir (str): The directory where project .json files are stored.
        """
        self.projects_directory = projects_dir
        self.projects: Dict[str, ProjectConfig] = {}
        if not os.path.exists(self.projects_directory):
            os.makedirs(self.projects_directory)

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

    def get_project(self, project_name: str) -> ProjectConfig:
        """Retrieves a specific ProjectConfig object by name."""
        return self.projects[project_name]

    def get_all_projects(self) -> List[ProjectConfig]:
        """Returns a list of all loaded ProjectConfig objects."""
        return list(self.projects.values())