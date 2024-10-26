# src/parsers/stages/model_based_parsing.py

from transformers import pipeline
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
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


def perform_model_based_parsing(prompt: str, llama_model: Any, logger: logging.Logger) -> Dict[str, Any]:
    try:
        logger.debug("Executing model-based parsing with prompt")
        result = llama_model['model'](prompt, max_length=llama_model['model'].config.max_length, do_sample=True)
        structured_data = extract_structured_data(result, logger)
        validated_data = validate_structured_data(structured_data, QUICKBASE_SCHEMA, logger)
        confidence_scores = calculate_confidence_scores(validated_data)
        parsed_data = {
            "structured_data": validated_data,
            "metadata": {
                "model_name": llama_model['model'].config.name_or_path,
                "parsing_timestamp": datetime.now().isoformat(),
                "confidence_scores": confidence_scores
            }
        }
        logger.debug(f"Model parsing complete: {len(structured_data)} sections extracted")
        return parsed_data
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


def extract_structured_data(result: List[Dict[str, Any]], logger: logging.Logger) -> Dict[str, Dict[str, List[Any]]]:
    structured_data = {}
    for entry in result:
        if isinstance(entry, dict):
            text = entry.get("generated_text", "")
            try:
                json_data = json.loads(text)
                sections = parse_json_sections(json_data, logger)
                for section_name, section_content in sections.items():
                    structured_data[section_name] = parse_section(section_content, logger)
            except json.JSONDecodeError as jde:
                logger.error(f"JSON decoding failed: {jde}")
                # Attempt to recover by extracting valid JSON parts
                recovered_data = recover_json(text, logger)
                structured_data.update(recovered_data)
            except Exception as e:
                logger.error(f"Error extracting structured data: {e}", exc_info=True)
    return structured_data


def parse_json_sections(json_data: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    sections = {}
    for section, content in json_data.items():
        if section in QUICKBASE_SCHEMA:
            sections[section] = content
        else:
            logger.warning(f"Unexpected section: {section}")
    return sections


def parse_section(content: Any, logger: logging.Logger) -> Dict[str, List[Any]]:
    fields = {}
    if isinstance(content, dict):
        for field, value in content.items():
            field_type = determine_field_type(field)
            if isinstance(value, list):
                cleaned_values = [clean_field_value(v, field_type) for v in value]
            else:
                cleaned_values = [clean_field_value(value, field_type)]
            fields[field] = cleaned_values
    else:
        logger.warning(f"Expected dict for section content, got {type(content)}")
    logger.debug(f"Parsed fields for section: {fields}")
    return fields


def recover_json(text: str, logger: logging.Logger) -> Dict[str, Dict[str, List[Any]]]:
    structured_data = {}
    json_pattern = re.compile(r'\{.*?\}', re.DOTALL)
    matches = json_pattern.findall(text)
    for match in matches:
        try:
            json_data = json.loads(match)
            sections = parse_json_sections(json_data, logger)
            for section_name, section_content in sections.items():
                if section_name not in structured_data:
                    structured_data[section_name] = {}
                for field, value in section_content.items():
                    field_type = determine_field_type(field)
                    cleaned_value = clean_field_value(value, field_type)
                    if field in structured_data[section_name]:
                        structured_data[section_name][field].append(cleaned_value)
                    else:
                        structured_data[section_name][field] = [cleaned_value]
        except json.JSONDecodeError as jde:
            logger.error(f"Failed to recover JSON from text: {jde}")
    return structured_data


def parse_checkbox(text: str) -> bool:
    return text.lower() in ['yes', 'true', '1', 'checked', 'on']


def clean_field_value(value: Any, field_type: str) -> Any:
    if isinstance(value, str):
        value = value.strip()
    if field_type == "boolean":
        if isinstance(value, bool):
            return value
        return parse_checkbox(str(value))
    elif field_type == "date":
        formatted_date = format_date(str(value))
        return formatted_date if formatted_date else "N/A"
    elif field_type == "string":
        return value if value else "N/A"
    elif field_type == "object":
        if isinstance(value, dict):
            cleaned_obj = {}
            for k, v in value.items():
                cleaned_obj[k] = clean_field_value(v, determine_field_type(k))
            return cleaned_obj
        return {"Checked": False, "Details": "N/A"}
    elif field_type == "array":
        if isinstance(value, list):
            return [clean_field_value(v, "string") for v in value]
        return ["N/A"]
    else:
        return value


def determine_field_type(field_name: str) -> str:
    # Map field names to their types based on schema
    for section, fields in QUICKBASE_SCHEMA.items():
        if field_name in fields:
            return fields[field_name]["type"]
    return "string"  # Default type


def format_date(date_str: str) -> Optional[str]:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


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
    # Handle missing required fields
    for section, fields in schema.items():
        if section not in structured_data:
            logger.warning(f"Missing required section: {section}")
            structured_data[section] = {}
        for field, properties in fields.items():
            if properties.get("required") and field not in structured_data[section]:
                logger.warning(f"Missing required field: {field} in section: {section}")
                structured_data[section][field] = ["N/A"]
    return structured_data


def coerce_type(value: Any, field_type: str, schema: Dict[str, Any], section: str, field: str, logger: logging.Logger) -> Any:
    if value == "N/A":
        return value
    try:
        if field_type == "boolean":
            return bool(value)
        elif field_type == "date":
            formatted_date = format_date(value)
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
