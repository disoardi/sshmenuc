import argparse
import json
import os
import re
from typing import List, Any

import readchar
import sys
import time

from subprocess import call, Popen, PIPE
from clint import resources
from clint.textui import puts, colored

import docker

new_con = {
    "test2_0.0.4": [
    {
        "friendly": "coordinator02",
        "host": "coordinator02",
        "connection_type": "gssh",
        "command": "docker",
        "zone": "cloud_zone",
        "project": "project_name"
    }
    ]
}

with open("json_test.json") as write_file:
    data = json.load(write_file)
    targets = data['targets']
    #print(list(targets.keys())[0])
    for index, target in enumerate(targets):
        #print(index, target)
        print(index, list(target.keys())[0])
    data['targets'].append(new_con)
    print(json.dumps(data, indent = 4, sort_keys=True))


class Connection:

    def __init__(self, friendly, host, option)
        self.friendly = friendly
        self.host = host
        self.option = option
