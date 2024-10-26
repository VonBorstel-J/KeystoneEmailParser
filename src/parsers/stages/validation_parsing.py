# src/parsers/stages/validation_parsing.py

from src.utils.config import Config
from jsonschema import Draft7Validator, validators
from typing import Optional, Tuple, List, Dict, Any
import logging
import re
from src.utils.quickbase_schema import QUICKBASE_SCHEMA
from src.utils.exceptions import ValidationError
from transformers import pipeline
import torch

logger = logging.getLogger("Validation")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]
    def set_defaults(validator, properties, instance, schema):
        for property_name, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(property_name, subschema["default"])
        for error in validate_properties(validator, properties, instance, schema):
            yield error
    return validators.extend(validator_class, {"properties": set_defaults})

DefaultValidatingDraft7Validator = extend_with_default(Draft7Validator)

def validate_schema(parsed_data: dict) -> List[str]:
    validator = DefaultValidatingDraft7Validator(QUICKBASE_SCHEMA)
    errors = sorted(validator.iter_errors(parsed_data), key=lambda e: e.path)
    error_messages = []
    for error in errors:
        path = ".".join([str(elem) for elem in error.path])
        message = f"{path}: {error.message}" if path else error.message
        error_messages.append(message)
        logger.warning("Schema validation issue: %s", message)
    return error_messages

def validate_field_formats(parsed_data: dict) -> List[str]:
    error_messages = []
    phone_pattern = re.compile(r"^\+?1?\d{9,15}$")
    adjuster_info = parsed_data.get("Adjuster Information", {})
    contact_numbers = adjuster_info.get("Adjuster Phone Number", []) or []
    for idx, phone in enumerate(contact_numbers):
        if not phone_pattern.match(phone):
            message = f"Adjuster Information.Adjuster Phone Number[{idx}]: Invalid phone number format."
            error_messages.append(message)
            logger.warning(message)
    email_pattern = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
    adjuster_emails = adjuster_info.get("Adjuster Email", []) or []
    for idx, email in enumerate(adjuster_emails):
        if not email_pattern.match(email):
            message = f"Adjuster Information.Adjuster Email[{idx}]: Invalid email format."
            error_messages.append(message)
            logger.warning(message)
    return error_messages

def validate_dependencies(parsed_data: dict) -> List[str]:
    error_messages = []
    assignment_info = parsed_data.get("Assignment Information", {})
    residence_occupied = assignment_info.get("Residence Occupied During Loss", [])
    someone_home = assignment_info.get("Was Someone home at time of damage", [])
    if residence_occupied and someone_home:
        residence_occupied_value = residence_occupied[0] if isinstance(residence_occupied, list) else residence_occupied
        someone_home_value = someone_home[0] if isinstance(someone_home, list) else someone_home
        if residence_occupied_value is False and someone_home_value is True:
            message = f"Assignment Information.Residence Occupied During Loss is False, but Assignment Information.Was Someone home at time of damage is True."
            error_messages.append(message)
            logger.warning(message)
    return error_messages

def validate_internal(email_content: Optional[str], parsed_data: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    error_messages = []
    if email_content:
        # Additional validations against email content can be implemented here
        pass
    schema_errors = validate_schema(parsed_data)
    error_messages.extend(schema_errors)
    field_errors = validate_field_formats(parsed_data)
    error_messages.extend(field_errors)
    dependency_errors = validate_dependencies(parsed_data)
    error_messages.extend(dependency_errors)
    if error_messages:
        parsed_data["validation_issues"] = parsed_data.get("validation_issues", []) + error_messages
    return parsed_data

def validate_schema_internal(parsed_data: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    schema_errors = validate_schema(parsed_data)
    if schema_errors:
        parsed_data["validation_issues"] = parsed_data.get("validation_issues", []) + schema_errors
    return parsed_data

def validate_json(parsed_data: dict) -> Tuple[bool, str]:
    logger.info("Starting JSON validation against schema and additional rules.")
    error_messages = []
    schema_errors = validate_schema(parsed_data)
    error_messages.extend(schema_errors)
    field_errors = validate_field_formats(parsed_data)
    error_messages.extend(field_errors)
    dependency_errors = validate_dependencies(parsed_data)
    error_messages.extend(dependency_errors)
    required_fields = [
        "Requesting Party",
        "Insured Information",
        "Adjuster Information",
        "Assignment Information",
        "Assignment Type",
        "Additional details/Special Instructions",
        "Attachment(s)",
        "Entities",
        "TransformerEntities",
    ]
    for field in required_fields:
        if field not in parsed_data or not parsed_data[field]:
            message = f"Missing required field: {field}"
            error_messages.append(message)
            logger.warning(message)
    allowed_properties = set(QUICKBASE_SCHEMA.get("properties", {}).keys())
    actual_properties = set(parsed_data.keys())
    unexpected_properties = actual_properties - allowed_properties
    for prop in unexpected_properties:
        message = f"Unexpected property found: {prop}"
        error_messages.append(message)
        logger.warning(message)
    if error_messages:
        logger.debug("Validation completed with %d issues.", len(error_messages))
        return False, "\n".join(error_messages)
    logger.info("JSON validation successful. Parsed data conforms to the schema and additional rules.")
    return True, ""

def init_validation_model(
    logger: logging.Logger,
    config: Optional[Dict[str, Any]] = None,
    prompt_template: Optional[str] = None
) -> pipeline:
    """
    Initializes the validation pipeline using a pre-trained transformer model.
    
    Args:
        logger (logging.Logger): Logger instance.
        config (Optional[Dict[str, Any]]): Configuration dictionary for the validation model.
        prompt_template (Optional[str]): Prompt template for the validation model.
    
    Returns:
        pipeline: Initialized Hugging Face pipeline for validation.
    
    Raises:
        ValidationError: If initialization fails.
    """
    try:
        logger.info("Initializing Validation pipeline.")
        validation_config = config or Config.get_model_config("validation")
        model_id = validation_config.get("repo_id", "distilbert-base-uncased")
        task = validation_config.get("task", "text-classification")
        device_config = validation_config.get("device", "cuda")
        device = 0 if device_config == "cuda" and torch.cuda.is_available() else -1
        validation_pipeline = pipeline(
            task=task,
            model=model_id,
            tokenizer=model_id,
            device=device
        )
        if prompt_template:
            logger.debug("Using prompt template for validation: %s", prompt_template)
        logger.info("Validation pipeline initialized successfully.")
        return validation_pipeline
    except Exception as e:
        logger.error(f"Failed to initialize Validation pipeline: {e}", exc_info=True)
        raise ValidationError(f"Failed to initialize Validation pipeline: {e}") from e
