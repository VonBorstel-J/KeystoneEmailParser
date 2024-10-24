# src/parsers/parser_init.py

import logging
import os
from typing import Optional, Tuple, Dict, Any

import torch
from huggingface_hub import login, HfApi
from transformers import (
    AutoProcessor,
    pipeline,
    Pipeline,
    VisionEncoderDecoderModel,
)

from src.utils.config import Config
from src.parsers.stages.model_based_parsing import initialize_model_parser

def setup_logging(logger_name: str = "EnhancedParser") -> logging.Logger:
    """Sets up logging based on configuration."""
    logging_config = Config.get_logging_config()
    logger = logging.getLogger(logger_name)
    
    # Set log level from config
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
        
        # Add file handler if configured
        if "FileHandler" in logging_config.get("handlers", []):
            file_path = logging_config.get("file_path", "logs/parser.log")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file_handler = logging.FileHandler(file_path)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
    logger.propagate = False
    return logger

def select_device(model_name: Optional[str] = None) -> Tuple[torch.device, int]:
    """Selects appropriate device based on configuration and availability."""
    device_str = Config.get_device(model_name)
    if device_str == "cuda" and torch.cuda.is_available():
        return torch.device("cuda"), 0
    return torch.device("cpu"), -1

def authenticate_huggingface(logger: logging.Logger) -> bool:
    """Authenticates with Hugging Face using configured token."""
    try:
        hf_token = Config.get_hf_token()
        if not hf_token:
            raise ValueError("Hugging Face token not found in environment variables.")

        cache_dir = Config.get_cache_dir()
        os.environ["HF_HOME"] = cache_dir
        logger.debug(f"Set HF_HOME to '{cache_dir}' for Hugging Face authentication.")

        login(token=hf_token)
        api = HfApi()
        user = api.whoami(token=hf_token)
        logger.info(f"Authenticated with Hugging Face as '{user['name']}'.")
        return True
    except Exception as e:
        logger.error(f"Failed to authenticate with Hugging Face: {e}", exc_info=True)
        return False

def init_ner(logger: logging.Logger) -> Optional[Pipeline]:
    """Initializes NER pipeline using configuration."""
    try:
        logger.info("Initializing NER pipeline.")
        model_config = Config.get_model_config("ner")
        device, pipeline_device = select_device("ner")
        
        ner_pipeline = pipeline(
            task=model_config["task"],
            model=model_config["repo_id"],
            tokenizer=model_config["repo_id"],
            aggregation_strategy=model_config.get("aggregation_strategy", "simple"),
            device=pipeline_device,
        )
        logger.info(f"Loaded NER model '{model_config['repo_id']}' successfully.")
        return ner_pipeline
    except Exception as e:
        logger.error(f"Failed to load NER model: {e}", exc_info=True)
        return None

def init_donut(logger: logging.Logger) -> Tuple[Optional[AutoProcessor], Optional[VisionEncoderDecoderModel]]:
    """Initializes Donut model using configuration."""
    try:
        logger.info("Initializing Donut model and processor.")
        model_config = Config.get_model_config("donut")
        device, _ = select_device("donut")
        
        donut_processor = AutoProcessor.from_pretrained(
            model_config["repo_id"], 
            trust_remote_code=True,
            cache_dir=Config.get_cache_dir()
        )
        
        donut_model = VisionEncoderDecoderModel.from_pretrained(
            model_config["repo_id"],
            trust_remote_code=True,
            cache_dir=Config.get_cache_dir()
        )
        
        if Config.should_quantize("donut"):
            donut_model = donut_model.half()
            
        donut_model.to(device)
        logger.info(f"Loaded Donut model '{model_config['repo_id']}' successfully.")
        return donut_processor, donut_model
    except Exception as e:
        logger.error(f"Failed to load Donut model: {e}", exc_info=True)
        return None, None

def init_validation_model(logger: logging.Logger) -> Optional[Pipeline]:
    """Initializes validation model using configuration."""
    try:
        if not authenticate_huggingface(logger):
            raise ValueError("Hugging Face authentication unsuccessful.")
            
        logger.info("Initializing Validation Model pipeline.")
        model_config = Config.get_model_config("validation")
        device, _ = select_device("validation")
        
        validation_pipeline = pipeline(
            task=model_config["task"],
            model=model_config["repo_id"],
            tokenizer=model_config["repo_id"],
            device=device,
        )
        logger.info(f"Loaded Validation Model '{model_config['repo_id']}' successfully.")
        return validation_pipeline
    except Exception as e:
        logger.error(f"Failed to load Validation Model: {e}", exc_info=True)
        return None

def init_summarization_model(logger: logging.Logger) -> Optional[Pipeline]:
    """Initializes summarization model using configuration."""
    try:
        logger.info("Initializing Text Summarization Model pipeline.")
        model_config = Config.get_model_config("summarization")
        device, _ = select_device("summarization")
        
        summarization_pipeline = pipeline(
            task=model_config["task"],
            model=model_config["repo_id"],
            tokenizer=model_config["repo_id"],
            device=device,
        )
        logger.info(f"Loaded Summarization Model '{model_config['repo_id']}' successfully.")
        return summarization_pipeline
    except Exception as e:
        logger.error(f"Failed to load Summarization Model: {e}", exc_info=True)
        return None