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

    def load_config(self):
        """
        Carica e normalizza il file di configurazione in self.config_data.
        Supporta due formati:
         - {"targets": [...]} (formato già corretto)
         - { "Group A": [...], "Group B": [...] } -> viene convertito in {"targets":[{"Group A": [...]}, ...]}
        In caso di file mancante o JSON non valido crea una struttura vuota.
        """
        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
                if isinstance(data, dict) and "targets" not in data:
                    targets = []
                    for k, v in data.items():
                        targets.append({k: v})
                    self.config_data = {"targets": targets}
                else:
                    self.config_data = data
        except FileNotFoundError:
            try:
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            except Exception:
                pass
            self.config_data = {"targets": []}
        except json.JSONDecodeError:
            print(f"Error decoding JSON in '{self.config_file}'. Using empty configuration.")
            self.config_data = {"targets": []}

    def has_global_hosts(self) -> bool:
        """
        Return True if there is at least one host (dict with 'host' or 'friendly')
        anywhere in self.config_data['targets'] for this navigator instance.
        """
        cfg = getattr(self, "config_data", {})
        if not isinstance(cfg, dict):
            return False
        targets = cfg.get("targets", []) if isinstance(cfg.get("targets", []), list) else []
        for t in targets:
            if isinstance(t, dict):
                for v in t.values():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict) and ("friendly" in item or "host" in item):
                                return True
        return False


################################################
#    Class to navigate and create the menu'    #
################################################
class ConnectionNavigator:
    global selected_target

    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config_data: Dict[str, Any]
        self.load_config()
        # set di indici selezionati nella vista corrente
        self.marked_indices = set()

    def load_config(self):
        """
        Carica e normalizza il file di configurazione in self.config_data.
        Supporta due formati:
         - {"targets": [...]} (formato già corretto)
         - { "Group A": [...], "Group B": [...] } -> viene convertito in {"targets":[{"Group A": [...]}, ...]}
        In caso di file mancante o JSON non valido crea una struttura vuota.
        """
        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
                if isinstance(data, dict) and "targets" not in data:
                    targets = []
                    for k, v in data.items():
                        targets.append({k: v})
                    self.config_data = {"targets": targets}
                else:
                    self.config_data = data
        except FileNotFoundError:
            try:
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            except Exception:
                pass
            self.config_data = {"targets": []}
        except json.JSONDecodeError:
            print(f"Error decoding JSON in '{self.config_file}'. Using empty configuration.")
            self.config_data = {"targets": []}

    def has_global_hosts(self) -> bool:
        """
        Return True if there is at least one host (dict with 'host' or 'friendly')
        anywhere in self.config_data['targets'] for this navigator instance.
        """
        cfg = getattr(self, "config_data", {})
        if not isinstance(cfg, dict):
            return False
        targets = cfg.get("targets", []) if isinstance(cfg.get("targets", []), list) else []
        for t in targets:
            if isinstance(t, dict):
                for v in t.values():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict) and ("friendly" in item or "host" in item):
                                return True
        return False

    def navigate(self):
        current_path = []
        selected_target = 0
        while True:
            num_targets = self.count_elements(current_path)
            self.print_menu(selected_target, current_path)
            key = readchar.readkey()

            # Quit
            if key == "q":
                break

            # Arrow navigation
            elif key == readchar.key.DOWN:
                if ((selected_target) < (num_targets - 1)) or num_targets == 0:
                    selected_target += 1
            elif key == readchar.key.UP:
                if (selected_target - 1) >= 0:
                    selected_target -= 1

            elif key == readchar.key.LEFT:  # Left arrow
                # clear selection when moving up a level
                self.marked_indices.clear()
                self.move_left(current_path)
                selected_target = 0

            # Toggle selection (space) quando siamo su una lista
            elif key == " ":
                node = self.get_node(current_path)
                if isinstance(node, list):
                    # toggle selezione per l'indice corrente
                    if selected_target in self.marked_indices:
                        self.marked_indices.remove(selected_target)
                    else:
                        if len(self.marked_indices) < 6:
                            self.marked_indices.add(selected_target)
                        else:
                            # massimo 6
                            puts(colored.red("Maximum 6 selections allowed"))
                # rimani sulla stessa riga

            elif key == readchar.key.ENTER:
                node = self.get_node(current_path)
                # se siamo su lista e ci sono selezioni multiple -> apri tmux con split
                if isinstance(node, list) and self.marked_indices:
                    # raccogli gli host selezionati (solo voci host valide)
                    selected_hosts = []
                    for i in sorted(self.marked_indices):
                        if 0 <= i < len(node):
                            item = node[i]
                            if isinstance(item, dict) and ("host" in item or "friendly" in item):
                                host = item.get("host", item.get("friendly"))
                                user = item.get("user", os.getlogin())
                                ident = item.get("certkey", item.get("identity_file", None))
                                selected_hosts.append({"host": host, "user": user, "identity": ident})
                    if selected_hosts:
                        # usa SSHLauncher per aprire sessione tmux con split panes
                        SSHLauncher.launch_group(selected_hosts)
                        # dopo lancio svuota selezioni
                        self.marked_indices.clear()
                    else:
                        puts(colored.red("No valid hosts selected"))
                else:
                    # comportamento singolo come prima
                    if isinstance(node, list):
                        if (
                            "friendly" in node[selected_target]
                        ):
                            host = node[selected_target]["host"]
                            user = node[selected_target].get("user", os.getlogin())
                            if "certkey" in node[selected_target]:
                                launcher = SSHLauncher(host, user, 22, node[selected_target]["certkey"])
                            else:
                                launcher = SSHLauncher(host, user)
                            launcher.launch()
                        else:
                            current_path.extend([selected_target, 0])
                            selected_target = 0
                    else:
                        current_path.append(selected_target)
                        selected_target = 0

    def get_node(self, path: List[Any]):
        """
        Restituisce il nodo corrente. Se path è vuoto ritorna un dizionario
        aggregato dei target (es. { "Group A": [...], "Group B": [...] }),
        in modo da entrare direttamente nei gruppi all'avvio.
        """
        # Costruisci dict aggregato dai target (lista di dict con singola chiave)
        targets = self.config_data.get("targets", [])
        aggregated: Dict[str, Any] = {}
        for t in targets:
            if isinstance(t, dict):
                for k, v in t.items():
                    aggregated[k] = v

        # Se path è vuoto ritorna l'aggregato (comportamento desiderato all'avvio)
        if not path:
            return aggregated

        # Altrimenti percorri il path a partire dall'aggregato
        cur: Union[dict, list, Any] = aggregated
        for item in path:
            if isinstance(cur, dict):
                keys = list(cur.keys())
                if 0 <= item < len(keys):
                    key = keys[item]
                    cur = cur[key]
                else:
                    return cur
            elif isinstance(cur, list):
                if 0 <= item < len(cur):
                    cur = cur[item]
                else:
                    return cur
            else:
                return cur
        return cur

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
    def node_has_hosts(self, node: Any) -> bool:
        """
        Return True if the given node (dict or list) contains at least one host
        entry (dict with 'friendly' or 'host') among the visible items.
        This checks only the current node's visible elements, so categories that
        only contain subgroups won't trigger host columns.
        """
        if isinstance(node, dict):
            for v in node.values():
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict) and ("friendly" in item or "host" in item):
                            return True
            return False
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, dict) and ("friendly" in item or "host" in item):
                    return True
            return False
        return False

    def print_menu(self, selected_target, current_path: List[Any]):
        clear_screen = lambda: (os.system("cls") if os.name == "nt" else os.system("clear"))
        clear_screen()
        # istruzioni di uso rapido
        print("Navigate with ↑ ↓  select with SPACE (max 6)  press ENTER to open selected hosts  q to quit")
        logging.debug("selected_target: %d", selected_target)
        logging.debug("current_path: %s", current_path)
        current_node = self.get_node(current_path)
        logging.debug("current_node_type: %s", type(current_node))
        logging.debug("current_node: %s", current_node)

        # Always print a single-column table (Description)
        if isinstance(current_node, dict):
            self.print_table(current_node, selected_target, level=len(current_path))
        elif isinstance(current_node, list):
            self.print_table(current_node, selected_target, level=len(current_path) + 1)


    def print_table(self, data: Dict[str, Any], selected_target: int, level: int):
        """
        Print a single-column table showing only Description.
        Works for dict (keys = categories) and list (items = groups or hosts).
        """
        # header (single Description column)
        self.print_header(["Description"])

        if isinstance(data, dict):
            keys = list(data.keys())
            for idx, key in enumerate(keys):
                marked = idx in self.marked_indices
                is_selected = idx == selected_target
                self.print_row([idx, key], is_selected, is_host=False, is_marked=marked)
            print(f"{bcolors.OKCYAN}+--------+------------------------------------+{bcolors.ENDC}")
            return

        # data is a list
        if not data:
            # empty list: still print separator
            print(f"{bcolors.OKCYAN}+--------+------------------------------------+{bcolors.ENDC}")
            return

        for i, item in enumerate(data):
            marked = i in self.marked_indices
            # treat as host if dict contains 'friendly' or 'host'
            if isinstance(item, dict) and ("friendly" in item or "host" in item):
                if i == selected_target:
                    self.print_row([i, item], True, is_host=True, is_marked=marked)
                else:
                    self.print_row([i, item], False, is_host=True, is_marked=marked)
            else:
                # category/group entry: show its single key as description
                key = list(item.keys())[0] if isinstance(item, dict) and item else str(item)
                if i == selected_target:
                    self.print_row([i, key], True, is_host=False, is_marked=marked)
                else:
                    self.print_row([i, key], False, is_host=False, is_marked=marked)

        print(f"{bcolors.OKCYAN}+--------+------------------------------------+{bcolors.ENDC}")


    def print_row(self, infos: tuple, is_selected_targes: bool, is_host: bool, is_marked: bool = False):
        """
        Simplified row printing: only Description column.
        infos:
         - [index, key] for categories
         - [index, item_dict] for hosts (item_dict contains 'friendly' or 'host')
        """
        # defaults
        idx_display = ""
        title = ""
        # normalize
        if len(infos) == 2:
            idx = infos[0]
            second = infos[1]
            idx_display = f"{idx:>7}"
            if isinstance(second, dict):
                title = second.get("friendly", second.get("host", ""))
            else:
                title = str(second)
        else:
            idx_display = str(infos[0])
            title = str(infos[1])

        marker = "[x]" if is_marked and is_host else ("[ ]" if is_host else "   ")

        # selected styling is only color; keep columns aligned
        if is_selected_targes:
            row = (
                f"{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.OKGREEN}{idx_display} {bcolors.ENDC}"
                f"{bcolors.OKCYAN}|{bcolors.ENDC}{bcolors.OKGREEN} {marker} {title:<31}{bcolors.ENDC}{bcolors.OKCYAN}|{bcolors.ENDC}"
            )
        else:
            row = (
                f"{bcolors.OKCYAN}|{bcolors.ENDC}{idx_display} {bcolors.OKCYAN}|{bcolors.ENDC}"
                f" {marker} {title:<31}{bcolors.OKCYAN}|{bcolors.ENDC}"
            )

        print(row)


    def print_header(self, header: List[str]):
        """
        Single-column header for Description.
        """
        tbl = "+--------+------------------------------------+"
        print(f"{bcolors.OKCYAN}{tbl}{bcolors.ENDC}")
        # header[0] is "Description"
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

    def _sanitize_session_name(self, raw: str) -> str:
        # keep alnum, underscore, dash
        return re.sub(r"[^A-Za-z0-9_-]+", "-", raw)

    def _list_tmux_sessions(self) -> List[str]:
        try:
            res = subprocess.run(["tmux", "ls"], capture_output=True, text=True)
            if res.returncode != 0:
                return []
            lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            sessions = []
            for line in lines:
                # tmux ls format: "session_name: N windows (created ...)"
                parts = line.split(":", 1)
                if parts:
                    sessions.append(parts[0])
            return sessions
        except Exception:
            return []

    def launch(self):
        ssh_command = ["ssh"]
        if self.identity_file:
            ssh_command.extend(["-i", self.identity_file])
        ssh_command.extend([f"{self.username}@{self.host}", "-p", str(self.port)])

        try:
            if shutil.which("tmux"):
                sanitized_host = self._sanitize_session_name(self.host)
                existing = self._list_tmux_sessions()
                # find sessions that start with sanitized_host-
                matches = [s for s in existing if s.startswith(f"{sanitized_host}-")]

                if matches:
                    # if multiple, let user pick; if single, ask attach or new
                    if len(matches) == 1:
                        choice = input(f"Found tmux session '{matches[0]}'. Attach (a) or create new (n)? [a/n]: ").strip().lower()
                        if choice == "a" or choice == "":
                            tmux_cmd = ["tmux", "attach-session", "-t", matches[0]]
                            subprocess.run(tmux_cmd)
                            return
                        # else fallthrough to create new
                    else:
                        print("Found existing tmux sessions for this host:")
                        for idx, s in enumerate(matches):
                            print(f"  {idx}) {s}")
                        sel = input("Select index to attach or press Enter to create a new session: ").strip()
                        if sel.isdigit():
                            sel_i = int(sel)
                            if 0 <= sel_i < len(matches):
                                tmux_cmd = ["tmux", "attach-session", "-t", matches[sel_i]]
                                subprocess.run(tmux_cmd)
                                return
                        # else fallthrough to create new

                # create a new session named <sanitized_host>-<timestamp>
                session_raw = f"{self.host}-{int(time.time())}"
                session = self._sanitize_session_name(session_raw)
                ssh_cmd_str = " ".join(shlex.quote(p) for p in ssh_command)
                tmux_cmd = ["tmux", "new-session", "-s", session, ssh_cmd_str]
                subprocess.run(tmux_cmd)
            else:
                # fallback: run ssh directly
                subprocess.run(ssh_command)

            if logging.getLogger().level == logging.DEBUG:
                readchar.readkey()
        except Exception as e:
            print(f"Error launching SSH client: {e}")

    @staticmethod
    def launch_group(host_entries: List[Dict[str, Any]]):
        """
        Open multiple SSH connections inside a tmux session, splitting the window into panes.
        host_entries: list of dicts with keys { 'host': str, 'user': str (optional), 'identity': str (optional) }
        """
        if not shutil.which("tmux"):
            puts(colored.red("tmux not found; cannot open grouped session"))
            return

        if not host_entries:
            puts(colored.red("No hosts provided"))
            return

        # enforce maximum panes
        if len(host_entries) > 6:
            puts(colored.yellow("Maximum 6 hosts supported; truncating list"))
            host_entries = host_entries[:6]

        # session name based on first host + timestamp
        session_raw = f"{host_entries[0]['host']}-{int(time.time())}"
        session = re.sub(r"[^A-Za-z0-9_-]+", "-", session_raw)

        # build ssh command strings
        ssh_cmds = []
        for he in host_entries:
            cmd = ["ssh"]
            identity = he.get("identity") or he.get("certkey")
            if identity:
                cmd.extend(["-i", identity])
            user = he.get("user", os.getlogin())
            cmd.append(f"{user}@{he['host']}")
            ssh_cmds.append(" ".join(shlex.quote(p) for p in cmd))

        try:
            # create detached session with first command
            subprocess.run(["tmux", "new-session", "-s", session, "-d", ssh_cmds[0]])
            # create splits for the rest
            for cmd in ssh_cmds[1:]:
                subprocess.run(["tmux", "split-window", "-t", session, cmd])
            # arrange layout to tile evenly
            subprocess.run(["tmux", "select-layout", "-t", session, "tiled"])
            # attach session
            subprocess.run(["tmux", "attach-session", "-t", session])
        except Exception as e:
            print(f"Error creating tmux session: {e}")


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
