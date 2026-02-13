"""
User interface rendering management.
"""
import os
import logging
from typing import List, Dict, Any, Union
from .colors import Colors


class MenuDisplay:
    """Manages menu display and rendering."""
    
    def __init__(self):
        self.colors = Colors()
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system("cls" if os.name == "nt" else "clear")
    
    def print_instructions(self):
        """Print usage instructions."""
        print("Navigate: ↑↓  Select: SPACE  Connect: ENTER  |  Edit: [a]dd [e]dit [d]elete [r]ename  |  Quit: q")
    
    def print_header(self, headers: List[str]):
        """Print table header.

        Args:
            headers: List of header column names
        """
        tbl = "+--------+------------------------------------+"
        print(f"{self.colors.OKCYAN}{tbl}{self.colors.ENDC}")
        print(
            f"{self.colors.OKCYAN}|{self.colors.ENDC}{self.colors.HEADER}{'#':>7} {self.colors.ENDC}"
            f"{self.colors.OKCYAN}|{self.colors.ENDC}{self.colors.HEADER}{headers[0]:^35} {self.colors.ENDC}"
            f"{self.colors.OKCYAN}|{self.colors.ENDC}"
        )
        print(f"{self.colors.OKCYAN}{tbl}{self.colors.ENDC}")
    
    def print_row(self, infos: tuple, is_selected: bool, is_host: bool, is_marked: bool = False):
        """Print a table row.

        Args:
            infos: Tuple of (index, data) for the row
            is_selected: Whether this row is currently selected
            is_host: Whether this row represents a host entry
            is_marked: Whether this row is marked for multi-selection
        """
        idx_display = ""
        title = ""
        
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
        
        if is_selected:
            row = (
                f"{self.colors.OKCYAN}|{self.colors.ENDC}{self.colors.OKGREEN}{idx_display} {self.colors.ENDC}"
                f"{self.colors.OKCYAN}|{self.colors.ENDC}{self.colors.OKGREEN} {marker} {title:<31}{self.colors.ENDC}"
                f"{self.colors.OKCYAN}|{self.colors.ENDC}"
            )
        else:
            row = (
                f"{self.colors.OKCYAN}|{self.colors.ENDC}{idx_display} {self.colors.OKCYAN}|{self.colors.ENDC}"
                f" {marker} {title:<31}{self.colors.OKCYAN}|{self.colors.ENDC}"
            )
        
        print(row)
    
    def print_footer(self):
        """Print table footer."""
        print(f"{self.colors.OKCYAN}+--------+------------------------------------+{self.colors.ENDC}")
    
    def print_table(self, data: Union[Dict[str, Any], List[Any]], selected_target: int, 
                   marked_indices: set, level: int):
        """Print complete table with data.

        Args:
            data: Dictionary or list of items to display
            selected_target: Index of currently selected item
            marked_indices: Set of indices marked for multi-selection
            level: Current navigation depth level
        """
        self.print_header(["Description"])
        
        if isinstance(data, dict):
            keys = list(data.keys())
            for idx, key in enumerate(keys):
                marked = idx in marked_indices
                is_selected = idx == selected_target
                self.print_row([idx, key], is_selected, is_host=False, is_marked=marked)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                marked = i in marked_indices
                if isinstance(item, dict) and ("friendly" in item or "host" in item):
                    self.print_row([i, item], i == selected_target, is_host=True, is_marked=marked)
                else:
                    key = list(item.keys())[0] if isinstance(item, dict) and item else str(item)
                    self.print_row([i, key], i == selected_target, is_host=False, is_marked=marked)
        
        self.print_footer()