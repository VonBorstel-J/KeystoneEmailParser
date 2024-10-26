import os
import yaml
import json
import logging
import torch
import time
import threading
import gzip
import copy
import io
from jinja2 import Template
from typing import Any, Dict, Optional, List, Union, Callable
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from cachetools import LRUCache, cached, keys

from src.utils.exceptions import (
    ConfigurationErrorFactory,
    ErrorAggregator,
    ErrorReporter,
    LoadError,
    ValidationError,
)
from src.utils.schema_validator import SchemaValidator

logger = logging.getLogger("ConfigLoader")
logger.setLevel(logging.DEBUG)


class ConfigLoader:
    _config: Dict[str, Any] = {}
    _is_loaded: bool = False
    _logger: Optional[logging.Logger] = logger
    _project_root: Optional[Path] = None
    _templates: Dict[str, Template] = {}
    _lock = threading.Lock()
    _cache: LRUCache = LRUCache(maxsize=128)
    _cache_stats: Dict[str, int] = {"hits": 0, "misses": 0}

    _config_observers: List[Callable[[Dict[str, Any]], None]] = []
    _file_observer: Optional[Observer] = None

    _schema_validator: Optional[SchemaValidator] = None

    _snapshot_compression = True  # Toggle for snapshot compression
    _snapshots: List[Union[Dict[str, Any], bytes]] = []
    _snapshot_lock = threading.Lock()
    _version: int = 0
    _observers: Optional[Any] = None  # Initialize properly as needed

    @classmethod
    def _get_project_root(cls) -> Path:
        """Get the project root directory."""
        if cls._project_root is None:
            cls._project_root = Path(__file__).parent.parent.parent.resolve()
        return cls._project_root

    @classmethod
    def setup_logging(cls) -> None:
        """Sets up logging based on configuration settings."""
        # Logging is already set up in exceptions.py and elsewhere

    @classmethod
    def _load_file(cls, config_path: Path) -> Dict[str, Any]:
        """Loads configuration from a file with support for YAML, JSON, and ENV formats."""
        try:
            if config_path.suffix in [".yaml", ".yml"]:
                with cls._atomic_read(config_path) as file:
                    return yaml.safe_load(file) or {}
            elif config_path.suffix == ".json":
                with cls._atomic_read(config_path) as file:
                    return json.load(file)
            elif config_path.suffix == ".env":
                return cls._load_env(config_path)
            else:
                raise LoadError(
                    f"Unsupported configuration file format: {config_path.suffix}",
                    {"file_path": str(config_path)},
                )
        except Exception as e:
            raise LoadError(
                f"Error loading configuration file: {e}",
                {"file_path": str(config_path)},
            ) from e

    @classmethod
    def _load_env(cls, config_path: Path) -> Dict[str, Any]:
        """Loads configuration from an environment file."""
        config = {}
        try:
            with cls._atomic_read(config_path) as file:
                for line in file:
                    if line.strip() and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        config[key] = value
            return config
        except Exception as e:
            raise LoadError(
                f"Error loading ENV configuration: {e}", {"file_path": str(config_path)}
            ) from e

    @classmethod
    def _atomic_read(cls, path: Path):
        """Reads a file atomically."""
        try:
            with open(path, "rb") as f:
                content = f.read()
            try:
                decompressed = gzip.decompress(content).decode("utf-8")
                logger.debug("Decompressed configuration file: %s", path)
                return io.StringIO(decompressed)
            except gzip.BadGzipFile:
                logger.debug("Reading uncompressed configuration file: %s", path)
                return open(path, "r", encoding="utf-8")
        except OSError as e:
            raise LoadError(f"Error reading file {path}: {e}", {"file_path": str(path)}) from e

    @classmethod
    def setup_file_watcher(cls, config_path: Path) -> None:
        """Sets up a file watcher to detect changes in the configuration file with debouncing and batching."""
        if cls._file_observer is not None:
            logger.debug("File watcher already set up.")
            return

        event_handler = cls._ConfigFileChangeHandler(config_path)
        cls._file_observer = Observer()
        cls._file_observer.schedule(
            event_handler, path=str(config_path.parent), recursive=False
        )
        cls._file_observer.start()
        logger.debug("Started file watcher for %s", config_path)

    class _ConfigFileChangeHandler(FileSystemEventHandler):
        def __init__(self, config_path: Path):
            self.config_path = config_path
            self._last_modified = time.time()
            self._debounce_delay = 1.0  # seconds
            self._lock = threading.Lock()

        def on_modified(self, event):
            if Path(event.src_path) != self.config_path:
                return
            with self._lock:
                current_time = time.time()
                if current_time - self._last_modified < self._debounce_delay:
                    logger.debug(
                        "Modification detected but within debounce delay. Ignoring."
                    )
                    return
                self._last_modified = current_time
            logger.info("Configuration file %s modified. Reloading...", self.config_path)
            try:
                cls = ConfigLoader
                cls.load()
                for observer in cls._config_observers:
                    observer(cls._config)
                logger.info("Configuration reloaded successfully after file change.")
            except LoadError as e:
                logger.error("Failed to reload configuration: %s", e)
            except ValidationError as ve:
                logger.error("Validation failed after reload: %s", ve)

    @classmethod
    def register_observer(cls, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Registers a callback to be called when the configuration changes."""
        cls._config_observers.append(callback)
        logger.debug("Observer %s registered.", callback.__name__)

    @classmethod
    def _verify_configuration(cls) -> None:
        """Verifies that all required configuration sections and values are present."""
        aggregator = ErrorAggregator()
        try:
            # Check for required top-level sections
            required_sections = {"models": dict, "processing": dict, "logging": dict}

            for section, expected_type in required_sections.items():
                if section not in cls._config:
                    error = ConfigurationErrorFactory.create_missing_config_error(
                        f"Required configuration section '{section}' not found",
                        {"section": section},
                    )
                    aggregator.add_error(error)
                elif not isinstance(cls._config[section], expected_type):
                    error = ConfigurationErrorFactory.create_type_mismatch_error(
                        f"Configuration section '{section}' must be a {expected_type.__name__}",
                        {"section": section, "expected_type": expected_type.__name__},
                    )
                    aggregator.add_error(error)

            # Check if quantization is enabled on CPU and disable it
            processing_device = cls._config.get("processing", {}).get("device", "auto")
            if processing_device == "cpu":
                for model_name, model_config in cls._config.get("models", {}).items():
                    if model_config.get("quantize", False):
                        logger.warning(
                            "Quantization enabled for %s but running on CPU. Disabling quantization.",
                            model_name,
                        )
                        cls._config["models"][model_name]["quantize"] = False

            if aggregator.has_errors():
                raise aggregator

            logger.debug("Configuration verification completed successfully.")

        except ErrorAggregator as aggregator:
            logger.error("Configuration verification failed.")
            ErrorReporter.report_errors(aggregator)
            raise

    @classmethod
    def _validate_schema(cls) -> None:
        """Validates the configuration against a predefined schema."""
        if cls._schema_validator:
            try:
                cls._schema_validator.validate(cls._config)
                logger.debug("Schema validation passed.")
            except ErrorAggregator as aggregator:
                logger.error("Schema validation failed.")
                ErrorReporter.report_errors(aggregator)
                raise
        else:
            logger.warning(
                "No schema validator configured. Skipping schema validation."
            )

    @classmethod
    def _process_device_settings(cls) -> None:
        """Processes and validates device settings for all models."""
        try:
            global_device = cls._config.get("processing", {}).get("device", "auto")

            # Determine actual device
            if global_device == "auto":
                global_device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info("Auto-detected device: %s", global_device)

            # Update global device setting
            cls._config["processing"]["device"] = global_device

            # Update model-specific device settings and handle quantization
            for model_name, model_config in cls._config.get("models", {}).items():
                if isinstance(model_config, dict):
                    device = model_config.get("device", "auto")
                    if device == "auto":
                        model_config["device"] = global_device

                    # Disable quantization if running on CPU
                    if (
                        model_config.get("quantize", False)
                        and model_config["device"] == "cpu"
                    ):
                        logger.warning(
                            "Quantization enabled for %s but running on CPU. Disabling quantization.",
                            model_name,
                        )
                        cls._config["models"][model_name]["quantize"] = False

        except Exception as e:
            logger.error("Error processing device settings: %s", e)
            raise

    @classmethod
    def _merge_configs(
        cls, base: Dict[str, Any], overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merges two configuration dictionaries with overrides taking precedence."""
        merged = copy.deepcopy(base)
        for key, value in overrides.items():
            if (
                isinstance(value, dict)
                and key in merged
                and isinstance(merged[key], dict)
            ):
                merged[key] = cls._merge_configs(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        logger.debug("Configurations merged successfully.")
        return merged

    @classmethod
    @cached(
        cache=LRUCache(maxsize=128),
        key=lambda cls, key, default: keys.hashkey(str(key)),
    )
    def get(cls, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value using dot notation for nested keys."""
        try:
            value = cls._config
            for k in key.split("."):
                value = value[k]
            cls._cache_stats["hits"] += 1
            logger.debug("Cache hit for key: %s", key)
            return value
        except (KeyError, TypeError):
            cls._cache_stats["misses"] += 1
            logger.debug("Cache miss for key: %s", key)
            return default

    @classmethod
    def get_model_config(cls, model_name: str) -> Dict[str, Any]:
        """Gets the configuration for a specific model."""
        try:
            models_config = cls._config.get("models", {})
            if model_name not in models_config:
                raise LoadError(
                    f"Configuration for model '{model_name}' not found",
                    {"model_name": model_name},
                )
            return models_config[model_name]
        except Exception as e:
            logger.error("Error retrieving model config: %s", e)
            raise
    @classmethod
    def invalidate_cache(cls) -> None:
        """Invalidates the configuration cache."""
        cls._cache.clear()
        cls._cache_stats['hits'] = 0
        cls._cache_stats['misses'] = 0
        logger.debug("Configuration cache invalidated.")
    
    @classmethod
    def _verify_model_configs(cls) -> None:
        """Verifies specific model configurations in the loaded config."""
        models_config = cls._config.get("models", {})

        for model_name, config in models_config.items():
            if not isinstance(config, dict):
                continue

            # Check required fields
            if "device" not in config:
                raise ConfigurationErrorFactory.create_missing_config_error(
                    f"Device configuration for model '{model_name}' is missing",
                    {"model_name": model_name}
                )

            # Handle max_length defaults and range checking
            max_length = config.get(
                "max_length", cls._config.get("processing", {}).get("max_length", 1024)
            )
            if not isinstance(max_length, int) or not (128 <= max_length <= 16384):
                raise ConfigurationErrorFactory.create_value_range_error(
                    f"max_length for {model_name} must be between 128 and 16384",
                    {"model_name": model_name, "max_length": max_length}
                )
            config["max_length"] = max_length
        logger.debug("Model configurations verified successfully.")
    
    
    @classmethod
    def get_cache_dir(cls) -> str:
        """Gets the cache directory path."""
        cache_dir = cls._config.get("cache_dir", ".cache")
        if not os.path.isabs(cache_dir):
            cache_dir = str(cls._get_project_root() / cache_dir)

        os.makedirs(cache_dir, exist_ok=True)
        logger.debug("Cache directory set to: %s", cache_dir)
        return cache_dir

    @classmethod
    def get_processing_config(cls) -> Dict[str, Any]:
        """Gets the processing configuration."""
        return cls.get("processing", {})

    @classmethod
    def retry_load(
        cls, config_path: str, retries: int = 3, backoff: float = 1.0
    ) -> Dict[str, Any]:
        """Attempts to load the configuration with retries and exponential backoff."""
        attempt = 0
        while attempt < retries:
            try:
                return cls.load(config_path)
            except LoadError:
                attempt += 1
                sleep_time = backoff * (2 ** (attempt - 1))
                logger.warning(
                    "Retrying to load configuration in %s seconds...", sleep_time
                )
                time.sleep(sleep_time)
        raise LoadError(
            "Failed to load configuration after multiple attempts",
            {"config_path": config_path},
        )

    @classmethod
    def load(cls, config_path: str = "config/parser_config.yaml") -> Dict[str, Any]:
        """Loads the configuration from the specified path."""
        with cls._lock:
            if not cls._is_loaded:
                try:
                    config_path = Path(config_path)
                    if not config_path.is_absolute():
                        config_path = cls._get_project_root() / config_path

                    config_data = cls._load_file(config_path)

                    # Support configuration templates
                    if "templates" in config_data:
                        for template_name, template_str in config_data[
                            "templates"
                        ].items():
                            cls._templates[template_name] = Template(template_str)
                        logger.debug("Configuration templates loaded.")

                    # Merge environment-specific overrides
                    environment = os.getenv("ENVIRONMENT", "development")
                    env_overrides = config_data.get(f"env_{environment}", {})
                    cls._config = cls._merge_configs(config_data, env_overrides)
                    logger.debug(
                        "Environment-specific overrides applied for: %s", environment
                    )

                    # Initialize schema validator
                    schema = config_data.get("schema", {})
                    cls._schema_validator = SchemaValidator(schema)
                    cls._validate_schema()

                    cls.setup_logging()
                    logger.debug("Loading configuration from %s", config_path)

                    cls._verify_configuration()
                    cls._process_device_settings()
                    cls._verify_model_configs()

                    # Setup file watcher with debouncing and batching
                    cls.setup_file_watcher(config_path)

                    cls._is_loaded = True
                    logger.info("Configuration loaded successfully.")

                except LoadError as e:
                    if not cls._logger:
                        cls.setup_logging()
                    cls._logger.error(
                        "Failed to load configuration: %s", e.args[0], exc_info=True
                    )
                    raise
                except ValidationError as ve:
                    if not cls._logger:
                        cls.setup_logging()
                    cls._logger.error(
                        "Configuration validation failed: %s", ve.args[0], exc_info=True
                    )
                    raise

            return cls._config

    @classmethod
    def compress_snapshot(cls, snapshot: Dict[str, Any]) -> bytes:
        """Compresses a configuration snapshot."""
        try:
            serialized = yaml.dump(snapshot).encode("utf-8")
            compressed = gzip.compress(serialized)
            logger.debug("Snapshot compressed successfully.")
            return compressed
        except Exception as e:
            logger.error("Failed to compress snapshot: %s", e)
            raise LoadError("Snapshot compression failed.", {"error": str(e)}) from e

    @classmethod
    def decompress_snapshot(cls, compressed_snapshot: bytes) -> Dict[str, Any]:
        """Decompresses a configuration snapshot."""
        try:
            decompressed = gzip.decompress(compressed_snapshot).decode("utf-8")
            snapshot = yaml.safe_load(decompressed)
            logger.debug("Snapshot decompressed successfully.")
            return snapshot
        except Exception as e:
            logger.error("Failed to decompress snapshot: %s", e)
            raise LoadError("Snapshot decompression failed.", {"error": str(e)}) from e

    @classmethod
    def cache_eviction_policy(
        cls, key: Any, value: Any, maxsize: int, currsize: int
    ) -> bool:
        """Determines if an item should be evicted from the cache."""
        # Example policy: Least Recently Used
        return currsize > maxsize
    
    @classmethod
    def cache_warmup(cls, keys: List[str]) -> None:
        """Warms up the cache with the specified keys."""
        for key in keys:
            _ = cls.get(key)
        logger.debug("Cache warmup completed.")

    @classmethod
    def monitor_cache_size(cls) -> None:
        """Monitors the cache size and logs if necessary."""
        size = len(cls._cache)
        logger.debug("Current cache size: %d", size)
        # Implement further monitoring logic as needed

    @classmethod
    def cache_performance_metrics(cls) -> Dict[str, int]:
        """Returns cache performance metrics."""
        return copy.deepcopy(cls._cache_stats)

    @classmethod
    def add_configuration_snapshot(cls) -> Union[Dict[str, Any], bytes]:
        """Creates a snapshot of the current configuration."""
        snapshot = copy.deepcopy(cls._config)
        if cls._snapshot_compression:
            snapshot = cls.compress_snapshot(snapshot)
        with cls._snapshot_lock:
            cls._snapshots.append(snapshot)
        logger.debug("Configuration snapshot added.")
        return snapshot

    @classmethod
    def rollback_configuration(cls, snapshot: Union[Dict[str, Any], bytes]) -> None:
        """Rolls back to a previous configuration snapshot."""
        try:
            if cls._snapshot_compression and isinstance(snapshot, bytes):
                snapshot = cls.decompress_snapshot(snapshot)
            cls._config = copy.deepcopy(snapshot)
            cls.invalidate_cache()
            cls._version += 1
            cls.add_configuration_snapshot()
            if cls._observers:
                cls._observers.notify(cls._config, async_notify=True)
            logger.info("Configuration rolled back to snapshot.")
        except Exception as e:
            logger.error("Error during rollback: %s", e)
            raise

    @classmethod
    def snapshot_pruning_strategy(cls, max_snapshots: int = 10) -> None:
        """Prunes old snapshots to maintain a maximum number."""
        with cls._snapshot_lock:
            while len(cls._snapshots) > max_snapshots:
                pruned = cls._snapshots.pop(0)
                logger.debug("Pruned snapshot: %s", pruned)
            logger.debug(
                "Snapshot pruning completed. Total snapshots: %d.", len(cls._snapshots)
            )

    @classmethod
    def snapshot_comparison_tools(
        cls, snapshot1: Dict[str, Any], snapshot2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compares two snapshots and returns the differences."""
        differences = {}
        keys_set = set(snapshot1.keys()).union(snapshot2.keys())
        for key in keys_set:
            if snapshot1.get(key) != snapshot2.get(key):
                differences[key] = {
                    "snapshot1": snapshot1.get(key),
                    "snapshot2": snapshot2.get(key),
                }
        logger.debug("Differences between snapshots: %s", differences)
        return differences
