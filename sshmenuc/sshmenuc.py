import argparse
import json
import os
import re
from typing import List, Any, Dict

import readchar
import sys, logging
import time

from subprocess import call, Popen, PIPE
from clint import resources
from clint.textui import puts, colored

import docker

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class ConnectionManager:
    def __init__(self, config_file: str = None):
        self.config_file = config_file
        self.config_data: Dict[str, Any] = {"targets": []}

        if config_file:
            self.load_config()

    def load_config(self):
        try:
            with open(self.config_file, 'r') as file:
                self.config_data = json.load(file)
        except FileNotFoundError:
            print(f"Config file '{self.config_file}' not found. Creating a new one.")
        except json.JSONDecodeError:
            print(f"Error decoding JSON in '{self.config_file}'. Creating a new one.")

    def save_config(self):
        with open(self.config_file, 'w') as file:
            json.dump(self.config_data, file, indent=4)

    def get_config(self) -> Dict[str, Any]:
        return self.config_data

    def set_config(self, config_data: Dict[str, Any]):
        self.config_data = config_data

    def create_target(self, target_name: str, connections: List[Dict[str, Any]]):
        target = {target_name: connections}
        self.config_data["targets"].append(target)

    def modify_target(self, target_name: str, new_target_name: str = None, connections: List[Dict[str, Any]] = None):
        for target in self.config_data["targets"]:
            if list(target.keys())[0] == target_name:
                if new_target_name:
                    target = {new_target_name: target[target_name]}
                if connections:
                    target[list(target.keys())[0]] = connections
                break

    def delete_target(self, target_name: str):
        for target in self.config_data["targets"]:
            if list(target.keys())[0] == target_name:
                self.config_data["targets"].remove(target)
                break

    def create_connection(self, target_name: str, friendly: str, host: str, connection_type: str = "ssh", command: str = "ssh", zone: str = "", project: str = ""):
        connection = {
            "friendly": friendly,
            "host": host,
            "connection_type": connection_type,
            "command": command,
            "zone": zone,
            "project": project
        }
        for target in self.config_data["targets"]:
            if list(target.keys())[0] == target_name:
                target[target_name].append(connection)
                break

    def modify_connection(self, target_name: str, connection_index: int, friendly: str = None, host: str = None, connection_type: str = None, command: str = None, zone: str = None, project: str = None):
        for target in self.config_data["targets"]:
            if list(target.keys())[0] == target_name:
                connection = target[target_name][connection_index]
                if friendly:
                    connection["friendly"] = friendly
                if host:
                    connection["host"] = host
                if connection_type:
                    connection["connection_type"] = connection_type
                if command:
                    connection["command"] = command
                if zone:
                    connection["zone"] = zone
                if project:
                    connection["project"] = project
                break

    def delete_connection(self, target_name: str, connection_index: int):
        for target in self.config_data["targets"]:
            if list(target.keys())[0] == target_name:
                target[target_name].pop(connection_index)
                break

class ConnectionNavigator:
    global selected_target
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config_data: Dict[str, Any]
        self.load_config()

    def load_config(self):
        try:
            with open(self.config_file, 'r') as file:
                self.config_data = json.load(file)
                logging.debug("Load config file %s", self.config_data)
        except FileNotFoundError:
            logging.error(f"Config file '{self.config_file}' not found.")
        except json.JSONDecodeError:
            logging.critical(f"Error decoding JSON in '{self.config_file}'.")

    def navigate(self):
        current_path = []
        # Keep track of currently selected target
        selected_target = 0
        while True:
            num_targets = self.count_elements(current_path)
            self.print_menu(selected_target, current_path)
            key = readchar.readkey()

            if key == 'q':
                break
            elif key == readchar.key.DOWN:
                # Ensure the new selection would be valid
                if ((selected_target) < (num_targets - 1)) or num_targets == 0:
                    selected_target += 1
            elif key == readchar.key.UP:
                # Ensure the new selection would be valid
                if (selected_target - 1) >= 0:
                    selected_target -= 1
            # elif key == '\x1b[C':  # Right arrow
            #     self.move_right(current_path)
            elif key == readchar.key.LEFT:  # Left arrow
                self.move_left(current_path)
            # elif key == 'c':
            #     self.create_connection(current_path)
            # elif key == 'm':
            #     self.modify_connection(current_path)
            # elif key == 'd':
            #     self.delete_connection(current_path)
            elif key == readchar.key.ENTER:
              if isinstance(self.get_node(current_path), list): # This to prevent a double print if current_path is on a list
                # If the current node is a list, we have reached a target, so we can exit the loop
                current_path.append(selected_target)
                current_path.append(selected_target)
                selected_target = 0
              else:
                # Otherwise, we need to go deeper into the structure
                current_path.append(selected_target)
                selected_target = 0

    def print_menu(self, selected_target, current_path: List[Any]):

        clear_screen = lambda:  os.system('cls') if os.name == 'nt'  else os.system('clear')
        lambda x: True if x % 2 == 0 else False
        clear_screen()
        logging.debug("selected_target: %d", selected_target)
        logging.debug("current_path: %s", current_path)
        current_node = self.get_node(current_path)
        logging.debug("current_node_type: %s", type(current_node))
        logging.debug("current_node: %s", current_node)
        if isinstance(current_node, dict):
            self.print_table(current_node, selected_target, level=len(current_path))
        elif isinstance(current_node, list):
            self.print_table(current_node, selected_target, level=len(current_path)+1)

    def print_table(self, data: Dict[str, Any], selected_target: int, level: int):
        tbl = "+--------+-----------------------------------+"
        print(f"{bcolors.OKCYAN}{tbl}{bcolors.ENDC}")
        row = f"{bcolors.OKCYAN}|{bcolors.ENDC} {bcolors.HEADER}{'#':>6}{bcolors.ENDC} {bcolors.OKCYAN}|{bcolors.ENDC} {bcolors.HEADER}{'Description':^33}{bcolors.ENDC} {bcolors.OKCYAN}|{bcolors.ENDC}"
        print(row)
        print(f"{bcolors.OKCYAN}{tbl}{bcolors.ENDC}")

        if isinstance(data, dict):
            keys = list(data.keys())
            for key in keys:
              if (keys.index(key) == selected_target):
                row = f"{bcolors.OKCYAN}|{bcolors.ENDC} {bcolors.OKGREEN}{keys.index(key):>6}{bcolors.ENDC} {bcolors.OKCYAN}|{bcolors.ENDC} {bcolors.OKGREEN}{key:^33}{bcolors.ENDC} {bcolors.OKCYAN}|{bcolors.ENDC}"
              else:
                row = f"{bcolors.OKCYAN}|{bcolors.ENDC} {keys.index(key):>6} {bcolors.OKCYAN}|{bcolors.ENDC} {key:^33} {bcolors.OKCYAN}|{bcolors.ENDC}"
              print(row)
        elif isinstance(data, list):
            for i, item in enumerate(data):#, start=1):
              t = i
              key = list(item.keys())[0]
              if (t == selected_target):
                row= f"{bcolors.OKCYAN}|{bcolors.ENDC} {bcolors.OKGREEN}{i:>6} w {bcolors.ENDC} {bcolors.OKCYAN}|{bcolors.ENDC} {bcolors.OKGREEN}{key:^33}{bcolors.ENDC} {bcolors.OKCYAN}|{bcolors.ENDC}"
              else:
                row = f"{bcolors.OKCYAN}|{bcolors.ENDC} {i:>6} w  {bcolors.OKCYAN}|{bcolors.ENDC} {key:^33} {bcolors.OKCYAN}|{bcolors.ENDC}"
              print(row)

    def get_node(self, path: List[Any]):
        node: Union[dict, list] = self.config_data
        for item in path:
            if isinstance(node, dict):
                keys = list(node.keys())
                if 0 <= item < len(keys):
                    key = keys[item]
                    if key in node:
                        node = node[key]
                    else:
                        raise KeyError(f"Key '{key}' not found in dictionary.")
            elif isinstance(node, list):
                if item < len(node):
                    node = node[item]
            else:
                raise TypeError(f"Unsupported type: {type(node)}")
        return node

    def get_previous_node(self, path: List[Any]):
        node: Union[dict, list] = self.config_data
        for item in path[:-1]:
            if isinstance(node, dict):
                keys = list(node.keys())
                if 0 <= item < len(keys):
                    key = keys[item]
                    if key in node:
                        node = node[key]
                    else:
                        raise KeyError(f"Key '{key}' not found in dictionary.")
            elif isinstance(node, list):
                if item < len(node):
                    node = node[item]
            else:
                raise TypeError(f"Unsupported type: {type(node)}")
        return node

    def count_elements(self, current_path: List[Any]) -> int:
        node = self.get_node(current_path)
        if isinstance(node, dict):
            return len(node)
        elif isinstance(node, list):
            count = 0
            for item in node:
                if isinstance(item, dict):
                    count += 1
            return count
        else:
            return 0

    def move_left(self, current_path: List[Any]):
        if current_path:
            if isinstance(self.get_node(current_path), dict):
                current_path.pop()
            elif isinstance(self.get_node(current_path), list) and len(current_path) > 1:
                if isinstance(self.get_previous_node(current_path), dict):
                  current_path.pop()
                  current_path.pop()
            elif len(current_path) == 1:
              current_path.clear()
            elif current_path[-1] == 0:
                current_path.pop()
            else:
                current_path[-1] -= 1

    def create_connection(self, current_path: List[Any]):
        # Implement the logic to create a new connection
        pass

    def modify_connection(self, current_path: List[Any]):
        # Implement the logic to modify an existing connection
        pass

    def delete_connection(self, current_path: List[Any]):
        # Implement the logic to delete an existing connection
        pass

def main():
    parser = argparse.ArgumentParser(description="SSH Connection Manager")
    parser.add_argument("-c", "--config", help="Path to the config file", default="config.json")
    parser.add_argument("-l", "--loglevel", help="Severity of log level: debug, info (default), warning, error and critical", default="default")
    args = parser.parse_args()
    print(args)
    if (args.loglevel == "debug"):
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    elif (args.loglevel == "info"):
        logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    elif (args.loglevel == "warning"):
        logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    elif (args.loglevel == "error"):
        logging.basicConfig(stream=sys.stderr, level=logging.ERROR)
    elif (args.loglevel == "critical"):
        logging.basicConfig(stream=sys.stderr, level=logging.CRITICAL)

    navigator = ConnectionNavigator(args.config)
    navigator.navigate()

# # Create a new config file
# config = ConnectionManager("config.json")
# config.create_target("test1_0.0.4", [{"friendly": "coordinator01", "host": "coordinator01", "connection_type": "gssh", "command": "docker", "zone": "cloud_zone", "project": "project_name"}])
# config.create_target("test2_0.0.4", [{"friendly": "coordinator02", "host": "coordinator02", "connection_type": "gssh", "command": "docker", "zone": "cloud_zone", "project": "project_name"}])
# config.save_config()

# # Load an existing config file
# config = ConnectionManager("config.json")
# print(config.get_config())

# # Modify a target
# config.modify_target("test1_0.0.4", new_target_name="new_target_name")
# config.save_config()

# # Delete a target
# config.delete_target("test2_0.0.4")
# config.save_config()

# # Create a new connection
# config.create_connection("new_target_name", "new_connection", "new_host")
# config.save_config()

# # Modify a connection
# config.modify_connection("new_target_name", 0, friendly="modified_connection")
# config.save_config()

# Delete a connection
#config.delete_connection("new_target_name", 0)
#config.save_config()

