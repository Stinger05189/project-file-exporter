# src/core/project_config.py
# Copyright (c) 2025 Google. All rights reserved.

from typing import Dict, List, Any, Type
from datetime import datetime
import copy

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
        
        # Global settings (Shared across all presets)
        self.blacklisted_paths: List[str] = DEFAULT_BLACKLIST[:]
        
        # Active State (These hold the values currently loaded in the UI)
        self.inclusive_filters: List[str] = []
        self.exclusive_filters: List[str] = []
        self.tree_exclusive_filters: List[str] = []
        self.tree_use_gitignore: bool = True
        self.extension_overrides: Dict[str, str] = {}
        
        # Presets Management
        self.active_preset_name: str = "Default"
        self.presets: Dict[str, Dict[str, Any]] = {
            "Default": {
                "inclusive_filters": [],
                "exclusive_filters": [],
                "tree_exclusive_filters": [],
                "tree_use_gitignore": True,
                "extension_overrides": {},
                "export_history": []
            }
        }

        self.config_file_path: str = ""
        self.ui_state: Dict[str, Any] = {}
        
        # Metadata
        self.date_created: str = datetime.utcnow().isoformat()
        self.last_opened: str = datetime.utcnow().isoformat()
        self.export_count: int = 0
        self.last_known_included_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the project's configuration into a dictionary."""
        return {
            "project_name": self.project_name,
            "root_path": self.root_path,
            # We save the current active state to root for fallback/readability
            "inclusive_filters": self.inclusive_filters,
            "exclusive_filters": self.exclusive_filters,
            "tree_exclusive_filters": self.tree_exclusive_filters,
            "tree_use_gitignore": self.tree_use_gitignore,
            "extension_overrides": self.extension_overrides,
            # Global settings
            "blacklisted_paths": self.blacklisted_paths,
            # Preset Data
            "active_preset_name": self.active_preset_name,
            "presets": self.presets,
            # UI & Metadata
            "ui_state": self.ui_state,
            "date_created": self.date_created,
            "last_opened": self.last_opened,
            "export_count": self.export_count,
            "last_known_included_count": self.last_known_included_count,
        }

    @classmethod
    def from_dict(cls: Type['ProjectConfig'], data: Dict[str, Any], file_path: str) -> 'ProjectConfig':
        """Creates a ProjectConfig instance from a dictionary."""
        project = cls(data["project_name"], data["root_path"])
        
        # Load Global Settings
        project.blacklisted_paths = data.get("blacklisted_paths", DEFAULT_BLACKLIST[:])
        project.ui_state = data.get("ui_state", {})
        project.config_file_path = file_path
        
        # Load Metadata
        project.date_created = data.get("date_created", datetime.utcnow().isoformat())
        project.last_opened = data.get("last_opened", datetime.utcnow().isoformat())
        project.export_count = data.get("export_count", 0)
        project.last_known_included_count = data.get("last_known_included_count", 0)

        # --- MIGRATION & PRESET LOGIC ---
        
        # Load values temporarily (needed for migration)
        inc = data.get("inclusive_filters", [])
        exc = data.get("exclusive_filters", [])
        tree_exc = data.get("tree_exclusive_filters", [])
        use_git = data.get("tree_use_gitignore", True)
        overrides = data.get("extension_overrides", {})

        # Load Presets if they exist
        if "presets" in data and isinstance(data["presets"], dict):
            project.presets = data["presets"]
            project.active_preset_name = data.get("active_preset_name", "Default")
            
            # Safety: Ensure Default exists even if presets key exists but is empty
            if "Default" not in project.presets:
                project.presets["Default"] = {
                    "inclusive_filters": [],
                    "exclusive_filters": [],
                    "tree_exclusive_filters": [],
                    "tree_use_gitignore": True,
                    "extension_overrides": {},
                    "export_history": []
                }
            
            # Ensure backward compatibility for export_history in existing presets
            for p_name, p_data in project.presets.items():
                if "export_history" not in p_data:
                    p_data["export_history"] = []
        else:
            # LEGACY FILE DETECTED: Migration Strategy
            # Create a 'Default' preset using the root-level values found in the old file
            project.presets = {
                "Default": {
                    "inclusive_filters": copy.deepcopy(inc),
                    "exclusive_filters": copy.deepcopy(exc),
                    "tree_exclusive_filters": copy.deepcopy(tree_exc),
                    "tree_use_gitignore": use_git,
                    "extension_overrides": copy.deepcopy(overrides),
                    "export_history": []
                }
            }
            project.active_preset_name = "Default"

        # Finally, set the "Active State" of the class to match the Active Preset
        # This ensures the UI loads what was selected last (or the migrated default)
        active_data = project.presets.get(project.active_preset_name, project.presets["Default"])
        project.inclusive_filters = active_data.get("inclusive_filters", [])
        project.exclusive_filters = active_data.get("exclusive_filters", [])
        project.tree_exclusive_filters = active_data.get("tree_exclusive_filters", [])
        project.tree_use_gitignore = active_data.get("tree_use_gitignore", True)
        project.extension_overrides = active_data.get("extension_overrides", {})

        return project