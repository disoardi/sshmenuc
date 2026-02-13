Usage Guide
===========

Basic Usage
-----------

Launch sshmenuc::

    sshmenuc

With custom config::

    sshmenuc -c /path/to/config.json

With debug logging::

    sshmenuc --loglevel debug

Navigation
----------

Use arrow keys to navigate through targets and connections:

- **↑/↓**: Move selection up/down
- **→**: Enter selected target
- **←**: Go back to previous level
- **SPACE**: Mark host for multi-connection
- **ENTER**: Connect (single or multi-host)
- **q**: Quit

See :doc:`keyboard_shortcuts` for complete list.

Single Connection
-----------------

1. Navigate to desired host
2. Press ENTER
3. SSH connection opens (or tmux session if available)

Multi-Host Connection
---------------------

1. Navigate to target with multiple hosts
2. Press SPACE to mark hosts (up to 6)
3. Press ENTER to launch tmux with split panes
4. All connections open in tiled layout

Configuration Management
------------------------

Built-in editor accessible with keyboard shortcuts:

- **a**: Add target or connection
- **e**: Edit connection
- **d**: Delete target or connection
- **r**: Rename target

See :doc:`keyboard_shortcuts` for details.

Tmux Integration
----------------

If tmux is available:

- Creates new sessions automatically
- Names sessions with hostname + timestamp
- Detects existing sessions
- Prompts to attach or create new
- Supports split panes for multiple hosts

Without tmux:

- Falls back to direct SSH connection
