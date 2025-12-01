import argparse
import json
import os

# import re
from typing import List, Any, Dict, Union

import readchar
import sys, logging

# import time

import subprocess
from clint import resources
from clint.textui import puts, colored

import docker  # used for Google Cloud ssh via gcp cli in docket image
import shutil
import time
import re
import shlex


################################################
#          Class to define the colors          #
################################################


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class ConnectionManager:
    def __init__(self, config_file: str = None):
        self.config_file = config_file
        self.config_data: Dict[str, Any] = {"targets": []}

        if config_file:
            self.load_config()

    def load_config(self):
        try:
            with open(self.config_file, "r") as file:
                self.config_data = json.load(file)
        except FileNotFoundError:
            print(f"Config file '{self.config_file}' not found. Creating a new one.")
        except json.JSONDecodeError:
            print(f"Error decoding JSON in '{self.config_file}'. Creating a new one.")

    def save_config(self):
        with open(self.config_file, "w") as file:
            json.dump(self.config_data, file, indent=4)

    def get_config(self) -> Dict[str, Any]:
        return self.config_data

    def set_config(self, config_data: Dict[str, Any]):
        self.config_data = config_data

    def create_target(self, target_name: str, connections: List[Dict[str, Any]]):
        target = {target_name: connections}
        self.config_data["targets"].append(target)

    def modify_target(
        self,
        target_name: str,
        new_target_name: str = None,
        connections: List[Dict[str, Any]] = None,
    ):
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

    def create_connection(
        self,
        target_name: str,
        friendly: str,
        host: str,
        connection_type: str = "ssh",
        command: str = "ssh",
        zone: str = "",
        project: str = "",
    ):
        connection = {
            "friendly": friendly,
            "host": host,
            "connection_type": connection_type,
            "command": command,
            "zone": zone,
            "project": project,
        }
        for target in self.config_data["targets"]:
            if list(target.keys())[0] == target_name:
                target[target_name].append(connection)
                break

    def modify_connection(
        self,
        target_name: str,
        connection_index: int,
        friendly: str = None,
        host: str = None,
        connection_type: str = None,
        command: str = None,
        zone: str = None,
        project: str = None,
    ):
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


################################################
#    Class to navigate and create the menu'    #
################################################
class ConnectionNavigator:
    global selected_target

    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config_data: Dict[str, Any]
        self.load_config()

    def load_config(self):
        try:
            with open(self.config_file, "r") as file:
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

            if key == "q":
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
                if isinstance(
                    self.get_node(current_path), list
                ):  # This to prevent a double print if current_path is on a list
                    current_node = self.get_node(current_path)
                    if (
                        "friendly" in current_node[selected_target]
                    ):  # If is a host call command
                        # if current_node[0]['connection_type'] == "ssh": # TODO create different call
                        host = current_node[selected_target]["host"]
                        if "user" in current_node[selected_target]:
                            user = current_node[selected_target]["user"]
                        else:
                            user = os.getlogin()
                        if "certkey" in current_node[selected_target]:
                            launcher = SSHLauncher(
                                host, user, 22, current_node[selected_target]["certkey"]
                            )
                        else:
                            launcher = SSHLauncher(host, user)
                        launcher.launch()
                    else:
                        # If the current node is a list, we have reached a target, so we can exit the loop
                        current_path.extend([selected_target, 0])
                        selected_target = 0
                else:
                    # Otherwise, we need to go deeper into the structure
                    current_path.append(selected_target)
                    selected_target = 0

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
            elif (
                isinstance(self.get_node(current_path), list) and len(current_path) > 1
            ):
                if isinstance(self.get_previous_node(current_path), dict):
                    current_path.pop()
                    current_path.pop()
            elif len(current_path) == 1:
                current_path.clear()
            elif current_path[-1] == 0:
                current_path.pop()
            else:
                current_path[-1] -= 1

    ################################################
    # Function to print Menu', items and structure #
    ################################################
    def print_menu(self, selected_target, current_path: List[Any]):
        clear_screen = lambda: (
            os.system("cls") if os.name == "nt" else os.system("clear")
        )
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
            self.print_table(current_node, selected_target, level=len(current_path) + 1)

    def print_table(self, data: Dict[str, Any], selected_target: int, level: int):
        if isinstance(data, dict):
            self.print_header(["Description"])
            keys = list(data.keys())
            for key in keys:
                if keys.index(key) == selected_target:
                    self.print_row([keys.index(key), key], True, False, False)
                else:
                    self.print_row([keys.index(key), key], False, False, False)
            row = f"{bcolors.OKCYAN}+--------+------------------------------------+{bcolors.ENDC}"
            print(row)
        elif isinstance(data, list):
            # protezione se lista vuota
            if not data:
                return
            # determina se è una lista di host (host dict) o gruppi
            # consideriamo host anche i dict che hanno 'friendly' o 'host' (o almeno 'host')
            table_has_host = any(isinstance(x, dict) and ("friendly" in x or "host" in x) for x in data)
            if table_has_host:
                self.print_header(["Description", "Connection Type"])
            else:
                self.print_header(["Description"])
            for i, item in enumerate(data):
                # considera host i dict che hanno 'friendly' o 'host'
                if isinstance(item, dict) and ("friendly" in item or "host" in item):
                    if i == selected_target:
                        self.print_row([i, item, item.get("connection_type", "")], True, True, table_has_host)
                    else:
                        self.print_row([i, item, item.get("connection_type", "")], False, True, table_has_host)
                else:
                    # gruppo: item è dict con una singola chiave o elemento non-host
                    key = list(item.keys())[0] if isinstance(item, dict) and item else str(item)
                    if i == selected_target:
                        self.print_row([i, key], True, False, table_has_host)
                    else:
                        self.print_row([i, key], False, False, table_has_host)
            if table_has_host:
                row = f"{bcolors.OKCYAN}+--------+------------------------------------+------------------------------------+------------------------------------+{bcolors.ENDC}"
            else:
                row = f"{bcolors.OKCYAN}+--------+------------------------------------+{bcolors.ENDC}"
            print(row)


    def print_row(self, infos: tuple, is_selected_targes: bool, is_host: bool, table_has_host: bool = False):
        """
        infos può essere:
         - [index, key] per voci di gruppo
         - [index, item_dict, connection_type] per host finali
         - [item_dict, friendly, connection_type] (vecchio formato) ancora supportato
        table_has_host indica se la tabella corrente ha le colonne notes/user (da header).
        """
        # default values
        idx_display = ""
        title = ""
        notes = ""
        user = os.getlogin()

        # Normalizza i valori in base al formato di infos
        if len(infos) == 3:
            first, second, third = infos
            # caso nuovo: first = index (int), second = item dict, third = connection_type
            if isinstance(first, int) and isinstance(second, dict):
                idx_display = f"{first:>7}"
                item_dict = second
                title = item_dict.get("friendly", item_dict.get("host", ""))
                notes = third or item_dict.get("connection_type", "")
                user = item_dict.get("user", os.getlogin())
            # caso vecchio: first = item dict, second = friendly, third = connection_type
            elif isinstance(first, dict):
                item_dict = first
                idx_display = f"{infos[0]:>7}" if isinstance(infos[0], int) else ""
                title = second
                notes = third or item_dict.get("connection_type", "")
                user = item_dict.get("user", os.getlogin())
            # caso generico: first è indice, second è titolo stringa
            else:
                idx_display = f"{first:>7}"
                title = second
                notes = third or ""
        else:
            # len == 2 ; formato [index, key]
            idx_display = f"{infos[0]:>7}"
            title = infos[1]
            notes = ""
            user = os.getlogin()

        # assicurarsi che siano stringhe per la formattazione
        idx_display = str(idx_display)
        title = "" if title is None else str(title)
        notes = "" if notes is None else str(notes)
        user = "" if user is None else str(user)

        # placeholder per colonne aggiuntive (quando la tabella ha host ma la riga non è host)
        notes_field = f"{notes:<35}"
        user_field = f"{user:<35}"
        empty_notes = f"{'':<35}"
        empty_user = f"{'':<35}"

        # Costruisci la riga a seconda dello stato selezionato
        if is_selected_targes:
            if is_host:
                row = (
                    f"{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.OKGREEN}{idx_display} {bcolors.ENDC}"
                    f"{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.OKGREEN} {title:<35}{bcolors.ENDC}"
                    f"{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.OKGREEN} {notes_field}{bcolors.ENDC}"
                    f"{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.OKGREEN} {user_field}{bcolors.ENDC}{bcolors.OKCYAN}|{bcolors.ENDC}"
                )
            else:
                if table_has_host:
                    row = (
                        f"{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.OKGREEN}{idx_display} {bcolors.ENDC}"
                        f"{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.OKGREEN} {title:<35}{bcolors.ENDC}"
                        f"{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.OKGREEN} {empty_notes}{bcolors.ENDC}"
                        f"{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.OKGREEN} {empty_user}{bcolors.ENDC}{bcolors.OKCYAN}|{bcolors.ENDC}"
                    )
                else:
                    row = (
                        f"{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.OKGREEN}{idx_display} {bcolors.ENDC}"
                        f"{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.OKGREEN} {title:<35}{bcolors.ENDC}{bcolors.OKCYAN}|{bcolors.ENDC}"
                    )
        else:
            if is_host:
                row = (
                    f"{bcolors.OKCYAN}|{bcolors.ENDC}{idx_display} {bcolors.OKCYAN}|{bcolors.ENDC}"
                    f" {title:<35}{bcolors.OKCYAN}|{bcolors.ENDC} {notes_field}"
                    f"{bcolors.OKCYAN}|{bcolors.ENDC} {user_field}{bcolors.OKCYAN}|{bcolors.ENDC}"
                )
            else:
                if table_has_host:
                    row = (
                        f"{bcolors.OKCYAN}|{bcolors.ENDC}{idx_display} {bcolors.OKCYAN}|{bcolors.ENDC}"
                        f" {title:<35}{bcolors.OKCYAN}|{bcolors.ENDC} {empty_notes}"
                        f"{bcolors.OKCYAN}|{bcolors.ENDC} {empty_user}{bcolors.OKCYAN}|{bcolors.ENDC}"
                    )
                else:
                    row = (
                        f"{bcolors.OKCYAN}|{bcolors.ENDC}{idx_display} {bcolors.OKCYAN}|{bcolors.ENDC}"
                        f" {title:<35}{bcolors.OKCYAN}|{bcolors.ENDC}"
                    )

        print(row)


    def print_header(self, header: tuple):
        tbl = "+--------+------------------------------------+"
        tblNotes = "+--------+------------------------------------+------------------------------------+------------------------------------+"
        if len(header) == 2:
            print(f"{bcolors.OKCYAN}{tblNotes}{bcolors.ENDC}")
            Description, Notes = header
            print(
                f"{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.HEADER}{'#':>7} {bcolors.ENDC}{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.HEADER}{Description:^35} {bcolors.ENDC}{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.HEADER}{Notes:^35} {bcolors.ENDC}{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.HEADER}{'User':^35} {bcolors.ENDC}{bcolors.OKCYAN}|{bcolors.ENDC}"
            )
            print(f"{bcolors.OKCYAN}{tblNotes}{bcolors.ENDC}")
        else:
            print(f"{bcolors.OKCYAN}{tbl}{bcolors.ENDC}")
            Description = header
            print(
                f"{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.HEADER}{'#':>7} {bcolors.ENDC}{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.HEADER}{header[0]:^35} {bcolors.ENDC}{bcolors.OKCYAN}|{bcolors.ENDC}"
            )
            print(f"{bcolors.OKCYAN}{tbl}{bcolors.ENDC}")


################################################
# Class to manage ssh connection               #
################################################
class SSHLauncher:
    def __init__(self, host, username, port=22, identity_file=None):
        self.host = host
        self.username = username
        self.port = port
        self.identity_file = identity_file

    def launch(self):
        ssh_command = ["ssh"]

        if self.identity_file:
            ssh_command.extend(["-i", self.identity_file])

        ssh_command.extend([f"{self.username}@{self.host}", "-p", str(self.port)])

        try:
            # If tmux is available, create (and attach) a tmux session named host-timestamp
            if shutil.which("tmux"):
                # sanitize session name: keep alnum, underscore, dash
                session_raw = f"{self.host}-{int(time.time())}"
                session = re.sub(r"[^A-Za-z0-9_-]+", "-", session_raw)

                # build a safely quoted ssh command string for tmux
                ssh_cmd_str = " ".join(shlex.quote(p) for p in ssh_command)

                # create and attach new tmux session that runs the ssh command
                tmux_cmd = ["tmux", "new-session", "-s", session, ssh_cmd_str]
                subprocess.run(tmux_cmd)
            else:
                # fallback: run ssh directly
                subprocess.run(ssh_command)

            if logging.getLogger().level == logging.DEBUG:
                readchar.readkey()
        except Exception as e:
            print(f"Error launching SSH client: {e}")

    # Example usage
    # launcher = SSHLauncher("example.com", "your_username", identity_file="/path/to/your/key.pem")
    # launcher.launch()


################################################
#                     Main                     #
################################################


def main():
    parser = argparse.ArgumentParser(description="SSH Connection Manager")
    parser.add_argument(
        "-c",
        "--config",
        help="Path to the config file",
        default=os.path.expanduser("~") + "/.config/sshmenuc/config.json",
    )
    parser.add_argument(
        "-l",
        "--loglevel",
        help="Severity of log level: debug, info (default), warning, error and critical",
        default="default",
    )
    args = parser.parse_args()
    print(args)
    if args.loglevel == "debug":
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    elif args.loglevel == "info":
        logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    elif args.loglevel == "warning":
        logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    elif args.loglevel == "error":
        logging.basicConfig(stream=sys.stderr, level=logging.ERROR)
    elif args.loglevel == "critical":
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
# config.delete_connection("new_target_name", 0)
# config.save_config()

main()
