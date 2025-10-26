# Project-Based File Exporter

Project-Based File Exporter is a desktop utility built with Python and PyQt6, designed to simplify the process of selecting and copying specific files from a complex source directory to a clean, temporary location. It allows users to create reusable "projects," each with its own set of powerful filtering rules, making it ideal for managing build artifacts, preparing files for distribution, or isolating specific assets from a larger repository.

## Key Features

The application provides a robust set of features to streamline the file export workflow:

*   **Project Management:**
    *   Create and manage multiple projects, each linked to a specific source directory.
    *   Project configurations are saved automatically and centrally in the user's application data folder, not cluttered within the project directory.

*   **Configurable Filtering:**
    *   **Inclusive Filters:** Specify which files or directories to include using glob patterns (e.g., `*.py`, `docs/`, `src/**/*.ui`).
    *   **Exclusive Filters:** Specify which files or directories to explicitly exclude (e.g., `__pycache__/`, `*.log`, `.git/`). Exclusive filters always take precedence.

*   **Interactive File Tree:**
    *   Visualize the entire source directory structure within the application.
    *   Get immediate visual feedback on which files and folders are included or excluded based on the current filter rules (excluded items are grayed out).

*   **Context Menu Operations:**
    *   Right-click on any file or folder in the tree to instantly add it to the include or exclude list. The application updates the filter rules and refreshes the tree automatically.

*   **Smart Export Process:**
    *   **Temporary Export Path:** Files are exported to a dedicated, temporary folder in the user's system, which is automatically cleared before each new export.
    *   **Flattened Output:** The entire directory structure is flattened, meaning all copied files reside in a single export folder for easy access.
    *   **Name Collision Resolution:** If multiple files with the same name are exported (e.g., `src/a/icon.svg` and `src/b/icon.svg`), the application automatically renames the conflicting files by appending a sanitized version of their original path (e.g., `icon (src_b_icon).svg`).
    *   **Extension Overrides:** Optionally define rules to change file extensions during the export process (e.g., automatically convert all `.svg` files to `.xml`).

## Getting Started

### Prerequisites
*   Python 3.x
*   PyQt6

### Installation
Install the required Python library using pip:
```bash
pip install PyQt6
```

### Running the Application
To run the application, navigate to the **root directory** of the project in your terminal and execute the following command:

```bash
python -m src.main
```

This will launch the main project selection window.

## Architectural Overview

The application is designed using a **Model-View-Controller (MVC)** pattern to ensure a clean separation between the user interface, data management, and business logic.

#### **1. Core Design (MVC)**

*   **Model (`src/core`, `src/logic`):** This is the application's core.
    *   The `core` modules (`ProjectConfig`, `ConfigManager`) define the data structures and handle the loading/saving of project `.json` configuration files.
    *   The `logic` modules (`FileScanner`, `FilterEngine`, `ExportManager`) contain the stateless business logic. They are responsible for all file system operations, applying filter rules, and executing the complex export process.

*   **View (`src/ui/views`):** This represents the user interface.
    *   Built with PyQt6, these classes (`ProjectListWindow`, `ProjectViewWindow`) define the layout and widgets the user interacts with. They are responsible for displaying data and emitting signals based on user actions (e.g., a button click).

*   **Controller (`src/ui/controllers`):** This acts as the intermediary.
    *   The controller classes (`ProjectListController`, `ProjectViewController`) listen for signals from the View. When a user performs an action, the controller calls the appropriate methods in the Model (e.g., telling the `ExportManager` to begin an export). It then takes the result from the Model and updates the View.

#### **2. Configuration Management**

*   Each project is stored as a single `.json` file.
*   The `ConfigManager` handles all CRUD (Create, Read, Update, Delete) operations for these files.
*   To avoid clutter, project files are not stored locally. Instead, they are saved to a standard, OS-specific application data directory:
    *   **Windows:** `%APPDATA%\ProjectFileExporter\Projects`
    *   **macOS/Linux:** `~/.config/ProjectFileExporter/Projects`

#### **3. The Export Pipeline**

The core operational workflow of the application follows a clear, three-step pipeline:

1.  **File System Scan (`FileScanner`):** When a project is opened or filters are applied, the `FileScanner` recursively traverses the project's source directory and builds an in-memory tree representation (as a nested dictionary) of all files and folders.

2.  **Filter Application (`FilterEngine`):** The `FilterEngine` takes this raw tree and iterates through every node. It applies the user-defined inclusive and exclusive filter patterns, marking each node as either `"included"` or `"excluded"`.

3.  **Export Execution (`ExportManager`):** When the user clicks "Export," the `ExportManager` receives the filtered tree and performs the final actions:
    *   It creates a clean, temporary directory.
    *   It collects a flat list of all file nodes marked as `"included"`.
    *   It iterates through this list, applying any extension overrides and resolving name collisions before copying each file to the flattened temporary directory.

## File Structure

```
project-file-exporter/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config_manager.py
│   │   └── project_config.py
│   ├── logic/
│   │   ├── __init__.py
│   │   ├── export_manager.py
│   │   ├── file_scanner.py
│   │   └── filter_engine.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── controllers/
│   │   │   ├── __init__.py
│   │   │   ├── project_list_controller.py
│   │   │   └── project_view_controller.py
│   │   └── views/
│   │       ├── __init__.py
│   │       ├── project_list_window.py
│   │       └── project_view_window.py
│   └── main.py
└── README.md
```