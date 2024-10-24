# src/parsers/parser_init.py


import logging
import os
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

import torch
from huggingface_hub import login, HfApi
from transformers import (
    AutoProcessor,
    AutoTokenizer,
    AutoModelForCausalLM,
    pipeline,
    Pipeline,
    VisionEncoderDecoderModel,
)

from src.utils.config import Config


def setup_logging(logger_name: str = "EnhancedParser") -> logging.Logger:
    """Sets up logging based on configuration."""
    logging_config = Config.get_logging_config()
    logger = logging.getLogger(logger_name)

    level = getattr(logging, logging_config.get("level", "DEBUG"))
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        if "FileHandler" in logging_config.get("handlers", []):
            file_path = logging_config.get("file_path", "logs/parser.log")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file_handler = logging.FileHandler(file_path)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def select_device(
    model_name: Optional[str] = None, required_memory_gb: float = 8.0
) -> Tuple[str, int]:
    """
    Selects appropriate device by first trying GPU, then falling back to CPU if necessary.
    """
    logger = logging.getLogger(f"DeviceSelector-{model_name}")

    if torch.cuda.is_available():
        try:
            # Get GPU properties
            cuda_device = torch.cuda.current_device()
            total_memory = torch.cuda.get_device_properties(cuda_device).total_memory
            available_memory = total_memory - torch.cuda.memory_allocated(cuda_device)
            available_memory_gb = available_memory / (1024**3)  # Convert to GB

            logger.info(f"GPU Memory Available: {available_memory_gb:.2f}GB")

            if available_memory_gb >= required_memory_gb:
                logger.info(f"Using GPU for {model_name}")
                return "cuda", 0
            else:
                logger.warning(
                    f"GPU has insufficient memory ({available_memory_gb:.2f}GB available, "
                    f"{required_memory_gb}GB required). Falling back to CPU."
                )
        except Exception as e:
            logger.warning(f"Error checking GPU memory: {e}. Falling back to CPU.")
    else:
        logger.info("No GPU available, using CPU")

    return "cpu", -1


def authenticate_huggingface(logger: logging.Logger) -> bool:
    """Authenticates with Hugging Face using configured token."""
    try:
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            logger.warning("No Hugging Face token found in environment variables.")
            return False

        cache_dir = Config.get_cache_dir()
        os.environ["HF_HOME"] = cache_dir
        logger.debug(f"Set HF_HOME to '{cache_dir}'")

        login(token=hf_token)
        api = HfApi()
        user = api.whoami(token=hf_token)
        logger.info(f"Authenticated with Hugging Face as '{user['name']}'")
        return True
    except Exception as e:
        logger.error(f"Hugging Face authentication failed: {e}", exc_info=True)
        return False


def init_donut(
    logger: logging.Logger,
) -> Tuple[Optional[AutoProcessor], Optional[VisionEncoderDecoderModel]]:
    """Initializes Donut model, attempting GPU first."""
    try:
        logger.info("Initializing Donut model and processor.")
        model_config = Config.get_model_config("donut")

        # Donut base model typically needs about 4GB VRAM
        device, _ = select_device("donut", required_memory_gb=4.0)

        # Initialize processor
        donut_processor = AutoProcessor.from_pretrained(
            model_config["repo_id"],
            trust_remote_code=True,
            cache_dir=Config.get_cache_dir(),
        )

        # Initialize model
        model_kwargs = {
            "trust_remote_code": True,
            "cache_dir": Config.get_cache_dir(),
        }

        if device == "cuda":
            model_kwargs["torch_dtype"] = torch.float16

        donut_model = VisionEncoderDecoderModel.from_pretrained(
            model_config["repo_id"], **model_kwargs
        )

        # Move to selected device
        donut_model = donut_model.to(device)
        logger.info(f"Loaded Donut model on {device}")

        return donut_processor, donut_model
    except Exception as e:
        logger.error(f"Failed to load Donut model: {e}", exc_info=True)
        if "device" in locals() and device == "cuda":
            logger.info("Attempting to fall back to CPU...")
            try:
                donut_model = donut_model.to("cpu")
                logger.info("Successfully moved Donut model to CPU")
                return donut_processor, donut_model
            except Exception as cpu_e:
                logger.error(f"CPU fallback also failed: {cpu_e}")
        return None, None


def init_llama_model(model_type: str, logger: logging.Logger) -> Optional[Pipeline]:
    """
    Initializes a Llama model pipeline with appropriate settings.
    """
    try:
        logger.info(f"Initializing Llama model for {model_type}")
        model_config = Config.get_model_config(model_type)

        # Verify we have authentication
        if not authenticate_huggingface(logger):
            raise ValueError("Hugging Face authentication required for Llama models")

        # Llama-70B needs about 35GB of memory
        device, pipeline_device = select_device(model_type, required_memory_gb=35.0)

        # Configure model initialization
        model_kwargs = {
            "rope_scaling": {"type": "dynamic", "factor": 8.0},
            "torch_dtype": torch.float16 if device == "cuda" else torch.float32,
            "device_map": "auto",
            "trust_remote_code": True,
        }

        # Initialize the model first
        model = AutoModelForCausalLM.from_pretrained(
            model_config["repo_id"], **model_kwargs
        )

        # Initialize tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            model_config["repo_id"], trust_remote_code=True
        )

        # Create pipeline
        pipeline_kwargs = {
            "model": model,
            "tokenizer": tokenizer,
            "task": "text2text-generation",
            "device": pipeline_device,
            "max_length": model_config.get("max_length", 512),
            "temperature": model_config.get("parameters", {}).get("temperature", 0.7),
            "top_p": model_config.get("parameters", {}).get("top_p", 0.9),
            "do_sample": True,
        }

        if model_type == "summarization":
            pipeline_kwargs["min_length"] = model_config.get("parameters", {}).get(
                "min_summary_length", 50
            )

        logger.info(f"Creating pipeline for {model_type} on {device}")
        model_pipeline = pipeline(**pipeline_kwargs)
        logger.info(f"Successfully initialized {model_type} pipeline")

        return model_pipeline

    except Exception as e:
        logger.error(
            f"Failed to initialize Llama model for {model_type}: {e}", exc_info=True
        )
        return None


def init_validation_model(logger: logging.Logger) -> Optional[Pipeline]:
    """Initializes validation model using configuration."""
    return init_llama_model("validation", logger)


def init_summarization_model(logger: logging.Logger) -> Optional[Pipeline]:
    """Initializes summarization model using configuration."""
    return init_llama_model("summarization", logger)


def init_model_parser(logger: logging.Logger) -> Optional[Pipeline]:
    """Initializes the model-based parser using configuration."""
    return init_llama_model("model_based_parsing", logger)
