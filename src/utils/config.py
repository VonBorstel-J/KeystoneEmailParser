# src/utils/config.py

import logging
from typing import Any, Dict

from src.utils.config_loader import ConfigLoader

class Config:
    """Configuration settings fetched from parser_config.yaml."""

    @classmethod
    def get_fuzzy_threshold(cls) -> int:
        return ConfigLoader.get("fuzzy_threshold", default=90)

    @classmethod
    def get_known_values(cls) -> Dict[str, Any]:
        return ConfigLoader.get("known_values", default={})

    @classmethod
    def get_date_formats(cls) -> list:
        return ConfigLoader.get("date_formats", default=[])

    @classmethod
    def get_boolean_values(cls) -> Dict[str, Any]:
        return ConfigLoader.get("boolean_values", default={})

    @classmethod
    def get_model_timeout(cls, model_name: str) -> int:
        """
        Retrieves the timeout for a specific model.

        Args:
            model_name (str): The name of the model (e.g., 'ner', 'donut').

        Returns:
            int: The timeout value in seconds.

        Raises:
            KeyError: If the model or timeout is not found in the configuration.
        """
        return ConfigLoader.get(f"models.{model_name}.timeout", required=True)

    @classmethod
    def get_model_config(cls, model_name: str) -> Dict[str, Any]:
        """
        Retrieves the entire configuration for a specific model.

        Args:
            model_name (str): The name of the model (e.g., 'ner', 'donut').

        Returns:
            Dict[str, Any]: The configuration dictionary for the model.

        Raises:
            KeyError: If the model configuration is not found.
        """
        return ConfigLoader.get(f"models.{model_name}", required=True)

    @classmethod
    def get_valid_extensions(cls) -> list:
        return ConfigLoader.get("valid_extensions", default=[])

    @classmethod
    def get_url_validation_setting(cls) -> Dict[str, bool]:
        return ConfigLoader.get("url_validation", default={})

    @classmethod
    def get_log_level(cls) -> str:
        return ConfigLoader.get("log_level", default="DEBUG")

    @classmethod
    def get_processing_config(cls) -> Dict[str, Any]:
        return ConfigLoader.get("processing", default={})

    @classmethod
    def load(cls, config_path: str = "config/parser_config.yaml") -> Dict[str, Any]:
        """
        Loads the configuration using ConfigLoader.

        Args:
            config_path (str): Path to the YAML configuration file.

        Returns:
            Dict[str, Any]: The loaded configuration dictionary.
        """
        return ConfigLoader.load_config(config_path)
