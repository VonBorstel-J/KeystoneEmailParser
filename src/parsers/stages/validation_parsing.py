from typing import Dict, Any, Optional, List
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
        insured_status = parsed_data.get("Insured Information", {}).get("Ownership_Status")
        loss_address = parsed_data.get("Insured Information", {}).get("Loss_Address")
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

def validate_dependencies(parsed_data: dict, logger: Optional[logging.Logger] = None) -> List[str]:
    """
    Validates conditional dependencies between fields.

    Args:
        parsed_data (dict): The data to validate.
        logger (Optional[logging.Logger]): Logger instance.

    Returns:
        List[str]: A list of dependency validation error messages.
    """
    logger = logger or logging.getLogger(__name__)
    error_messages = []

    # Example: If "Residence Occupied During Loss" is False, "Was Someone home at time of damage" should also be False
    assignment_info = parsed_data.get("Assignment Information", {})
    residence_occupied = assignment_info.get("Residence_Occupied")
    someone_home = assignment_info.get("Someone_Home")

    if residence_occupied and someone_home:
        residence_occupied_value = (
            residence_occupied[0]
            if isinstance(residence_occupied, list)
            else residence_occupied
        )
        someone_home_value = (
            someone_home[0] if isinstance(someone_home, list) else someone_home
        )

        if residence_occupied_value is False and someone_home_value is True:
            message = (
                "Assignment Information.Residence Occupied During Loss is False, "
                "but Was Someone home at time of damage is True."
            )
            error_messages.append(message)
            logger.warning(message)

    # Add more dependency validations as needed

    return error_messages

def final_validation(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    logger = logging.getLogger("Validation")
    try:
        logger.info("Performing final validation pass.")
        is_valid, errors = validate_json(parsed_data)

        validated_data = parsed_data.copy()
        validated_data["missing_fields"] = get_missing_required_fields(parsed_data)
        validated_data["inconsistent_fields"] = get_inconsistent_fields(parsed_data)
        validated_data["low_confidence_fields"] = get_low_confidence_fields(parsed_data)
        validated_data["validation_errors"] = errors.split("\n") if not is_valid else []

        logger.info("Final validation completed.")
        return validated_data
    except Exception as e:
        logger.error(f"Error during final validation: {e}", exc_info=True)
        return parsed_data

def get_missing_required_fields(parsed_data: Dict[str, Any]) -> List[str]:
    """
    Identifies any missing required fields based on the schema.

    Args:
        parsed_data (dict): The data to check.

    Returns:
        List[str]: A list of missing required fields.
    """
    missing_fields = []
    for section, fields in assignment_schema.get("properties", {}).items():
        if section in parsed_data:
            for field, field_props in fields.get("properties", {}).items():
                if "required" in fields and field in fields["required"]:
                    value = parsed_data.get(section, {}).get(field)
                    if not value or (isinstance(value, list) and not any(value)):
                        missing_fields.append(f"{section}.{field}")
    return missing_fields

def get_inconsistent_fields(parsed_data: Dict[str, Any]) -> List[str]:
    """
    Identifies any inconsistent fields based on custom validation rules.

    Args:
        parsed_data (dict): The data to check.

    Returns:
        List[str]: A list of inconsistent fields.
    """
    # Placeholder for custom consistency checks
    # Implement as needed based on business logic
    inconsistent_fields = []
    return inconsistent_fields

def get_low_confidence_fields(parsed_data: Dict[str, Any], threshold: float = 0.7) -> List[str]:
    low_confidence_fields = []
    for section, fields in parsed_data.items():
        if isinstance(fields, dict):
            for field, values in fields.items():
                if isinstance(values, list):
                    for value in values:
                        if isinstance(value, dict) and 'confidence' in value:
                            if value['confidence'] < threshold:
                                low_confidence_fields.append(f"{section}.{field}")
                                break
    return low_confidence_fields
