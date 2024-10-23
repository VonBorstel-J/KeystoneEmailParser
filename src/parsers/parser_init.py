# src/parsers/parser_init.py

"""
Module for initializing various parsers and models used in the KeystoneEmailParser project.

Includes functions to set up logging, select devices, authenticate with Hugging Face,
and initialize different NLP pipelines such as NER, Donut, Validation, and Summarization.
"""

import logging
import os
from typing import Optional, Tuple, Dict, Any

import torch
from huggingface_hub import login, HfApi
from transformers import (
    AutoProcessor,
    AutoModelForSeq2SeqLM,
    pipeline,
    Pipeline,
)

def setup_logging(logger_name: str = "EnhancedParser") -> logging.Logger:
    """
    Configures and returns a logger with the specified name.

    Args:
        logger_name (str): Name of the logger.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Prevent log propagation to the root logger to avoid duplicate logs
    logger.propagate = False

    return logger


def select_device(config: Dict[str, Any]) -> Tuple[torch.device, int]:
    """
    Selects the device for model deployment.

    Args:
        config (Dict[str, Any]): Configuration dictionary.

    Returns:
        Tuple[torch.device, int]: A tuple containing the torch.device and the corresponding device index for Hugging Face pipelines.

    Raises:
        ValueError: If an invalid device option is provided.
    """
    device_str = config["processing"].get("device", "auto").lower()
    if device_str == "cuda" and torch.cuda.is_available():
        return torch.device("cuda"), 0
    elif device_str == "cpu":
        return torch.device("cpu"), -1
    elif device_str == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda"), 0
        else:
            return torch.device("cpu"), -1
    else:
        raise ValueError(f"Invalid device option: {device_str}")


def init_ner(logger: logging.Logger, config: Dict[str, Any]) -> Optional[Pipeline]:
    """
    Initializes the Named Entity Recognition (NER) pipeline.

    Args:
        logger (logging.Logger): Logger instance.
        config (Dict[str, Any]): Configuration dictionary.

    Returns:
        Optional[Pipeline]: Initialized NER pipeline or None if initialization fails.
    """
    try:
        logger.info("Initializing NER pipeline.")
        model_config = config["models"]["ner"]
        repo_id = model_config["repo_id"]
        task = model_config.get("task", "ner")
        aggregation_strategy = model_config.get("aggregation_strategy", "simple")
        device, pipeline_device = select_device(config)

        ner_pipeline = pipeline(
            task=task,
            model=repo_id,
            tokenizer=repo_id,
            aggregation_strategy=aggregation_strategy,
            device=pipeline_device,
        )
        logger.info("Loaded NER model '%s' successfully.", repo_id)
        return ner_pipeline
    except (ValueError, OSError) as e:
        logger.error("ValueError: Failed to load NER model: %s", e)
        return None
    except Exception as e:
        logger.error("Failed to load NER model: %s", e, exc_info=True)
        return None


def init_donut(
    logger: logging.Logger, config: Dict[str, Any]
) -> Tuple[Optional[AutoProcessor], Optional[AutoModelForSeq2SeqLM]]:
    """
    Initializes the Donut model and processor.

    Args:
        logger (logging.Logger): Logger instance.
        config (Dict[str, Any]): Configuration dictionary.

    Returns:
        Tuple[Optional[AutoProcessor], Optional[AutoModelForSeq2SeqLM]]:
            The Donut processor and model, or (None, None) if initialization fails.
    """
    try:
        logger.info("Initializing Donut model and processor.")
        model_config = config["models"]["donut"]
        repo_id = model_config["repo_id"]
        cache_dir = config.get("cache_dir", ".cache")
        device, pipeline_device = select_device(config)

        # Set HF_HOME to manage cache directory and eliminate TRANSFORMERS_CACHE warning
        hf_home = config.get("hf_home", os.path.expanduser("~/.cache/huggingface"))
        os.environ["HF_HOME"] = hf_home
        logger.debug("Set HF_HOME to '%s'.", hf_home)

        # Initialize processor and model using Auto classes with trust_remote_code=True
        donut_processor = AutoProcessor.from_pretrained(repo_id, trust_remote_code=True)
        donut_model = AutoModelForSeq2SeqLM.from_pretrained(
            repo_id, trust_remote_code=True
        )
        donut_model.to(device)
        logger.info("Loaded Donut model '%s' successfully.", repo_id)
        return donut_processor, donut_model
    except (ValueError, OSError) as e:
        logger.error("ValueError: Failed to load Donut model '%s': %s", repo_id, e)
        return None, None
    except Exception as e:
        logger.error("Failed to load Donut model '%s': %s", repo_id, e, exc_info=True)
        return None, None


def authenticate_huggingface(logger: logging.Logger, config: Dict[str, Any]) -> bool:
    """
    Authenticates with the Hugging Face Hub using the provided token.

    Args:
        logger (logging.Logger): Logger instance.
        config (Dict[str, Any]): Configuration dictionary.

    Returns:
        bool: True if authentication is successful, False otherwise.
    """
    try:
        hf_token_env_var = config["authentication"]["hf_token_env_var"]
        hf_token = os.getenv(hf_token_env_var)
        if not hf_token:
            raise ValueError(
                f"Hugging Face token not found in environment variable '{hf_token_env_var}'."
            )

        # Set HF_HOME before authentication to ensure proper caching
        hf_home = config.get("hf_home", os.path.expanduser("~/.cache/huggingface"))
        os.environ["HF_HOME"] = hf_home
        logger.debug("Set HF_HOME to '%s' for Hugging Face authentication.", hf_home)

        login(token=hf_token)
        # Verify authentication
        api = HfApi()
        user = api.whoami(token=hf_token)
        logger.info("Authenticated with Hugging Face as '%s'.", user["name"])
        return True
    except (ValueError, OSError) as e:
        logger.error("ValueError: Hugging Face authentication failed: %s", e)
        return False
    except Exception as e:
        logger.error("Failed to authenticate with Hugging Face: %s", e, exc_info=True)
        return False


def init_validation_model(
    logger: logging.Logger, config: Dict[str, Any]
) -> Optional[Pipeline]:
    """
    Initializes the Validation Model pipeline.

    Args:
        logger (logging.Logger): Logger instance.
        config (Dict[str, Any]): Configuration dictionary.

    Returns:
        Optional[Pipeline]: Initialized Validation pipeline or None if initialization fails.
    """
    try:
        if not authenticate_huggingface(logger, config):
            raise ValueError("Hugging Face authentication unsuccessful.")

        logger.info("Initializing Validation Model pipeline.")
        model_config = config["models"]["validation"]
        repo_id = model_config["repo_id"]
        task = model_config.get("task", "text2text-generation")
        device, pipeline_device = select_device(config)

        validation_pipeline = pipeline(
            task=task,
            model=repo_id,
            tokenizer=repo_id,
            device=pipeline_device,
        )
        logger.info("Loaded Validation Model '%s' successfully.", repo_id)
        return validation_pipeline
    except (ValueError, OSError) as e:
        logger.error("ValueError: Failed to load Validation Model: %s", e)
        return None
    except Exception as e:
        logger.error("Failed to load Validation Model: %s", e, exc_info=True)
        return None


def init_summarization_model(
    logger: logging.Logger, config: Dict[str, Any]
) -> Optional[Pipeline]:
    """
    Initializes the Text Summarization Model pipeline.

    Args:
        logger (logging.Logger): Logger instance.
        config (Dict[str, Any]): Configuration dictionary.

    Returns:
        Optional[Pipeline]: Initialized Summarization pipeline or None if initialization fails.
    """
    try:
        logger.info("Initializing Text Summarization Model pipeline.")
        model_config = config["models"]["summarization"]
        repo_id = model_config["repo_id"]
        task = model_config.get("task", "summarization")
        device, pipeline_device = select_device(config)

        summarization_pipeline = pipeline(
            task=task,
            model=repo_id,
            tokenizer=repo_id,
            device=pipeline_device,
        )
        logger.info("Loaded Summarization Model '%s' successfully.", repo_id)
        return summarization_pipeline
    except (ValueError, OSError) as e:
        logger.error("ValueError: Failed to load Summarization Model '%s': %s", repo_id, e)
        return None
    except Exception as e:
        logger.error(
            "Failed to load Summarization Model '%s': %s", repo_id, e, exc_info=True
        )
        return None
