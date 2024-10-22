# src/parsers/parser_registry.py

from src.parsers.enhanced_parser import EnhancedParser
from src.parsers.parser_options import ParserOption
from typing import Dict, Optional

class ParserRegistry:
    _parsers = {}

    @classmethod
    def register_parser(cls, option: ParserOption, parser_class):
        """
        Register a parser class with a specific parser option.

        Args:
            option (ParserOption): The parser option identifier.
            parser_class: The parser class to register.
        """
        cls._parsers[option] = parser_class

    @classmethod
    def get_parser(cls, option: ParserOption, socketio, sid) -> EnhancedParser:
        """
        Instantiate and retrieve a parser instance for a given option.

        Args:
            option (ParserOption): The parser option identifier.
            socketio: The SocketIO instance for emitting events.
            sid: The session ID of the connected client.

        Returns:
            EnhancedParser: An instance of the requested parser.
        
        Raises:
            ValueError: If no parser is registered for the given option.
        """
        parser_class = cls._parsers.get(option)
        if not parser_class:
            raise ValueError(f"No parser registered for option: {option}")
        return parser_class(socketio, sid)

    @classmethod
    def health_check(cls) -> Dict[str, bool]:
        """
        Perform health checks on all registered parsers.

        Returns:
            Dict[str, bool]: A dictionary mapping parser options to their health status.
        """
        health_status = {}
        for option, parser_class in cls._parsers.items():
            try:
                # Instantiate a temporary parser without SocketIO and sid for health checks
                parser_instance = parser_class(socketio=None, sid=None)
                health_status[str(option)] = parser_instance.health_check()
            except Exception as e:
                # If instantiation fails, mark the parser as unhealthy
                health_status[str(option)] = False
        return health_status

# Initialize and register EnhancedParser
ParserRegistry.register_parser(ParserOption.ENHANCED_PARSER, EnhancedParser)
