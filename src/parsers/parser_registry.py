# src/parsers/parser_registry.py

import logging
from typing import Optional, Dict

from flask_socketio import SocketIO
from transformers import Pipeline

from src.parsers.enhanced_parser import EnhancedParser  # Assuming this is still needed
from src.parsers.parser_options import ParserOption
from src.parsers.parser_init import (
    init_ner,
    init_donut,
    init_validation_model,
    init_summarization_model,
    setup_logging,
)
from src.utils.config import Config
from src.parsers.composite_parser import CompositeParser  # Import CompositeParser


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

    @staticmethod
    def get_parser(parser_option: ParserOption, socketio: SocketIO, sid: str) -> Optional[CompositeParser]:
        """
        Initialize and retrieve a parser based on the parser_option.

        Args:
            parser_option (ParserOption): The parser option identifier.
            socketio (SocketIO): The SocketIO instance for emitting events.
            sid (str): The session ID for the client.

        Returns:
            Optional[CompositeParser]: The initialized parser or None if initialization fails.
        """
        logger = setup_logging("ParserRegistry")
        config = Config.load()

        if parser_option == ParserOption.ENHANCED_PARSER:
            ner_pipeline = init_ner(logger, config)
            donut_processor, donut_model = init_donut(logger, config)
            validation_pipeline = init_validation_model(logger, config)
            summarization_pipeline = init_summarization_model(logger, config)

            # Check if all components initialized successfully
            if not all([ner_pipeline, donut_processor, donut_model, validation_pipeline, summarization_pipeline]):
                logger.error("One or more parser components failed to initialize.")
                return None

            # Initialize CompositeParser with all components
            composite_parser = CompositeParser(
                ner=ner_pipeline,
                donut_processor=donut_processor,
                donut_model=donut_model,
                validation=validation_pipeline,
                summarization=summarization_pipeline,
            )

            return composite_parser
        else:
            logger.error(f"Unknown parser option: {parser_option}")
            return None

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
