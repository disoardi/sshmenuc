Keyboard Shortcuts
==================

Navigation Keys
---------------

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Key
     - Action
   * - ↑ / UP
     - Move selection up
   * - ↓ / DOWN
     - Move selection down
   * - ← / LEFT
     - Go back / Return to previous level
   * - → / RIGHT
     - (Not used)
   * - SPACE
     - Toggle host selection for multi-connection
   * - ENTER
     - Connect to selected host(s)
   * - q
     - Quit application

Configuration Editor Keys
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Key
     - Action
   * - a
     - Add target (at root) or connection (in target)
   * - e
     - Edit selected connection
   * - d
     - Delete selected target or connection
   * - r
     - Rename selected target

Context-Sensitive Actions
--------------------------

The **a**, **e**, **d**, **r** keys perform different actions based on context:

At Root Level:
~~~~~~~~~~~~~~

- **a**: Add new target
- **d**: Delete target
- **r**: Rename target
- **e**: (Not available)

Inside Target (Connection List):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **a**: Add new connection
- **e**: Edit connection
- **d**: Delete connection
- **r**: (Not available)

Multi-Selection
---------------

Maximum Selections:
~~~~~~~~~~~~~~~~~~~

- Up to **6 hosts** can be marked simultaneously
- Marked hosts shown with **[x]** indicator
- Press SPACE again to unmark

Launching Multi-Connection:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Mark desired hosts with SPACE
2. Press ENTER to launch all in tmux
3. Hosts open in tiled split-pane layout

Tips
----

- Use LEFT arrow to quickly deselect all marked hosts
- Use 'q' at any time to exit safely
- Tmux sessions persist after disconnection
