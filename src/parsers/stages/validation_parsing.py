from typing import Dict, Any, Optional
import logging
from src.utils.validation import validate_json, assignment_schema
import re

def validate_internal(
    email_content: str,
    parsed_data: Dict[str, Any],
    logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """
    Internal validation stage handler.

    Args:
        email_content (str): Raw email content.
        parsed_data (Dict[str, Any]): Currently parsed data.
        logger (Optional[logging.Logger]): Logger instance.

    Returns:
        Dict[str, Any]: Updated parsed data with validation results.
    """
    logger = logger or logging.getLogger(__name__)
    try:
        logger.debug("Starting internal validation.")
        # Ensure required sections are present
        required_sections = ["Requesting Party", "Insured Information", "Adjuster Information", "Assignment Information"]
        for section in required_sections:
            if section not in parsed_data:
                logger.error(f"Missing required section: {section}")
                parsed_data.setdefault("validation_issues", []).append(f"Missing required section: {section}")

        # Validate required fields within each section
        for section, fields in assignment_schema.get("properties", {}).items():
            if section in parsed_data:
                for field, field_props in fields.get("properties", {}).items():
                    if "required" in fields and field in fields["required"]:
                        value = parsed_data.get(section, {}).get(field)
                        if not value or (isinstance(value, list) and not any(value)):
                            logger.error(f"Missing required field: {section} -> {field}")
                            parsed_data.setdefault("validation_issues", []).append(f"Missing required field: {section} -> {field}")

        # Example Cross-Field Validation: If 'Is the insured an Owner' is True, 'Loss Address' must be present
        insured_status = parsed_data.get("Insured Information", {}).get("Is the insured an Owner or a Tenant of the loss location?")
        loss_address = parsed_data.get("Insured Information", {}).get("Loss Address")
        if insured_status and any(status.lower() == 'true' for status in insured_status):
            if not loss_address or not any(loss_address):
                logger.error("Loss Address is required when the insured is an Owner.")
                parsed_data.setdefault("validation_issues", []).append("Loss Address is required when the insured is an Owner.")

        # Additional custom validations can be added here

    except Exception as e:
        logger.error(f"Error during internal validation: {e}", exc_info=True)
    return parsed_data

def validate_schema_internal(
    parsed_data: Dict[str, Any],
    logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """
    Internal schema validation handler.

    Args:
        parsed_data (Dict[str, Any]): Data to validate against schema.
        logger (Optional[logging.Logger]): Logger instance.

    Returns:
        Dict[str, Any]: Updated parsed data with schema validation results.
    """
    logger = logger or logging.getLogger(__name__)
    try:
        logger.debug("Starting schema validation.")
        is_valid, error_message = validate_json(parsed_data)
        if not is_valid:
            logger.error(f"Schema validation failed: {error_message}")
            parsed_data.setdefault("validation_issues", []).append(f"Schema validation failed: {error_message}")
        else:
            logger.debug("Schema validation passed.")
    except Exception as e:
        logger.error(f"Error during schema validation: {e}", exc_info=True)
        parsed_data.setdefault("validation_issues", []).append(f"Schema validation error: {e}")
    return parsed_data
