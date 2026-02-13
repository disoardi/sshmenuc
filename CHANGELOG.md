# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2024-XX-XX

### Added
- **Interactive Config Editor**: Integrated CRUD operations directly in navigation menu
  - Add targets and connections with 'a' key
  - Edit connections with 'e' key
  - Delete targets/connections with 'd' key
  - Rename targets with 'r' key
  - Form-based input with validation and confirmation prompts
- Comprehensive test coverage (102 tests, 69% coverage)
- Type hints improvements with Optional and return types
- Constants for magic numbers (MAX_MARKED_SELECTIONS, MAX_TMUX_PANES)

### Changed
- **All docstrings and comments translated to English** (CLAUDE.md compliance)
- Improved error handling with specific exception types
- Replaced os.system() with subprocess.run() for better security
- Updated menu instructions to show editing commands
- Refactored config.py with helper methods (_get_target_key, _find_target)

### Fixed
- **Version mismatch**: synchronized __init__.py (0.1.0 → 1.1.0) with pyproject.toml
- **Critical bug in get_previous_node()**: added target aggregation logic matching get_node()
- Fixed print_menu() to properly call display.print_table()

### Technical Improvements
- Code refactoring to eliminate duplication
- Enhanced type safety across codebase
- Improved test coverage for launcher and navigation modules
- Better error messages with debug logging

## [1.0.0] - 2024-XX-XX

### Added
- Complete OOP refactoring with modular architecture (core/ui/utils)
- Support for tmux sessions with automatic session management
- Support for multiple connections with split panes
- Attach to existing tmux sessions
- GitHub Actions CI/CD pipeline
- Mock support for no-tty environments

### Changed
- Migrated from monolithic to modular structure
- Enhanced code organization and maintainability

## [0.0.4] - 2024-XX-XX

### Changed
- Pre-release improvements and bug fixes

## [Unreleased]

### Planned
- Sphinx API documentation
- PyPI publishing automation
- Pre-commit hooks integration
- Enhanced logging capabilities
