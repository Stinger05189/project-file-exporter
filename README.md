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
    *   **Temporary Export Path:** Files are exported to a dedicated, temporary folder in the user's system.
    *   **Flattened Output:** All copied files reside in a single export folder for easy access.
    *   **Name Collision Resolution:** Automatically renames conflicting files by appending a sanitized version of their original path.
    *   **Extension Overrides:** Define rules to change file extensions during the export process (e.g., `.svg` to `.xml`).

## Getting Started

### Prerequisites
*   Git
*   Python 3.9+
*   Miniconda or Anaconda (Recommended)

### Setup and Running

**1. Clone the Repository**
```bash
git clone <your-repository-url>
cd project-file-exporter
```

**2. Create a Virtual Environment**
It is highly recommended to use a dedicated virtual environment to avoid conflicts with other projects.

*   **Using Conda (Recommended):**
    ```bash
    # Create a new environment named 'exporter-env'
    conda create --name exporter-env python=3.11

    # Activate the environment
    conda activate exporter-env
    ```

*   **Using `venv` (Standard Python):**
    ```bash
    # Create the environment
    python -m venv venv

    # Activate the environment
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

**3. Install Dependencies**
With your environment active, install the required library:
```bash
pip install PyQt6
```

**4. Run the Application**
To run the application, execute the `main` module from the **root directory** of the project:
```bash
python -m src.main
```

## Building the Executable

The project is configured to be packaged into a single, standalone executable (`.exe`) using PyInstaller.

**1. Install PyInstaller**
If you haven't already, install PyInstaller into your active virtual environment:
```bash
pip install pyinstaller
```

**2. Build Using the Spec File (Recommended)**
This repository includes a pre-configured `Project-Based File Exporter.spec` file. This is the most reliable method as it contains all the necessary settings, including the application icon and data files.

From the project root directory, run:
```bash
pyinstaller "Project-Based File Exporter.spec" --clean
```

**3. Locate the Executable**
Once the build process is complete, you will find the final application in the `dist` folder: `dist/Project-Based File Exporter.exe`.

## Architectural Overview

The application is designed using a **Model-View-Controller (MVC)** pattern to ensure a clean separation between the user interface, data management, and business logic.

#### **1. Core Design (MVC)**

*   **Model (`src/core`, `src/logic`):** This is the application's core.
    *   The `core` modules define data structures and handle the loading/saving of project `.json` configurations.
    *   The `logic` modules contain the stateless business logic for file scanning, filter application, and the export process.

*   **View (`src/ui/views`):** This represents the user interface.
    *   Built with PyQt6, these classes define the layout and widgets the user interacts with.

*   **Controller (`src/ui/controllers`):** This acts as the intermediary.
    *   The controller classes listen for signals from the View, call the appropriate methods in the Model, and update the View with the results.

#### **2. Configuration Management**

Project configurations are stored as `.json` files in a standard, OS-specific application data directory to avoid cluttering the user's project folders.
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
├── assets/
│   └── icon.ico
├── src/
│   ├── core/
│   │   ├── config_manager.py
│   │   └── project_config.py
│   ├── logic/
│   │   ├── export_manager.py
│   │   ├── file_scanner.py
│   │   └── filter_engine.py
│   ├── ui/
│   │   ├── controllers/
│   │   │   ├── project_list_controller.py
│   │   │   └── project_view_controller.py
│   │   └── views/
│   │       ├── help_dialog.py
│   │       ├── project_list_window.py
│   │       └── project_view_window.py
│   ├── main.py
│   └── utils.py
├── Project-Based File Exporter.spec
└── README.md
```