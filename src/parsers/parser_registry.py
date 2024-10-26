# src/parsers/parser_registry.py

import logging
from typing import Optional, Any, Dict

from flask_socketio import SocketIO

from src.parsers.enhanced_parser import EnhancedParser
from src.parsers.parser_options import ParserOption
from src.utils.config import Config


class ParserRegistry:
    """Registry for managing parser instances."""

    _logger = logging.getLogger(__name__)

    @classmethod
    def initialize_parsers(cls) -> None:
        """Initialize parsers with configuration."""
        pass  # Parsers are initialized per request

    @classmethod
    def get_parser(
        cls,
        parser_option: ParserOption,
        socketio: Optional[SocketIO] = None,
        sid: Optional[str] = None,
    ) -> Optional[Any]:
        """Get a parser instance based on input type with optional Socket.IO configuration."""
        if parser_option == ParserOption.ENHANCED_PARSER:
            parser = EnhancedParser(
                config=Config.get_full_config(),
                socketio=socketio,
                sid=sid,
            )
            return parser
        cls._logger.warning(f"No parser found for option: {parser_option}")
        return None

    @classmethod
    def cleanup_parsers(cls) -> None:
        """Clean up parser resources."""
        # Since parsers are instantiated per request, no persistent parsers to clean up
        pass

    @classmethod
    def health_check(cls) -> Dict[str, bool]:
        """Check health status of parsers."""
        # Implement if there are persistent parsers
        return {}
