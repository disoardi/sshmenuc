sshmenuc Documentation
======================

**sshmenuc** is an interactive SSH connection manager with tmux integration and built-in configuration editor.

Features
--------

- 🔑 Interactive menu navigation with keyboard shortcuts
- 🖥️ Tmux session management with automatic attach/create
- 📦 Multi-host connections with split panes (max 6 hosts)
- ⚙️ Built-in config editor (add/edit/delete/rename)
- 🎨 Colorized terminal UI
- 🔒 Support for SSH keys and identity files

Quick Start
-----------

Installation::

    pip install sshmenuc

Usage::

    sshmenuc

Or with custom config::

    sshmenuc -c /path/to/config.json

Configuration
-------------

Default config location: ``~/.config/sshmenuc/config.json``

See :doc:`configuration` for detailed configuration options.

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   configuration
   usage
   keyboard_shortcuts

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/core
   api/ui
   api/utils

.. toctree::
   :maxdepth: 1
   :caption: Development

   contributing
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
