sshmenu
-------
``sshmenu`` is a simple tool for connecting to remote hosts via ssh. Great if you have trouble remembering ip addresses, hostnames, or usernames.

This tool works by using Python's ``os.execvp(...)``, which will replace the current process (python) with ``ssh``.

This is a fork from mmeyer724/sshmenu code with integration of selboo/sshmenu push.

I have add support to create more than one config level for organize in groups of host

Quick Setup
-----------
Tested working on Fedora with Python 3.7

**Linux**

.. code-block:: bash

   pip3 install sshmenu
   sshmenu

**Development**

.. code-block:: bash

   git clone https://github.com/Mike724/sshmenu.git
   cd sshmenu
   pip3 install -r requirements.txt
   python3 -m sshmenu

For run this versione on your systems overvrite the original sshmenu.py with this file.

In my installation:
.. code-block:: bash

    cp /home/isoardi/Progetti/sshmenu/sshmenu/sshmenu.py /usr/local/lib/python3.7/site-packages/sshmenu/

Configuration
-------------

**Linux**

.. code-block:: bash

   vim ~/.config/sshmenu/config.json

**Default contents**

.. code-block:: json

    {
        "targets": [
            {
                "host": "user@example-machine.local",
                "friendly": "This is an example target",
                "options": []
            },
            {
                "command": "mosh",
                "host": "user@example-machine.local",
                "friendly": "This is an example target using mosh",
                "options": []
            }
        ]
    }

You can specify additional command line options (see `man ssh`) as follows:

.. code-block:: json
    
    {
        "targets": [
            {
                "host": "user@example-machine.local",
                "friendly": "An example target listening non-standard port and verbose flag", 
                "options" : [
                    "-p443",
                    "-v"
                ]
            }
        ]
    }

Todo
----
* Add support to edit, delete and add new groups/hosts
* Return on previous menu level
