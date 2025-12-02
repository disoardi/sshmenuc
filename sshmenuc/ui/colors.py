"""
Definizioni dei colori per l'interfaccia utente.
"""


class Colors:
    """Classe per la gestione dei colori del terminale."""
    
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
        """Applica un colore al testo."""
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