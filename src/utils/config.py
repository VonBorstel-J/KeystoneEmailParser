# src/utils/config.py

import logging
import torch
from typing import Any, Dict, List, Optional, Union

from src.utils.config_loader import ConfigLoader


class Config:
    """
    Configuration utility class providing easy access to parser configuration settings.
    Interfaces with ConfigLoader to provide a clean API for accessing configuration values.
    """

    @classmethod
    def initialize(cls, config_path: Optional[str] = None) -> None:
        """
        Initializes the configuration system.

        Args:
            config_path (Optional[str]): Optional path to configuration file.
        """
        if config_path:
            ConfigLoader.load(config_path)
        else:
            ConfigLoader.load()

    @classmethod
    def get_model_config(cls, model_name: str) -> Dict[str, Any]:
        """
        Gets the complete configuration for a specific model.

        Args:
            model_name (str): Name of the model (e.g., 'ner', 'donut').

        Returns:
            Dict[str, Any]: Complete model configuration.
        """
        return ConfigLoader.get_model_config(model_name)

    @classmethod
    def get_device(cls, model_name: Optional[str] = None) -> str:
        """
        Gets the appropriate device for a model or globally.

        Args:
            model_name (Optional[str]): Model name to get specific device for.

        Returns:
            str: Device to use ('cuda' or 'cpu').
        """
        if model_name:
            device = ConfigLoader.get(f"models.{model_name}.device", "auto")
        else:
            device = ConfigLoader.get("processing.device", "auto")

        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device

    @classmethod
    def should_quantize(cls, model_name: str) -> bool:
        """
        Checks if a model should use quantization.

        Args:
            model_name (str): Name of the model.

        Returns:
            bool: True if quantization should be used.
        """
        return ConfigLoader.get(f"models.{model_name}.quantize", False)

    @classmethod
    def get_cache_dir(cls) -> str:
        """
        Gets the cache directory path.

        Returns:
            str: Absolute path to cache directory.
        """
        return ConfigLoader.get_cache_dir()

    @classmethod
    def get_hf_token(cls) -> Optional[str]:
        """
        Gets the Hugging Face token from environment variable.

        Returns:
            Optional[str]: The token if available.
        """
        import os
        env_var = ConfigLoader.get("authentication.hf_token_env_var", "HF_TOKEN")
        return os.getenv(env_var)

    @classmethod
    def get_processing_config(cls) -> Dict[str, Any]:
        """
        Gets all processing-related configuration.

        Returns:
            Dict[str, Any]: Processing configuration.
        """
        return ConfigLoader.get("processing", {})

    @classmethod
    def get_batch_size(cls, model_name: Optional[str] = None) -> int:
        """
        Gets batch size for a specific model or global default.

        Args:
            model_name (Optional[str]): Model name for specific batch size.

        Returns:
            int: Batch size to use.
        """
        if model_name:
            return ConfigLoader.get(
                f"models.{model_name}.batch_size",
                ConfigLoader.get("processing.batch_size", 1)
            )
        return ConfigLoader.get("processing.batch_size", 1)

    @classmethod
    def get_max_length(cls, model_name: Optional[str] = None) -> int:
        """
        Gets max length for a specific model or global default.

        Args:
            model_name (Optional[str]): Model name for specific max length.

        Returns:
            int: Max length to use.
        """
        if model_name:
            return ConfigLoader.get(
                f"models.{model_name}.max_length",
                ConfigLoader.get("processing.max_length", 512)
            )
        return ConfigLoader.get("processing.max_length", 512)

    @classmethod
    def get_timeout(cls, model_name: str) -> int:
        """
        Gets timeout value for a specific model.

        Args:
            model_name (str): Name of the model.

        Returns:
            int: Timeout in seconds.
        """
        return ConfigLoader.get(f"models.{model_name}.timeout", 30)

    @classmethod
    def get_known_values(cls) -> Dict[str, List[str]]:
        """
        Gets dictionary of known values for entity matching.

        Returns:
            Dict[str, List[str]]: Known values by category.
        """
        return ConfigLoader.get("known_values", {})

    @classmethod
    def get_date_formats(cls) -> List[str]:
        """
        Gets list of supported date formats.

        Returns:
            List[str]: Supported date format strings.
        """
        return ConfigLoader.get("date_formats", [])

    @classmethod
    def get_boolean_values(cls) -> Dict[str, List[str]]:
        """
        Gets mappings for boolean value recognition.

        Returns:
            Dict[str, List[str]]: Boolean value mappings.
        """
        return ConfigLoader.get("boolean_values", {})

    @classmethod
    def get_valid_extensions(cls) -> List[str]:
        """
        Gets list of valid file extensions.

        Returns:
            List[str]: Valid file extensions.
        """
        return ConfigLoader.get("valid_extensions", [])

    @classmethod
    def get_fuzzy_threshold(cls) -> int:
        """
        Gets fuzzy matching threshold.

        Returns:
            int: Threshold value for fuzzy matching.
        """
        return ConfigLoader.get("fuzzy_threshold", 90)

    @classmethod
    def is_amp_enabled(cls) -> bool:
        """
        Checks if Automatic Mixed Precision is enabled.

        Returns:
            bool: True if AMP is enabled.
        """
        return ConfigLoader.get("enable_amp", False)

    @classmethod
    def should_optimize_memory(cls) -> bool:
        """
        Checks if memory optimization is enabled.

        Returns:
            bool: True if memory optimization is enabled.
        """
        return ConfigLoader.get("optimize_memory", False)

    @classmethod
    def get_logging_config(cls) -> Dict[str, Any]:
        """
        Gets complete logging configuration.

        Returns:
            Dict[str, Any]: Logging configuration.
        """
        return ConfigLoader.get("logging", {})

    @classmethod
    def get_log_level(cls) -> str:
        """
        Gets configured logging level.

        Returns:
            str: Logging level.
        """
        return ConfigLoader.get("logging.level", "DEBUG")

    @classmethod
    def should_fallback_to_cpu(cls) -> bool:
        """
        Checks if CPU fallback is enabled.

        Returns:
            bool: True if CPU fallback is enabled.
        """
        return ConfigLoader.get("processing.fallback_to_cpu", True)
