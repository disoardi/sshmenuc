"""
Color definitions for the user interface.
"""


class Colors:
    """Terminal color management class with ANSI escape sequences."""
    
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    
    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Apply a color to text.

        Args:
            text: Text to colorize
            color: ANSI color code

        Returns:
            Colored text string
        """
        return f"{color}{text}{cls.ENDC}"
    
    @classmethod
    def header(cls, text: str) -> str:
        return cls.colorize(text, cls.HEADER)
    
    @classmethod
    def success(cls, text: str) -> str:
        return cls.colorize(text, cls.OKGREEN)
    
    @classmethod
    def warning(cls, text: str) -> str:
        return cls.colorize(text, cls.WARNING)
    
    @classmethod
    def error(cls, text: str) -> str:
        return cls.colorize(text, cls.FAIL)