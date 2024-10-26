from transformers import pipeline
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Tuple
import torch
import json
import re

from src.utils.quickbase_schema import QUICKBASE_SCHEMA


class ParsingError(Exception):
    pass


def initialize_model_parser(logger: logging.Logger, config: Dict[str, Any], prompt_templates: Optional[Dict[str, str]] = None) -> Any:
    try:
        system_prompt = config.get("llama", {}).get("system_prompt", "You are a helpful assistant that outputs JSON.")
        example_output = config.get("llama", {}).get("example_output", "{}")
        field_types = config.get("llama", {}).get("field_types", {})

        full_prompt = (
            f"{system_prompt}\n\n"
            f"Example Output:\n{example_output}\n\n"
            f"Field Types:\n{json.dumps(field_types, indent=2)}\n\n"
            f"{prompt_templates.get('text_extraction', '')}"
        )

        model_name = config.get("llama", {}).get("repo_id", "meta-llama/Llama-3.2-3B-Instruct")
        logger.info(f"Initializing LLaMA model with: {model_name}")
        llama_pipeline = pipeline(
            config.get("llama", {}).get("task", "text-generation"),
            model=model_name,
            tokenizer=model_name,
            device=0 if torch.cuda.is_available() else -1,
            torch_dtype=torch.float16 if config.get("llama", {}).get("torch_dtype") == "float16" else torch.float32,
            cache_dir=config.get("models", {}).get("cache_dir", ".cache"),
        )
        logger.info("LLaMA model initialized successfully.")
        return {"model": llama_pipeline, "prompt_templates": prompt_templates, "field_types": field_types}
    except Exception as e:
        logger.error(f"Failed to initialize LLaMA model: {e}")
        raise ParsingError(f"Failed to initialize LLaMA model: {e}")


def extract_json_from_llama_output(text: str, logger: logging.Logger) -> Dict[str, Any]:
    """Find and extract JSON from LLaMA's text output."""
    json_pattern = r'\{(?:[^{}]|(?R))*\}'
    matches = re.finditer(json_pattern, text, re.DOTALL)

    for match in matches:
        try:
            potential_json = match.group()
            return json.loads(potential_json)
        except json.JSONDecodeError:
            continue

    logger.error("No valid JSON found in output")
    return {}


def perform_model_based_parsing(prompt: str, llama_model: Any, logger: logging.Logger) -> Dict[str, Any]:
    try:
        logger.debug("Executing model-based parsing with prompt")
        result = llama_model['model'](
            prompt, 
            max_length=llama_model['model'].config.max_length,
            do_sample=True,
            temperature=0.1  # Lower temperature for more structured output
        )
        
        json_data = {}
        for entry in result:
            json_data = extract_json_from_llama_output(entry['generated_text'], logger)
            if json_data:
                break
        
        if not json_data:
            logger.error("Failed to extract JSON from LLaMA output")
            raise ParsingError("No valid JSON extracted from model output.")
        
        structured_data = parse_json_sections(json_data, logger)
        validated_data = validate_structured_data(structured_data, QUICKBASE_SCHEMA, logger)
        
        return {
            "structured_data": validated_data,
            "metadata": {
                "model_name": llama_model['model'].config.name_or_path,
                "parsing_timestamp": datetime.now().isoformat(),
                "confidence_scores": calculate_confidence_scores(validated_data)
            }
        }
    except Exception as e:
        logger.error(f"Model parsing failed: {e}", exc_info=True)
        raise ParsingError(f"Model parsing failed: {e}")


def calculate_confidence_scores(structured_data: Dict[str, Dict[str, List[Any]]]) -> Dict[str, float]:
    confidence_scores = {}
    for section, fields in structured_data.items():
        field_confidences = []
        for field, values in fields.items():
            for value in values:
                if isinstance(value, dict) and 'confidence' in value:
                    field_confidences.append(value['confidence'])
                elif isinstance(value, float):
                    field_confidences.append(value)
        if field_confidences:
            confidence_scores[section] = sum(field_confidences) / len(field_confidences)
        else:
            confidence_scores[section] = 1.0  # Default confidence
    return confidence_scores


def parse_json_sections(json_data: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    sections = {}
    for section, content in json_data.items():
        if section in QUICKBASE_SCHEMA:
            sections[section] = content
        else:
            logger.warning(f"Unexpected section: {section}")
    return sections


def validate_structured_data(structured_data: Dict[str, Dict[str, List[Any]]], schema: Dict[str, Any], logger: logging.Logger) -> Dict[str, Dict[str, List[Any]]]:
    for section, fields in structured_data.items():
        if section not in schema:
            logger.warning(f"Section '{section}' not found in schema.")
            continue
        for field, values in fields.items():
            if field not in schema[section]:
                logger.warning(f"Field '{field}' in section '{section}' not found in schema.")
                continue
            field_type = schema[section][field]["type"]
            validated_values = []
            for value in values:
                coerced_value = coerce_type(value, field_type, schema, section, field, logger)
                validated_values.append(coerced_value)
            structured_data[section][field] = validated_values
    return structured_data

def _format_dates(dates: List[str]) -> List[str]:
    """
    Formats a list of date strings to 'YYYY-MM-DD'.
    """
    from datetime import datetime
    formatted = []
    for date in dates:
        try:
            if date != "N/A":
                dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
                formatted.append(dt.strftime("%Y-%m-%d"))
        except ValueError:
            formatted.append("N/A")
    return formatted if formatted else ["N/A"]

def coerce_type(value: Any, field_type: str, schema: Dict[str, Any], section: str, field: str, logger: logging.Logger) -> Any:
    if value == "N/A":
        return value
    try:
        if field_type == "boolean":
            return bool(value)
        elif field_type == "date":
            formatted_date = _format_dates([value])[0]  # Use the local function
            if formatted_date:
                return formatted_date
            else:
                logger.warning(f"Invalid date format for field '{field}' in section '{section}': {value}")
                return "N/A"
        elif field_type == "string":
            return str(value)
        elif field_type == "object":
            if isinstance(value, dict):
                return value
            else:
                logger.warning(f"Expected object for field '{field}' in section '{section}', got {type(value)}")
                return {"Checked": False, "Details": "N/A"}
        elif field_type == "array":
            if isinstance(value, list):
                return value
            else:
                logger.warning(f"Expected array for field '{field}' in section '{section}', got {type(value)}")
                return ["N/A"]
        else:
            return value
    except Exception as e:
        logger.error(f"Type coercion error for field '{field}' in section '{section}': {e}")
        return "N/A"
