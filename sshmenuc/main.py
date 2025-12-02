"""
Entry point principale per sshmenuc.
"""
from .core import ConnectionNavigator
from .utils import setup_argument_parser, setup_logging


def main():
    """Funzione principale dell'applicazione."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    setup_logging(args.loglevel)
    
    navigator = ConnectionNavigator(args.config)
    navigator.navigate()


if __name__ == "__main__":
    main()