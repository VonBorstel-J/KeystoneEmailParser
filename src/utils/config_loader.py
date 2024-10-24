import os
import yaml
import logging
import torch
from jinja2 import Template
from typing import Any, Dict, Optional, List
from pathlib import Path

class ConfigLoader:
    _config: Dict[str, Any] = {}
    _is_loaded: bool = False
    _logger: Optional[logging.Logger] = None
    _project_root: Optional[Path] = None
    _templates: Dict[str, Template] = {}

    @classmethod
    def _get_project_root(cls) -> Path:
        """Get the project root directory."""
        if cls._project_root is None:
            cls._project_root = Path(__file__).parent.parent.parent.resolve()
        return cls._project_root

    @classmethod
    def setup_logging(cls) -> None:
        """Sets up logging based on configuration settings."""
        if not cls._logger:
            logging_config = {
                "level": "DEBUG",
                "file_path": "logs/parser.log",
                "handlers": ["StreamHandler", "FileHandler"],
                "create_logs_dir_if_not_exists": True
            }
            
            if "logging" in cls._config:
                logging_config.update(cls._config["logging"])

            try:
                log_path = Path(cls._get_project_root()) / logging_config["file_path"]
                if logging_config.get("create_logs_dir_if_not_exists", True):
                    log_path.parent.mkdir(parents=True, exist_ok=True)

                handlers = []
                if "StreamHandler" in logging_config.get("handlers", []):
                    handlers.append(logging.StreamHandler())
                if "FileHandler" in logging_config.get("handlers", []):
                    handlers.append(logging.FileHandler(str(log_path)))

                logging.basicConfig(
                    level=getattr(logging, logging_config.get("level", "DEBUG")),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=handlers,
                    force=True  # Force reconfiguration of the root logger
                )

                cls._logger = logging.getLogger("ConfigLoader")
                cls._logger.debug("Logging setup completed")

            except Exception as e:
                logging.basicConfig(
                    level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    force=True
                )
                cls._logger = logging.getLogger("ConfigLoader")
                cls._logger.error(f"Error setting up logging: {str(e)}", exc_info=True)

    @classmethod
    def _verify_configuration(cls) -> None:
        """Verifies that all required configuration sections and values are present."""
        try:
            # Check for required top-level sections
            required_sections = {
                "models": dict,
                "processing": dict,
                "logging": dict
            }

            for section, expected_type in required_sections.items():
                if section not in cls._config:
                    raise ValueError(f"Required configuration section '{section}' not found")
                if not isinstance(cls._config[section], expected_type):
                    raise ValueError(f"Configuration section '{section}' must be a {expected_type.__name__}")

            cls._logger.debug("Configuration verification completed successfully")

        except Exception as e:
            cls._logger.error(f"Configuration verification failed: {str(e)}")
            raise

    @classmethod
    def _validate_prompt_template(cls, model_name: str, template: str) -> None:
        """
        Validates that a prompt template contains required placeholders and syntax.
        
        Args:
            model_name: Name of the model the template is for
            template: The template string to validate
        """
        required_placeholders = {
            'ner': ['{email_content}'],
            'model_based_parsing': ['{email_content}'],
            'validation': ['{parsed_data}'],
            'summarization': ['{email_content}']
        }
        
        try:
            # Verify Jinja2 syntax
            Template(template)
            
            # Check required placeholders
            if model_name in required_placeholders:
                for placeholder in required_placeholders[model_name]:
                    if placeholder not in template:
                        raise ValueError(
                            f"Template for {model_name} missing required placeholder: {placeholder}"
                        )
                        
            cls._logger.debug(f"Template validation successful for {model_name}")
            
        except Exception as e:
            cls._logger.error(f"Template validation failed for {model_name}: {e}")
            raise ValueError(f"Invalid template for {model_name}: {str(e)}")

    @classmethod
    def load(cls, config_path: str = "config/parser_config.yaml") -> Dict[str, Any]:
        if not cls._is_loaded:
            try:
                # Convert to Path object and resolve absolute path
                config_path = Path(config_path)
                if not config_path.is_absolute():
                    config_path = cls._get_project_root() / config_path

                if not config_path.exists():
                    raise FileNotFoundError(f"Configuration file not found: {config_path}")

                # Load configuration
                with open(config_path, "r", encoding='utf-8') as file:
                    cls._config = yaml.safe_load(file) or {}

                # Setup logging first
                cls.setup_logging()
                cls._logger.debug(f"Loading configuration from {config_path}")

                # Verify configuration structure
                cls._verify_configuration()

                # Validate and compile templates
                for model_name, model_config in cls._config.get('models', {}).items():
                    if 'prompt_template' in model_config:
                        cls._validate_prompt_template(
                            model_name, 
                            model_config['prompt_template']
                        )
                        cls._templates[model_name] = Template(model_config['prompt_template'])

                # Process settings
                cls._process_device_settings()
                cls._verify_model_configs()

                cls._is_loaded = True
                cls._logger.info("Configuration loaded successfully")

            except Exception as e:
                if not cls._logger:
                    cls.setup_logging()
                cls._logger.error(f"Failed to load configuration: {str(e)}", exc_info=True)
                raise

        return cls._config

    @classmethod
    def _process_device_settings(cls) -> None:
        """Processes and validates device settings for all models."""
        try:
            global_device = cls._config.get("processing", {}).get("device", "auto")
            fallback_to_cpu = cls._config.get("processing", {}).get("fallback_to_cpu", True)

            # Determine actual device
            if global_device == "auto":
                global_device = "cuda" if torch.cuda.is_available() else "cpu"
                if global_device == "cpu" and not fallback_to_cpu:
                    raise ValueError("GPU not available and fallback_to_cpu is disabled")
                cls._logger.info(f"Auto-detected device: {global_device}")

            # Update model-specific device settings
            for model_name, model_config in cls._config.get("models", {}).items():
                if isinstance(model_config, dict):
                    if model_config.get("device", "auto") == "auto":
                        model_config["device"] = global_device
                    
                    if model_config.get("quantize", False) and model_config["device"] == "cpu":
                        cls._logger.warning(
                            f"Quantization enabled for {model_name} but running on CPU"
                        )

        except Exception as e:
            cls._logger.error(f"Error processing device settings: {str(e)}", exc_info=True)
            raise

    @classmethod
    def _verify_model_configs(cls) -> None:
        """Verifies specific model configurations."""
        models_config = cls._config.get("models", {})
        
        for model_name, config in models_config.items():
            if not isinstance(config, dict):
                continue

            # Handle max_length defaults
            if "max_length" not in config:
                config["max_length"] = cls._config.get("processing", {}).get("max_length", 1024)

            # Verify Mistral models
            if "mistral" in config.get("repo_id", "").lower():
                if config.get("max_length", 0) > 8192:
                    cls._logger.warning(
                        f"Max length for Mistral model {model_name} exceeds recommended limit"
                    )

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value using dot notation for nested keys."""
        if not cls._is_loaded:
            cls.load()
            
        try:
            value = cls._config
            for k in key.split('.'): 
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    @classmethod
    def get_model_config(cls, model_name: str) -> Dict[str, Any]:
        """Gets the configuration for a specific model."""
        if not cls._is_loaded:
            cls.load()
        
        models_config = cls._config.get("models", {})
        if model_name not in models_config:
            raise KeyError(f"Configuration for model '{model_name}' not found")
        
        return models_config[model_name]

    @classmethod
    def get_cache_dir(cls) -> str:
        """Gets the cache directory path."""
        if not cls._is_loaded:
            cls.load()
            
        cache_dir = cls._config.get("cache_dir", ".cache")
        if not os.path.isabs(cache_dir):
            cache_dir = str(cls._get_project_root() / cache_dir)
        
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
