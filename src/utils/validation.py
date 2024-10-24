from src.utils.config import Config
from jsonschema import Draft7Validator, validators
from transformers import pipeline
import logging
from typing import Optional, Tuple, List, Dict, Any
import torch
import re

# Define constants for repeated strings
REQUESTING_PARTY = "Requesting Party"
INSURED_INFORMATION = "Insured Information"
ADJUSTER_INFORMATION = "Adjuster Information"
ADJUSTER_NAME = "Adjuster Name"
ADJUSTER_PHONE_NUMBER = "Adjuster Phone Number"
ADJUSTER_EMAIL = "Adjuster Email"
ASSIGNMENT_INFORMATION = "Assignment Information"
RESIDENCE_OCCUPIED_DURING_LOSS = "Residence Occupied During Loss"
WAS_SOMEONE_HOME_AT_TIME_OF_DAMAGE = "Was Someone home at time of damage"
ASSIGNMENT_TYPE = "Assignment Type"
ADDITIONAL_DETAILS_SPECIAL_INSTRUCTIONS = "Additional details/Special Instructions"
ATTACHMENTS = "Attachment(s)"

logger = logging.getLogger("Validation")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def init_validation_model(
    logger: logging.Logger,
    prompt_template: Optional[str] = None,
) -> Optional[Any]:
    """
    Initialize the validation model pipeline.

    Args:
        logger (logging.Logger): Logger instance.
        prompt_template (Optional[str]): Optional prompt template.

    Returns:
        Optional[Any]: The initialized pipeline or None if failed.
    """
    try:
        logger.info("Initializing Validation Model pipeline.")
        
        # Get config from Config singleton
        config = Config.get_model_config("validation")
        if not config:
            raise ValueError("Validation model configuration not found")

        # Load model
        device = Config.get_device("validation")
        
        validation_pipeline = pipeline(
            task=config["task"],
            model=config["repo_id"],
            tokenizer=config["repo_id"],
            device=0 if device == "cuda" and torch.cuda.is_available() else -1
        )

        # Log the prompt if provided
        if prompt_template:
            logger.debug("Using prompt template: %s", prompt_template)

        logger.info("Validation model initialized successfully.")
        return validation_pipeline
    except Exception as e:
        logger.error("Failed to initialize validation model: %s", e, exc_info=True)
        return None


def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property_name, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(property_name, subschema["default"])

        for error in validate_properties(
            validator,
            properties,
            instance,
            schema,
        ):
            yield error

    return validators.extend(
        validator_class,
        {"properties": set_defaults},
    )


DefaultValidatingDraft7Validator = extend_with_default(Draft7Validator)

assignment_schema = {
    "type": "object",
    "properties": {
        REQUESTING_PARTY: {
            "type": "object",
            "properties": {
                "Insurance Company": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                "Handler": {"type": ["array", "null"], "items": {"type": "string"}},
                "Carrier Claim Number": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
            },
            "required": ["Insurance Company", "Handler", "Carrier Claim Number"],
            "additionalProperties": False,
        },
        INSURED_INFORMATION: {
            "type": "object",
            "properties": {
                "Name": {"type": ["array", "null"], "items": {"type": "string"}},
                "Contact #": {"type": ["array", "null"], "items": {"type": "string"}},
                "Loss Address": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                "Public Adjuster": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                "Is the insured an Owner or a Tenant of the loss location?": {
                    "type": ["array", "null"],
                    "items": {"type": "boolean"},
                },
            },
            "required": [
                "Name",
                "Contact #",
                "Loss Address",
                "Public Adjuster",
                "Is the insured an Owner or a Tenant of the loss location?",
            ],
            "additionalProperties": False,
        },
        ADJUSTER_INFORMATION: {
            "type": "object",
            "properties": {
                ADJUSTER_NAME: {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                ADJUSTER_PHONE_NUMBER: {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                ADJUSTER_EMAIL: {
                    "type": ["array", "null"],
                    "items": {"type": "string", "format": "email"},
                },
                "Job Title": {"type": ["array", "null"], "items": {"type": "string"}},
                "Address": {"type": ["array", "null"], "items": {"type": "string"}},
                "Policy #": {"type": ["array", "null"], "items": {"type": "string"}},
            },
            "required": [
                ADJUSTER_NAME,
                ADJUSTER_PHONE_NUMBER,
                ADJUSTER_EMAIL,
                "Job Title",
                "Address",
                "Policy #",
            ],
            "additionalProperties": False,
            "dependencies": {
                ADJUSTER_NAME: [ADJUSTER_EMAIL],
                ADJUSTER_EMAIL: [ADJUSTER_NAME],
            },
        },
        ASSIGNMENT_INFORMATION: {
            "type": "object",
            "properties": {
                "Date of Loss/Occurrence": {
                    "type": ["array", "null"],
                    "items": {"type": "string", "format": "date"},
                },
                "Cause of loss": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                "Facts of Loss": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                "Loss Description": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                RESIDENCE_OCCUPIED_DURING_LOSS: {
                    "type": ["array", "null"],
                    "items": {"type": "boolean"},
                },
                WAS_SOMEONE_HOME_AT_TIME_OF_DAMAGE: {
                    "type": ["array", "null"],
                    "items": {"type": "boolean"},
                },
                "Repair or Mitigation Progress": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                "Type": {"type": ["array", "null"], "items": {"type": "string"}},
                "Inspection type": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
            },
            "required": [
                "Date of Loss/Occurrence",
                "Cause of loss",
                "Facts of Loss",
                "Loss Description",
                RESIDENCE_OCCUPIED_DURING_LOSS,
                WAS_SOMEONE_HOME_AT_TIME_OF_DAMAGE,
                "Repair or Mitigation Progress",
                "Type",
                "Inspection type",
            ],
            "additionalProperties": False,
        },
        ASSIGNMENT_TYPE: {
            "type": "object",
            "properties": {
                "Wind": {"type": ["array", "null"], "items": {"type": "boolean"}},
                "Structural": {"type": ["array", "null"], "items": {"type": "boolean"}},
                "Hail": {"type": ["array", "null"], "items": {"type": "boolean"}},
                "Foundation": {"type": ["array", "null"], "items": {"type": "boolean"}},
                "Other": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "Checked": {"type": ["boolean", "null"]},
                            "Details": {"type": ["string", "null"]},
                        },
                        "required": ["Checked", "Details"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["Wind", "Structural", "Hail", "Foundation", "Other"],
            "additionalProperties": False,
        },
        ADDITIONAL_DETAILS_SPECIAL_INSTRUCTIONS: {
            "type": ["array", "null"],
            "items": {"type": "string"},
        },
        ATTACHMENTS: {
            "type": "array",
            "items": {"type": "string", "format": "uri"},
        },
        "Entities": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "TransformerEntities": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "missing_fields": {"type": "array", "items": {"type": "string"}},
        "inconsistent_fields": {"type": "array", "items": {"type": "string"}},
        "user_notifications": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        REQUESTING_PARTY,
        INSURED_INFORMATION,
        ADJUSTER_INFORMATION,
        ASSIGNMENT_INFORMATION,
        ASSIGNMENT_TYPE,
        ADDITIONAL_DETAILS_SPECIAL_INSTRUCTIONS,
        ATTACHMENTS,
        "Entities",
        "TransformerEntities",
    ],
    "additionalProperties": False,
    "if": {
        "properties": {
            ADJUSTER_NAME: {"type": "array"},
        },
        "required": [ADJUSTER_NAME],
    },
    "then": {
        "properties": {
            ADJUSTER_EMAIL: {"type": "array"},
        },
        "required": [ADJUSTER_EMAIL],
    },
    "else": {
        "properties": {
            ADJUSTER_EMAIL: {"type": ["array", "null"]},
        },
    },
}


def validate_schema(parsed_data: dict) -> List[str]:
    """
    Validate parsed data against the JSON schema.

    Args:
        parsed_data (dict): The data to validate.

    Returns:
        List[str]: List of error messages.
    """
    validator = DefaultValidatingDraft7Validator(assignment_schema)
    errors = sorted(validator.iter_errors(parsed_data), key=lambda e: e.path)
    error_messages = []

    for error in errors:
        path = ".".join([str(elem) for elem in error.path])
        message = f"{path}: {error.message}" if path else error.message
        error_messages.append(message)
        logger.warning("Schema validation issue: %s", message)

    return error_messages


def validate_field_formats(parsed_data: dict) -> List[str]:
    """
    Validate the formats of specific fields like phone numbers and emails.

    Args:
        parsed_data (dict): The data to validate.

    Returns:
        List[str]: List of error messages.
    """
    error_messages = []
    phone_pattern = re.compile(r"^\+?1?\d{9,15}$")
    adjuster_info = parsed_data.get(ADJUSTER_INFORMATION, {})
    contact_numbers = adjuster_info.get(ADJUSTER_PHONE_NUMBER, []) or []
    for idx, phone in enumerate(contact_numbers):
        if not phone_pattern.match(phone):
            message = f"{ADJUSTER_INFORMATION}.{ADJUSTER_PHONE_NUMBER}[{idx}]: Invalid phone number format."
            error_messages.append(message)
            logger.warning(message)

    email_pattern = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
    adjuster_emails = adjuster_info.get(ADJUSTER_EMAIL, []) or []
    for idx, email in enumerate(adjuster_emails):
        if not email_pattern.match(email):
            message = (
                f"{ADJUSTER_INFORMATION}.{ADJUSTER_EMAIL}[{idx}]: Invalid email format."
            )
            error_messages.append(message)
            logger.warning(message)

    return error_messages


def validate_dependencies(parsed_data: dict) -> List[str]:
    """
    Validate inter-field dependencies within the parsed data.

    Args:
        parsed_data (dict): The data to validate.

    Returns:
        List[str]: List of error messages.
    """
    error_messages = []
    assignment_info = parsed_data.get(ASSIGNMENT_INFORMATION, {})
    residence_occupied = assignment_info.get(RESIDENCE_OCCUPIED_DURING_LOSS, [])
    someone_home = assignment_info.get(WAS_SOMEONE_HOME_AT_TIME_OF_DAMAGE, [])

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
                f"{ASSIGNMENT_INFORMATION}.{RESIDENCE_OCCUPIED_DURING_LOSS} is False, "
                f"but {ASSIGNMENT_INFORMATION}.{WAS_SOMEONE_HOME_AT_TIME_OF_DAMAGE} is True."
            )
            error_messages.append(message)
            logger.warning(message)

    return error_messages


def validate_json(parsed_data: dict) -> Tuple[bool, str]:
    """
    Perform comprehensive validation on the parsed JSON data.

    Args:
        parsed_data (dict): The data to validate.

    Returns:
        Tuple[bool, str]: Validation status and error messages.
    """
    logger.info("Starting JSON validation against schema and additional rules.")
    error_messages = []

    schema_errors = validate_schema(parsed_data)
    error_messages.extend(schema_errors)

    field_errors = validate_field_formats(parsed_data)
    error_messages.extend(field_errors)

    dependency_errors = validate_dependencies(parsed_data)
    error_messages.extend(dependency_errors)

    required_fields = [
        REQUESTING_PARTY,
        INSURED_INFORMATION,
        ADJUSTER_INFORMATION,
        ASSIGNMENT_INFORMATION,
        ASSIGNMENT_TYPE,
        ADDITIONAL_DETAILS_SPECIAL_INSTRUCTIONS,
        ATTACHMENTS,
        "Entities",
        "TransformerEntities",
    ]
    for field in required_fields:
        if field not in parsed_data or not parsed_data[field]:
            message = f"Missing required field: {field}"
            error_messages.append(message)
            logger.warning(message)

    allowed_properties = set(assignment_schema.get("properties", {}).keys())
    actual_properties = set(parsed_data.keys())
    unexpected_properties = actual_properties - allowed_properties
    for prop in unexpected_properties:
        message = f"Unexpected property found: {prop}"
        error_messages.append(message)
        logger.warning(message)

    if error_messages:
        logger.debug("Validation completed with %d issues.", len(error_messages))
        return False, "\n".join(error_messages)

    logger.info(
        "JSON validation successful. Parsed data conforms to the schema and additional rules."
    )
    return True, ""


def sanitize_parsed_data(parsed_data: dict) -> dict:
    """
    Sanitize the parsed data by removing nulls and empty values.

    Args:
        parsed_data (dict): The data to sanitize.

    Returns:
        dict: Sanitized data.
    """
    def sanitize(obj):
        if isinstance(obj, dict):
            return {
                k: sanitize(v) for k, v in obj.items() if v not in [None, [], {}, ""]
            }
        elif isinstance(obj, list):
            return [sanitize(item) for item in obj if item not in [None, [], {}, ""]]
        else:
            return obj

    sanitized_data = sanitize(parsed_data)
    logger.debug("Sanitized parsed data by removing nulls and empty values.")
    return sanitized_data


def get_missing_required_fields(parsed_data: dict) -> List[str]:
    """
    Retrieve a list of missing required fields from the parsed data.

    Args:
        parsed_data (dict): The data to check.

    Returns:
        List[str]: List of missing required fields.
    """
    validator = Draft7Validator(assignment_schema)
    missing_fields = sorted(
        error.message
        for error in validator.iter_errors(parsed_data)
        if error.validator == "required"
    )
    for field in missing_fields:
        logger.warning(f"Missing required field: {field}")
    return missing_fields


def get_inconsistent_fields(parsed_data: dict) -> List[str]:
    """
    Retrieve a list of inconsistent fields from the parsed data.

    Args:
        parsed_data (dict): The data to check.

    Returns:
        List[str]: List of inconsistent fields.
    """
    inconsistent_fields = []
    # Implement logic for detecting inconsistent fields if any
    return inconsistent_fields


def collect_user_notifications(parsed_data: dict) -> List[str]:
    """
    Collect user notifications based on the parsed data.

    Args:
        parsed_data (dict): The data to check.

    Returns:
        List[str]: List of user notifications.
    """
    notifications = []
    if "summary" not in parsed_data:
        notifications.append("Summary of services needed is missing.")
        logger.info("User notification added: Summary of services needed is missing.")
    return notifications


def final_validation(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform the final validation and augment the parsed data with validation results.

    Args:
        parsed_data (Dict[str, Any]): The data to validate.

    Returns:
        Dict[str, Any]: The validated and augmented data.
    """
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
        logger.error("Error during final validation: %s", e, exc_info=True)
        return parsed_data


def get_low_confidence_fields(
    parsed_data: Dict[str, Any], threshold: float = 0.7
) -> List[str]:
    """
    Identify fields with low confidence scores.

    Args:
        parsed_data (Dict[str, Any]): The data to check.
        threshold (float): The confidence threshold.

    Returns:
        List[str]: List of fields with low confidence.
    """
    low_confidence_fields = []
    for section, fields in parsed_data.items():
        if isinstance(fields, dict):
            for field, values in fields.items():
                if isinstance(values, list):
                    for value in values:
                        if isinstance(value, dict) and "confidence" in value:
                            if value["confidence"] < threshold:
                                low_confidence_fields.append(f"{section}.{field}")
                                break
    return low_confidence_fields
