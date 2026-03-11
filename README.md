# Project-Based File Exporter

Project-Based File Exporter is a desktop utility built with Python and PyQt6, designed to simplify the process of selecting and copying specific files from a complex source directory to a clean, temporary location. It allows users to create reusable "projects," each with its own set of powerful filtering rules, making it ideal for managing build artifacts, preparing files for distribution, isolating specific assets from a larger repository, or creating sparse context windows for AI tools.

## Key Features

The application provides a robust set of features to streamline the file export workflow:

- **Advanced Project Management:**
  - A welcome **landing page** showing your most recently used projects for quick access.
  - A full **project browser** to view, sort, and manage all projects, with details like last opened date, export count, and included file count.
  - Create, remove, and **edit project names** through intuitive dialogs.
  - Project configurations are saved automatically and centrally in the user's application data folder, not cluttered within the project directory.

- **Dynamic and Interactive File Tree:**
  - Visualize the entire source directory structure within the application.
  - **Live file watcher** automatically refreshes the tree when files are added, removed, or changed in your project's source directory.
  - Get immediate visual feedback on which files and folders are included or excluded based on the current filter rules (excluded items are grayed out).
  - Convenient toolbar actions to **open the project's source directory** or the final export directory.

- **Configurable Filtering:**
  - **Inclusive Filters:** Specify which files or directories to include using glob patterns (e.g., `*.py`, `docs/`, `src/**/*.ui`).
  - **Exclusive Filters:** Specify which files or directories to explicitly exclude (e.g., `__pycache__/`, `*.log`, `.git/`). Exclusive filters always take precedence.
  - **Context Menu Operations:** Right-click on any file or folder in the tree to instantly add it to the include or exclude list.

- **Sparse Context & Manifest Exports:**
  - **AI Prompt Generation:** Copy a pre-formatted system prompt to instruct AI models to return JSON manifests for specific files.
  - **Clipboard Export:** Instantly export files based on a valid JSON manifest copied to your clipboard.
  - **Manual Selection:** Select individual files and folders directly from the tree for quick, isolated exports.
  - **Visual Export History:** Track your 15 most recent exports per preset with precise timestamps. Click any history item to instantly visualize its file footprint on the tree.

- **Smart Export Process:**
  - **Temporary Export Path:** Files are exported to a dedicated, temporary folder.
  - **Flattened Output:** All copied files reside in a single export folder for easy access.
  - **Name Collision Resolution:** Automatically renames conflicting files by appending a sanitized version of their original path.
  - **Extension Overrides:** Define rules to change file extensions during the export process (e.g., `.svg` to `.xml`).

## Getting Started

### Prerequisites

- Git
- Python 3.9+
- Miniconda or Anaconda (Recommended)

### Setup and Running

**1. Clone the Repository**

```bash
git clone <your-repository-url>
cd project-file-exporter

```

**2. Create a Virtual Environment**
It is highly recommended to use a dedicated virtual environment to avoid conflicts.

- **Using Conda (Recommended):**

```bash
# Create a new environment named 'exporter-env'
conda create --name exporter-env python=3.11

# Activate the environment
conda activate exporter-env

```

- **Using `venv` (Standard Python):**

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
With your environment active, install the required libraries:

```bash
pip install PyQt6 watchdog

```

**4. Run the Application**
To run the application, execute the `main` module from the **root directory** of the project:

```bash
python -m src.main

```

## Building the Executable

The project can be packaged into a single, standalone executable (`.exe` on Windows) using PyInstaller.

**1. Install PyInstaller**
If you haven't already, install PyInstaller into your active virtual environment:

```bash
pip install pyinstaller

```

**2. Build Using the Command**
From the project's root directory, run the following command. This will create a clean build with the application name, icon, and necessary data files included.

```bash
pyinstaller --name "Project-Based File Exporter" --onefile --windowed --clean --icon="assets/icon.ico" --add-data="assets/icon.ico;assets" launcher.py

```

**3. Locate the Executable**
Once the build process is complete, you will find the final application in the `dist` folder: `dist/Project-Based File Exporter.exe`.

## Architectural Overview

The application is designed using a **Model-View-Controller (MVC)** pattern to ensure a clean separation between the user interface, data management, and business logic.

#### **1. Core Design (MVC)**

- **Model (`src/core`, `src/logic`):** This is the application's core.
- The `core` modules define data structures and handle the loading/saving of project `.json` configurations.
- The `logic` modules contain the stateless business logic for file scanning, filter application, and the export process.

- **View (`src/ui/views`):** This represents the user interface.
- Built with PyQt6, these classes define the layout and widgets the user interacts with, including the landing page, project browser, and main project view.

- **Controller (`src/ui/controllers`):** This acts as the intermediary.
- The controller classes (`LandingController`, `ProjectBrowserController`, `ProjectViewController`) listen for signals from the View, call the appropriate methods in the Model, and update the View with the results.

#### **2. Configuration Management**

Project configurations are stored as `.json` files in a standard, OS-specific application data directory to avoid cluttering the user's project folders.

- **Windows:** `%APPDATA%\ProjectFileExporter\Projects`
- **macOS/Linux:** `~/.config/ProjectFileExporter/Projects`

#### **3. The Export Pipeline**

The core operational workflow of the application follows a clear, three-step pipeline:

1. **File System Scan (`FileScanner`):** When a project is opened or filters are applied, the `FileScanner` recursively traverses the project's source directory and builds an in-memory tree representation of all files and folders.
2. **Filter Application (`FilterEngine`):** The `FilterEngine` takes this raw tree and applies the user-defined inclusive and exclusive filter patterns, marking each node as either `"included"` or `"excluded"`.
3. **Export Execution (`ExportManager`):** When the user clicks "Export," the `ExportManager` receives the filtered tree, resolves name collisions, applies extension overrides, and copies the included files to a clean temporary directory.

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
│   │   │   ├── landing_controller.py
│   │   │   ├── project_browser_controller.py
│   │   │   └── project_view_controller.py
│   │   └── views/
│   │       ├── help_dialog.py
│   │       ├── landing_window.py
│   │       ├── project_browser_window.py
│   │       ├── project_edit_dialog.py
│   │       └── project_view_window.py
│   ├── main.py
│   └── utils.py
├── .gitignore
├── launcher.py
├── Project-Based File Exporter.spec
└── README.md
```
