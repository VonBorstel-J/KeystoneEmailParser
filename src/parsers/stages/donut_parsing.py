# src/parsers/stages/donut_parsing.py

import logging
from typing import Dict, Any, Union, Optional, Tuple
from PIL import Image
import torch
from transformers import DonutProcessor, VisionEncoderDecoderModel

def initialize_donut(logger: logging.Logger, donut_config: Dict[str, Any]) -> Tuple[Optional[DonutProcessor], Optional[VisionEncoderDecoderModel]]:
    processor = None
    model = None
    try:
        logger.debug("Loading Donut model and processor.")
        logger.debug(f"Donut model configuration: {donut_config}")
        if not donut_config:
            raise KeyError("'donut' configuration is empty")
        repo_id = donut_config.get("repo_id")
        if not isinstance(repo_id, str):
            raise ValueError(f"Invalid 'repo_id' for Donut model: {repo_id}")
        processor = DonutProcessor.from_pretrained(repo_id)
        model = VisionEncoderDecoderModel.from_pretrained(repo_id)
        device = donut_config.get("device", "cpu")
        if device not in ["cpu", "cuda"]:
            logger.warning(f"Invalid device '{device}' specified. Falling back to 'cpu'.")
            device = "cpu"
        if device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA requested but not available. Falling back to CPU.")
            device = "cpu"
        model.to(device)
        logger.info("Donut model and processor initialized successfully.")
    except KeyError as e:
        logger.error("Configuration key error during Donut initialization: %s", e, exc_info=True)
    except ValueError as e:
        logger.error("Value error during Donut initialization: %s", e, exc_info=True)
    except ImportError as e:
        logger.error("Import error during Donut initialization: %s", e, exc_info=True)
    except Exception as e:
        logger.error("Unexpected error during Donut initialization: %s", e, exc_info=True)
    return processor, model

def perform_donut_parsing(
    document_image: Union[str, Image.Image],
    processor,
    model,
    device: str,
    logger: logging.Logger,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        logger.setLevel(getattr(logging, config.get('logging_level', 'DEBUG').upper(), logging.DEBUG))
        logger.debug("Starting Donut parsing process.")
        if isinstance(document_image, str):
            image = Image.open(document_image).convert("RGB")
        elif isinstance(document_image, Image.Image):
            image = document_image.convert("RGB")
        else:
            raise ValueError("Invalid image input type")
        image = preprocess_image(image, logger)
        inputs = processor(image, return_tensors="pt").to(device)
        max_length = config.get("max_length", 512)
        generated_ids = model.generate(**inputs, max_length=max_length)
        output = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        parsed_output = parse_donut_output(output, logger)
        return parsed_output
    except ValueError as e:
        logger.error(f"Value error during Donut parsing: {e}", exc_info=True)
        return {}
    except Exception as e:
        logger.error(f"Error during Donut parsing: {e}", exc_info=True)
        return {}

def preprocess_image(image: Image.Image, logger: logging.Logger) -> Image.Image:
    try:
        logger.debug("Applying image preprocessing.")
        from PIL import ImageEnhance, ImageFilter
        import cv2
        import numpy as np
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2)
        image = image.filter(ImageFilter.SHARPEN)
        image = image.convert("L")
        max_size = 1024
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            logger.debug(f"Resized image to {new_size}")
        image_np = np.array(image)
        _, image_np = cv2.threshold(image_np, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        image = Image.fromarray(image_np)
        image = image.filter(ImageFilter.MedianFilter())
        logger.debug("Image preprocessing completed.")
        return image
    except Exception as e:
        logger.error(f"Error during image preprocessing: {e}", exc_info=True)
        return image

def parse_donut_output(output: str, logger: logging.Logger) -> Dict[str, Any]:
    import json
    try:
        logger.debug("Parsing Donut model output into JSON.")
        parsed_json = json.loads(output)
        parsed_output_str = json.dumps(parsed_json)
        logger.debug(f"Parsed JSON: {parsed_output_str[:500]}")
        return parsed_json
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding failed: {e}", exc_info=True)
        return {}
    except Exception as e:
        logger.error(f"Error during Donut output parsing: {e}", exc_info=True)
        return {}
