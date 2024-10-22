# src/utils/validation.py

import jsonschema
from jsonschema import Draft7Validator
import logging

# Define the QuickBase schema based on importSchema.txt
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
                    "items": {"type": "string"},
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
        },
        "Assignment Information": {
            "type": "object",
            "properties": {
                "Date of Loss/Occurrence": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                    "format": "date",
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
}


def validate_json(parsed_data: dict) -> (bool, str):
    """
    Validate the parsed data against the QuickBase schema.

    Args:
        parsed_data (dict): The parsed data to validate.

    Returns:
        tuple: (is_valid (bool), error_message (str))
    """
    logger = logging.getLogger("Validation")
    validator = Draft7Validator(assignment_schema)
    errors = sorted(validator.iter_errors(parsed_data), key=lambda e: e.path)

    if errors:
        error_messages = [
            f"{'.'.join(map(str, error.path))}: {error.message}" for error in errors
        ]
        logger.error(f"Validation failed with errors: {error_messages}")
        return False, "\n".join(error_messages)
    logger.debug("Validation successful. Parsed data conforms to the schema.")
    return True, ""
