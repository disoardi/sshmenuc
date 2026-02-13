Configuration
=============

Config File Location
--------------------

Default: ``~/.config/sshmenuc/config.json``

Custom location::

    sshmenuc -c /path/to/config.json

Config Format
-------------

JSON structure with targets and connections:

.. code-block:: json

    {
      "targets": [
        {
          "Production": [
            {
              "friendly": "web-server",
              "host": "web.example.com",
              "user": "admin",
              "certkey": "/path/to/key.pem",
              "connection_type": "ssh"
            }
          ]
        }
      ]
    }

Connection Fields
-----------------

Required:
~~~~~~~~~

- **host**: Hostname or IP address
- **friendly**: Display name in menu

Optional:
~~~~~~~~~

- **user**: SSH username (default: current user)
- **port**: SSH port (default: 22)
- **certkey**: Path to SSH private key
- **identity_file**: Alternative to certkey
- **connection_type**: Connection type (ssh, gssh, docker)
- **zone**: Cloud zone (for gssh)
- **project**: Cloud project (for gssh)
- **command**: Custom command (for docker)

Example Configurations
----------------------

See ``config.example.json`` in the repository for comprehensive examples.
