# src/utils/config_loader.py

import os
import yaml
import logging
from typing import Any, Dict

class ConfigLoader:
    _config: Dict[str, Any] = {}
    _is_loaded: bool = False

    @classmethod
    def load_config(cls, config_path: str = "config/parser_config.yaml") -> Dict[str, Any]:
        """
        Loads the configuration from the specified YAML file.
        Implements a singleton pattern to load the config only once.

        Args:
            config_path (str): Path to the YAML configuration file.

        Returns:
            Dict[str, Any]: The loaded configuration dictionary.
        """
        if not cls._is_loaded:
            logger = logging.getLogger("ConfigLoader")
            try:
                # Resolve absolute path if config_path is relative
                if not os.path.isabs(config_path):
                    project_root = os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    )
                    config_path = os.path.join(project_root, config_path)
                
                logger.debug(f"Loading configuration from {config_path}")
                with open(config_path, "r") as file:
                    cls._config = yaml.safe_load(file) or {}
                cls._is_loaded = True
                logger.info("Configuration loaded successfully.")
            except FileNotFoundError:
                logger.error(f"Configuration file not found at {config_path}.", exc_info=True)
                raise
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML configuration: {e}", exc_info=True)
                raise
            except Exception as e:
                logger.error(f"Failed to load configuration: {e}", exc_info=True)
                raise
        return cls._config

    @classmethod
    def get(cls, key: str, default: Any = None, required: bool = False) -> Any:
        """
        Retrieves a configuration value using dot notation for nested keys.

        Args:
            key (str): The configuration key, using dot notation for nested keys.
            default (Any): The default value to return if the key is not found.
            required (bool): If True, raises a KeyError if the key is not found.

        Returns:
            Any: The configuration value.

        Raises:
            KeyError: If the key is not found and required is True.
        """
        keys = key.split('.')
        value = cls._config
        try:
            for k in keys:
                value = value[k]
            return value
        except KeyError:
            if required:
                raise KeyError(f"Configuration key '{key}' not found.")
            return default
