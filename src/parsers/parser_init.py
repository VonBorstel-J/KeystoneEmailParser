# src\parsers\parser_init.py


import logging
import os
import torch
from huggingface_hub import login
from transformers import (
    AutoProcessor,
    AutoModelForCausalLM,
    pipeline,
    VisionEncoderDecoderModel,
)
from src.utils.config import Config

def setup_logging(logger_name: str = "EnhancedParser") -> logging.Logger:
    """Sets up logging based on configuration."""
    config = Config.get_logging_config()
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, config.get("level", "DEBUG")))

    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler
        if "FileHandler" in config.get("handlers", []):
            file_path = config.get("file_path", "logs/parser.log")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file_handler = logging.FileHandler(file_path)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger

def init_donut(logger: logging.Logger):
    """Initializes Donut model and processor."""
    try:
        model_config = Config.get_model_config("donut")
        device = Config.get_device("donut")
        
        processor = AutoProcessor.from_pretrained(
            model_config["repo_id"],
            trust_remote_code=True,
            cache_dir=Config.get_cache_dir()
        )
        
        model = VisionEncoderDecoderModel.from_pretrained(
            model_config["repo_id"],
            trust_remote_code=True,
            cache_dir=Config.get_cache_dir(),
            torch_dtype=torch.float32 if device == "cuda" else torch.float16
        ).to(device)
        
        logger.info(f"Loaded Donut model on {device}")
        return processor, model
        
    except Exception as e:
        logger.error(f"Failed to load Donut model: {e}", exc_info=True)
        return None, None

def init_llama_model(model_type: str, logger: logging.Logger):
    """Initializes a Llama model pipeline."""
    try:
        # Auth check
        if not os.getenv("HF_TOKEN"):
            raise ValueError("HF_TOKEN not found in environment variables")
        login(token=os.getenv("HF_TOKEN"))
        
        model_config = Config.get_model_config(model_type)
        device = Config.get_device(model_type)
        
        model = pipeline(
            task=model_config.get("task", "text-generation"),
            model=model_config["repo_id"],
            tokenizer=model_config["repo_id"],
            device_map="auto" if device == "cuda" else None,
            torch_dtype=torch.float32 if device == "cuda" else torch.float16,
            **model_config.get("parameters", {})
        )
        
        logger.info(f"Initialized {model_type} model on {device}")
        return model
        
    except Exception as e:
        logger.error(f"Failed to initialize {model_type} model: {e}", exc_info=True)
        return None

# Convenience functions for specific models
def init_validation_model(logger): return init_llama_model("validation", logger)
def init_summarization_model(logger): return init_llama_model("summarization", logger)
def init_model_parser(logger): return init_llama_model("model_based_parsing", logger)