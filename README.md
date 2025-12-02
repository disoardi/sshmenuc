# sshmenuc Refactoring Guide

## Overview

sshmenuc is a complete rewrite of the original sshmenu tool, implemented as an object‑oriented Python application. The project has been redesigned around classes and clear separation of concerns to make the codebase easier to extend, maintain and test.

## Description

sshmenuc provides an interactive terminal menu to browse, filter and launch SSH (and cloud CLI) connections. It supports nested groups of hosts, per‑host metadata (user, connection type, identity file / certkey) and launching different connection commands (e.g., ssh, gcloud ssh inside Docker).

**Important**: sshmenuc intentionally does NOT store or persist plain‑text passwords. If a password is required, either remember it at runtime or use a secure password manager / SSH keys. Password history or in‑app password storage is not supported by design for security reasons.

## Requirements

- Python 3.8+
- Dependencies: readchar, clint, docker
  - These are declared in pyproject.toml for packaging

## New Modular Structure

```
sshmenuc/
├── __init__.py
├── __main__.py          # Module entry point
├── main.py              # Refactored main function
├── sshmenuc.py          # Original file (to be deprecated)
├── core/                # Core business logic
│   ├── __init__.py
│   ├── base.py          # Common base class BaseSSHMenuC
│   ├── config.py        # ConnectionManager
│   ├── navigation.py    # ConnectionNavigator
│   └── launcher.py      # SSHLauncher
├── ui/                  # User interface
│   ├── __init__.py
│   ├── colors.py        # Color management (Colors)
│   └── display.py       # Menu rendering (MenuDisplay)
└── utils/               # Common utilities
    ├── __init__.py
    └── helpers.py       # Helper functions
```

## Common Base Class

### `BaseSSHMenuC` (core/base.py)

Abstract class providing common functionality to all other classes:

- **Configuration management**: Loading, saving, validation
- **Logging setup**: Base logging system configuration
- **Utility methods**: Directory creation, data structure validation
- **Template Method pattern**: Abstract `validate_config()` method to implement

#### Shared Functionality:
- `load_config()`: JSON configuration loading and normalization
- `save_config()`: Configuration saving
- `get_config()` / `set_config()`: Configuration getter/setter
- `has_global_hosts()`: Check for hosts presence in configuration
- `_create_config_directory()`: Configuration directory creation

## Derived Classes

### 1. `ConnectionManager` (core/config.py)
Extends `BaseSSHMenuC` for configuration management:
- CRUD operations on targets and connections
- Specific validation for configuration structures
- Methods to create, modify, delete targets and connections

### 2. `ConnectionNavigator` (core/navigation.py)
Extends `BaseSSHMenuC` for menu navigation:
- Main navigation loop
- User input handling (arrows, space, enter)
- Multiple selection with markers
- Integration with `MenuDisplay` for rendering

### 3. `SSHLauncher` (core/launcher.py)
Standalone class for connection launching:
- tmux session management (single and multiple)
- SSH command construction with parameters
- Session name sanitization
- Multiple connection launching with split panes

## UI Components

### `Colors` (ui/colors.py)
- ANSI color constants definitions
- Text coloring helper methods
- Semantic methods (`success()`, `warning()`, `error()`)

### `MenuDisplay` (ui/display.py)
- Table and menu rendering
- Header, row, footer management
- Multiple selection and marker support
- Complete separation of display logic

## Utilities

### `helpers.py` (utils/helpers.py)
- Argument parser setup
- Logging configuration
- Host entry validation
- Generic support functions

## Installation & Usage

### Install (buildable pip package)

1. Ensure packaging config is present (pyproject.toml). Dependencies are declared there.

2. Install build tooling:
```bash
python -m pip install --upgrade build twine
```

3. Build distributions:
```bash
python -m build
```

4. Install locally:
```bash
# Install built wheel
python -m pip install dist/sshmenuc-<version>-py3-none-any.whl

# Or install in editable mode for development
python -m pip install -e .
```

### Development with Poetry

1. Install Poetry: https://python-poetry.org/docs/#installation

2. Create/install environment and dependencies:
```bash
poetry install
```

3. Activate Poetry virtualenv:
```bash
poetry shell
# or run commands without activating:
poetry run python -m sshmenuc
```

### Running the Application

```bash
# As a module (recommended)
python -m sshmenuc

# Direct execution
python sshmenuc/main.py

# With arguments
python -m sshmenuc -c /path/to/config.json -l debug
```

## Refactoring Benefits

### 1. **Separation of Concerns**
- Each class has a specific, well-defined responsibility
- UI separated from business logic
- Configuration isolated from navigation

### 2. **Reusability**
- Base class provides common functionality
- UI components reusable in other contexts
- SSH launcher usable independently

### 3. **Testability**
- Smaller, focused classes
- Injectable dependencies
- Well-defined public methods for unit testing

### 4. **Extensibility**
- Easy to add new connection types
- Template Method pattern for customizations
- Modular structure for new features

### 5. **Maintainability**
- Logically organized code
- Reduced code duplication
- Clear interfaces between modules

## Migration Guide

### Using the New Structure:

```python
# Instead of importing everything from one file
from sshmenuc.core import ConnectionManager, ConnectionNavigator
from sshmenuc.ui import Colors, MenuDisplay
from sshmenuc.utils import setup_logging

# Create objects with common inheritance
config_manager = ConnectionManager("config.json")
navigator = ConnectionNavigator("config.json")

# Both inherit from BaseSSHMenuC
assert isinstance(config_manager, BaseSSHMenuC)
assert isinstance(navigator, BaseSSHMenuC)
```

### Backward Compatibility
- Original `sshmenuc.py` file remains for compatibility
- New entry point is in `main.py`
- `__main__.py` updated to use new structure

## Testing

The new structure facilitates testing:

```python
# Base class testing
def test_base_config_loading():
    manager = ConnectionManager("test_config.json")
    assert manager.validate_config()

# Isolated UI component testing
def test_colors():
    colors = Colors()
    assert colors.success("test").startswith("\033[92m")

# Launcher testing with mocks
def test_ssh_launcher():
    launcher = SSHLauncher("test.com", "user")
    assert launcher.host == "test.com"
```

## Contributing

Contributions are welcome. Typical workflow:

1. Fork the repository
2. Create a feature branch:
```bash
git checkout -b feature/my-change
```
3. Implement changes, add tests and update documentation
4. Commit and push your branch:
```bash
git commit -am "Describe change"
git push origin feature/my-change
```
5. Open a Pull Request against the main repository

Please follow the existing code style and include tests for new functionality where appropriate.

## License

This project is licensed under GPLv3. See the LICENSE file for details.

## Next Steps

1. **Gradually deprecate** original `sshmenuc.py`
2. **Add comprehensive tests** for each module
3. **Document** public class APIs
4. **Consider** Observer pattern for UI events
5. **Evaluate** dependency injection for greater flexibility