import jsonschema
from jsonschema import Draft7Validator, validators, ValidationError
from transformers import pipeline
import logging
from typing import Tuple, List, Dict, Any
import re

logger = logging.getLogger("Validation")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def init_validation_model(logger: logging.Logger, config: Dict[str, Any], prompt_template: Optional[str] = None):
    try:
        logger.info("Initializing Validation Model pipeline.")
        
        # Load model
        validation_pipeline = pipeline(task=config['models']['validation']['task'], 
                                       model=config['models']['validation']['repo_id'],
                                       tokenizer=config['models']['validation']['repo_id'],
                                       device=0 if config['processing']['device'] == 'cuda' and torch.cuda.is_available() else -1)

        # Log the prompt if provided
        if prompt_template:
            logger.debug(f"Using prompt template for validation: {prompt_template}")
        
        logger.info("Validation model initialized successfully.")
        return validation_pipeline
    except Exception as e:
        logger.error(f"Failed to initialize validation model: {e}", exc_info=True)
        return None

def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

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
        "Requesting Party": {
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
        "Insured Information": {
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
        "Adjuster Information": {
            "type": "object",
            "properties": {
                "Adjuster Name": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                "Adjuster Phone Number": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                },
                "Adjuster Email": {
                    "type": ["array", "null"],
                    "items": {"type": "string", "format": "email"},
                },
                "Job Title": {"type": ["array", "null"], "items": {"type": "string"}},
                "Address": {"type": ["array", "null"], "items": {"type": "string"}},
                "Policy #": {"type": ["array", "null"], "items": {"type": "string"}},
            },
            "required": [
                "Adjuster Name",
                "Adjuster Phone Number",
                "Adjuster Email",
                "Job Title",
                "Address",
                "Policy #",
            ],
            "additionalProperties": False,
            "dependencies": {
                "Adjuster Name": ["Adjuster Email"],
                "Adjuster Email": ["Adjuster Name"],
            },
        },
        "Assignment Information": {
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
                "Residence Occupied During Loss": {
                    "type": ["array", "null"],
                    "items": {"type": "boolean"},
                },
                "Was Someone home at time of damage": {
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
                "Residence Occupied During Loss",
                "Was Someone home at time of damage",
                "Repair or Mitigation Progress",
                "Type",
                "Inspection type",
            ],
            "additionalProperties": False,
        },
        "Assignment Type": {
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
        "Additional details/Special Instructions": {
            "type": ["array", "null"],
            "items": {"type": "string"},
        },
        "Attachment(s)": {
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
        "Requesting Party",
        "Insured Information",
        "Adjuster Information",
        "Assignment Information",
        "Assignment Type",
        "Additional details/Special Instructions",
        "Attachment(s)",
        "Entities",
        "TransformerEntities",
    ],
    "additionalProperties": False,
    "if": {
        "properties": {
            "Adjuster Name": {"type": "array"},
        },
        "required": ["Adjuster Name"],
    },
    "then": {
        "properties": {
            "Adjuster Email": {"type": "array"},
        },
        "required": ["Adjuster Email"],
    },
    "else": {
        "properties": {
            "Adjuster Email": {"type": ["array", "null"]},
        },
    },
}

def validate_schema(parsed_data: dict) -> List[str]:
    validator = DefaultValidatingDraft7Validator(assignment_schema)
    errors = sorted(validator.iter_errors(parsed_data), key=lambda e: e.path)
    error_messages = []

    for error in errors:
        path = ".".join([str(elem) for elem in error.path])
        message = f"{path}: {error.message}" if path else error.message
        error_messages.append(message)
        logger.warning(f"Schema validation issue: {message}")

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

    return error_messages

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

    allowed_properties = set(assignment_schema.get("properties", {}).keys())
    actual_properties = set(parsed_data.keys())
    unexpected_properties = actual_properties - allowed_properties
    for prop in unexpected_properties:
        message = f"Unexpected property found: {prop}"
        error_messages.append(message)
        logger.warning(message)

    if error_messages:
        logger.debug(f"Validation completed with {len(error_messages)} issues.")
        return False, "\n".join(error_messages)

    logger.info("JSON validation successful. Parsed data conforms to the schema and additional rules.")
    return True, ""

def sanitize_parsed_data(parsed_data: dict) -> dict:
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
    inconsistent_fields = []
    return inconsistent_fields

def collect_user_notifications(parsed_data: dict) -> List[str]:
    notifications = []
    if "summary" not in parsed_data:
        notifications.append("Summary of services needed is missing.")
        logger.info("User notification added: Summary of services needed is missing.")
    return notifications

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
