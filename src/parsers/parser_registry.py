# src/parsers/parser_registry.py

import logging
from typing import Dict, Any, Optional
from flask_socketio import SocketIO

from src.parsers.enhanced_parser import EnhancedParser
from src.parsers.parser_options import ParserOption
from src.utils.config import Config


class ParserRegistry:
    """
    Registry for managing parser instances and their lifecycle.
    """

    _parsers: Dict[ParserOption, Any] = {}
    _logger = logging.getLogger(__name__)

    @classmethod
    def initialize_parsers(cls, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize all parsers with configuration.

        Args:
            config (Optional[Dict[str, Any]]): Configuration dictionary.
        """
        try:
            # Initialize configuration if not provided
            if config is None:
                Config.initialize()
                config = Config._config  # Get the full config

            # Set up logging based on configuration
            logging_config = config.get("logging", {})
            cls._logger.setLevel(logging_config.get("level", "DEBUG"))

            cls._logger.info("Initializing parsers with configuration.")

            # Initialize enhanced parser with full configuration
            cls._parsers[ParserOption.ENHANCED_PARSER] = EnhancedParser(config=config)

            cls._logger.info("Parser initialization completed successfully.")
        except Exception as e:
            cls._logger.error(f"Failed to initialize parsers: {e}", exc_info=True)
            raise

    @classmethod
    def get_parser(
        cls,
        parser_option: ParserOption,
        socketio: Optional[SocketIO] = None,
        sid: Optional[str] = None,
    ) -> Any:
        """
        Get a parser instance with optional Socket.IO configuration.

        Args:
            parser_option (ParserOption): The type of parser to retrieve.
            socketio (Optional[SocketIO]): Socket.IO instance for real-time updates.
            sid (Optional[str]): Socket.IO session ID.

        Returns:
            Any: The requested parser instance.
        """
        try:
            parser = cls._parsers.get(parser_option)
            if parser:
                parser.socketio = socketio
                parser.sid = sid
                cls._logger.debug(f"Retrieved parser for option: {parser_option}")
                return parser
            else:
                cls._logger.warning(f"No parser found for option: {parser_option}")
                return None
        except Exception as e:
            cls._logger.error(f"Error retrieving parser: {e}", exc_info=True)
            return None

    @classmethod
    def cleanup_parsers(cls) -> None:
        """
        Clean up all parser instances and free resources.
        """
        cls._logger.info("Starting parser cleanup.")
        try:
            for parser_type, parser in cls._parsers.items():
                try:
                    if hasattr(parser, "cleanup_resources"):
                        parser.cleanup_resources()
                    elif hasattr(parser, "cleanup"):
                        parser.cleanup()
                    cls._logger.debug(f"Cleaned up parser: {parser_type}")
                except Exception as e:
                    cls._logger.error(
                        f"Error cleaning up parser {parser_type}: {e}", exc_info=True
                    )
            cls._parsers.clear()
            cls._logger.info("Parser cleanup completed.")
        except Exception as e:
            cls._logger.error(f"Error during parser cleanup: {e}", exc_info=True)

    @classmethod
    def health_check(cls) -> Dict[str, bool]:
        """
        Check the health status of all registered parsers.

        Returns:
            Dict[str, bool]: Health status for each parser.
        """
        cls._logger.debug("Performing health check on all parsers.")
        health_status = {}
        try:
            for parser_type, parser in cls._parsers.items():
                try:
                    is_healthy = (
                        parser.health_check()
                        if hasattr(parser, "health_check")
                        else False
                    )
                    health_status[str(parser_type)] = is_healthy
                    cls._logger.debug(
                        f"Health check for {parser_type}: {'Healthy' if is_healthy else 'Unhealthy'}"
                    )
                except Exception as e:
                    cls._logger.error(
                        f"Error checking health for parser {parser_type}: {e}",
                        exc_info=True,
                    )
                    health_status[str(parser_type)] = False
            return health_status
        except Exception as e:
            cls._logger.error(f"Error during health check: {e}", exc_info=True)
            return {str(parser_type): False for parser_type in cls._parsers}
