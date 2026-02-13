"""
Main entry point for sshmenuc application.
"""
from .core import ConnectionNavigator
from .utils import setup_argument_parser, setup_logging


def main():
    """Main application function.

    Parses command-line arguments, sets up logging,
    and launches the connection navigator.
    """
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    setup_logging(args.loglevel)
    
    navigator = ConnectionNavigator(args.config)
    navigator.navigate()


if __name__ == "__main__":
    main()