"""
Gestione del lancio delle connessioni SSH.
"""
import os
import re
import shlex
import shutil
import subprocess
import time
from typing import List, Dict, Any
import readchar
import logging
from clint.textui import puts, colored


class SSHLauncher:
    """Gestisce il lancio delle connessioni SSH."""
    
    def __init__(self, host: str, username: str, port: int = 22, identity_file: str = None):
        self.host = host
        self.username = username
        self.port = port
        self.identity_file = identity_file
    
    def _sanitize_session_name(self, raw: str) -> str:
        """Sanitizza il nome della sessione tmux."""
        return re.sub(r"[^A-Za-z0-9_-]+", "-", raw)
    
    def _list_tmux_sessions(self) -> List[str]:
        """Lista le sessioni tmux esistenti."""
        try:
            res = subprocess.run(["tmux", "ls"], capture_output=True, text=True)
            if res.returncode != 0:
                return []
            lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            sessions = []
            for line in lines:
                parts = line.split(":", 1)
                if parts:
                    sessions.append(parts[0])
            return sessions
        except Exception:
            return []
    
    def _build_ssh_command(self) -> List[str]:
        """Costruisce il comando SSH."""
        ssh_command = ["ssh"]
        if self.identity_file:
            ssh_command.extend(["-i", self.identity_file])
        ssh_command.extend([f"{self.username}@{self.host}", "-p", str(self.port)])
        return ssh_command
    
    def _handle_existing_sessions(self, sanitized_host: str) -> bool:
        """Gestisce le sessioni tmux esistenti. Ritorna True se si attacca a una esistente."""
        existing = self._list_tmux_sessions()
        matches = [s for s in existing if s.startswith(f"{sanitized_host}-")]
        
        if not matches:
            return False
        
        if len(matches) == 1:
            choice = input(f"Found tmux session '{matches[0]}'. Attach (a) or create new (n)? [a/n]: ").strip().lower()
            if choice == "a" or choice == "":
                tmux_cmd = ["tmux", "attach-session", "-t", matches[0]]
                subprocess.run(tmux_cmd)
                return True
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
                    return True
        
        return False
    
    def _create_new_tmux_session(self, ssh_command: List[str]):
        """Crea una nuova sessione tmux."""
        session_raw = f"{self.host}-{int(time.time())}"
        session = self._sanitize_session_name(session_raw)
        ssh_cmd_str = " ".join(shlex.quote(p) for p in ssh_command)
        tmux_cmd = ["tmux", "new-session", "-s", session, ssh_cmd_str]
        subprocess.run(tmux_cmd)
    
    def launch(self):
        """Lancia la connessione SSH."""
        ssh_command = self._build_ssh_command()
        
        try:
            if shutil.which("tmux"):
                sanitized_host = self._sanitize_session_name(self.host)
                
                # Prova ad attaccarsi a sessioni esistenti
                if self._handle_existing_sessions(sanitized_host):
                    return
                
                # Crea nuova sessione
                self._create_new_tmux_session(ssh_command)
            else:
                # Fallback: esegui SSH direttamente
                subprocess.run(ssh_command)
            
            if logging.getLogger().level == logging.DEBUG:
                readchar.readkey()
        except Exception as e:
            print(f"Error launching SSH client: {e}")
    
    @staticmethod
    def launch_group(host_entries: List[Dict[str, Any]]):
        """Lancia connessioni multiple in una sessione tmux con split panes."""
        if not shutil.which("tmux"):
            puts(colored.red("tmux not found; cannot open grouped session"))
            return
        
        if not host_entries:
            puts(colored.red("No hosts provided"))
            return
        
        # Limita a massimo 6 panes
        if len(host_entries) > 6:
            puts(colored.yellow("Maximum 6 hosts supported; truncating list"))
            host_entries = host_entries[:6]
        
        # Nome sessione basato sul primo host + timestamp
        session_raw = f"{host_entries[0]['host']}-{int(time.time())}"
        session = re.sub(r"[^A-Za-z0-9_-]+", "-", session_raw)
        
        # Costruisci comandi SSH
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
            # Crea sessione detached con primo comando
            subprocess.run(["tmux", "new-session", "-s", session, "-d", ssh_cmds[0]])
            # Crea split per gli altri
            for cmd in ssh_cmds[1:]:
                subprocess.run(["tmux", "split-window", "-t", session, cmd])
            # Organizza layout
            subprocess.run(["tmux", "select-layout", "-t", session, "tiled"])
            # Attacca sessione
            subprocess.run(["tmux", "attach-session", "-t", session])
        except Exception as e:
            print(f"Error creating tmux session: {e}")