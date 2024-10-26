# config.py

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

import torch 
import pipeline


class ConfigurationError(Exception):
    """Base exception for configuration errors."""
    pass


class Config:
    """Simplified configuration management for the parser system."""

    _config: Dict[str, Any] = {}
    _is_initialized: bool = False

    @classmethod
    def initialize(cls, config_path: Optional[str] = None) -> None:
        """Initialize configuration from a YAML file."""
        if cls._is_initialized:
            return

        try:
            # Use the provided path if it exists, else use the default path
            if not config_path:
                config_path = Path(__file__).parent.parent / "config" / "parser_config.yaml"

            # Log the config path to ensure correctness
            logging.debug(f"Loading config from: {config_path}")

            with open(config_path, 'r') as f:
                cls._config = yaml.safe_load(f) or {}

            # Log the loaded configuration for debugging
            logging.debug(f"Loaded configuration: {cls._config}")

            cls._is_initialized = True
            logging.info("Configuration initialized successfully")

        except FileNotFoundError:
            logging.error(f"Configuration file not found at: {config_path}")
            raise ConfigurationError(f"Configuration file not found at: {config_path}")
        except yaml.YAMLError as e:
            logging.error(f"Error parsing YAML file: {e}")
            raise ConfigurationError(f"Error parsing YAML file: {e}")
        except Exception as e:
            logging.error(f"Unexpected error during configuration initialization: {e}")
            raise ConfigurationError(f"Unexpected error during configuration initialization: {e}") from e

    @classmethod
    def get_full_config(cls) -> Dict[str, Any]:
        """Retrieve the full configuration."""
        if not cls._is_initialized:
            cls.initialize()
        logging.debug(f"Full config loaded: {cls._config}")
        return cls._config

    @classmethod
    def get_processing_config(cls) -> Dict[str, Any]:
        """Retrieve the processing section of the configuration."""
        return cls.get_full_config().get("processing", {})

    @classmethod
    def get_model_config(cls, model_name: str) -> Dict[str, Any]:
        """Retrieve the configuration for a specific model."""
        models = cls.get_full_config().get("models", {})
        if model_name not in models:
            raise ConfigurationError(f"Configuration for model '{model_name}' not found")
        return models[model_name]

    @classmethod
    def get_logging_config(cls) -> Dict[str, Any]:
        """Retrieve the logging configuration."""
        return cls.get_full_config().get("logging", {})

    @classmethod
    def get_cache_dir(cls) -> str:
        """Retrieve the cache directory from the configuration."""
        return cls.get_full_config().get("cache_dir", ".cache")

    @classmethod
    def should_fallback_to_cpu(cls) -> bool:
        """Determine if fallback to CPU is enabled."""
        return cls.get_processing_config().get("fallback_to_cpu", True)

    @classmethod
    def is_amp_enabled(cls) -> bool:
        """Check if Automatic Mixed Precision (AMP) is enabled."""
        return cls.get_processing_config().get("enable_amp", False)

    @classmethod
    def should_optimize_memory(cls) -> bool:
        """Check if memory optimization is enabled."""
        return cls.get_processing_config().get("optimize_memory", True)

    @classmethod
    def get_enabled_stages(cls) -> List[str]:
        """Get list of enabled parsing stages."""
        stages = cls.get_full_config().get("stages", {})
        return [
            stage_name
            for stage_name, config in stages.items()
            if config.get("enabled", True)
        ]

    @classmethod
    def get_stage_config(cls, stage_name: str) -> Dict[str, Any]:
        """Get configuration for a specific stage."""
        stages = cls.get_full_config().get("stages", {})
        if stage_name not in stages:
            raise ConfigurationError(f"Configuration for stage '{stage_name}' not found")
        return stages[stage_name]

    @classmethod
    def get_error_handling_config(cls) -> Dict[str, Any]:
        """Get error handling configuration."""
        return cls.get_full_config().get("error_handling", {})

    @classmethod
    def initialize_model(cls, model_name: str) -> Any:
        """Initialize a model with appropriate configuration."""
        model_config = cls.get_model_config(model_name)
        device = cls.get_device(model_name)

        try:
            # Initialize model with configuration
            model_kwargs = {
                "device_map": "auto" if device == "cuda" else None,
                "torch_dtype": torch.float16 if device == "cuda" else torch.float32,
                "cache_dir": cls.get_cache_dir(),
            }

            model = pipeline(
                task=model_config.get("task", "text-generation"),
                model=model_config["repo_id"],
                tokenizer=model_config["repo_id"],
                **model_kwargs,
            )

            logging.info(f"Successfully initialized model {model_name} on {device}")
            return model

        except Exception as e:
            raise ConfigurationError(f"Failed to initialize model {model_name}: {str(e)}")

    @classmethod
    def get_device(cls, model_name: Optional[str] = None) -> str:
        """Get appropriate device for model or global setting."""
        if model_name:
            device = cls.get_model_config(model_name).get("device", "auto")
        else:
            device = cls.get_processing_config().get("device", "auto")

        # Handle 'auto' device setting
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        return device

    @classmethod
    def get_valid_extensions(cls) -> List[str]:
        """Retrieve valid file extensions from the configuration."""
        return cls.get_full_config().get("valid_extensions", [".pdf", ".jpg", ".png"])

    @classmethod
    def get_data_points(cls) -> Dict[str, Any]:
        """Retrieve data points from the configuration."""
        return cls.get_full_config().get("data_points", {})

    @classmethod
    def should_validate_schema(cls) -> bool:
        """Check if schema validation is enabled."""
        schema_config = cls.get_full_config().get("schema", {})
        return schema_config.get("validate_input", True) or schema_config.get(
            "validate_output", True
        )
