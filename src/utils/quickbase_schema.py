# src/utils/quickbase_schema.py

from typing import Dict, Any

# Comprehensive mapping of parsed data keys to QuickBase field IDs with validation rules
QUICKBASE_SCHEMA: Dict[str, Dict[str, Dict[str, Any]]] = {
    "Requesting Party": {
        "Insurance Company": {
            "field_id": "field_1",
            "type": "string",
            "required": True,
            "enum": ["Allianz", "State Farm", "GEICO"]  
        },
        "Handler": {
            "field_id": "field_2",
            "type": "string",
            "required": True
        },
        "Carrier Claim Number": {
            "field_id": "field_3",
            "type": "string",
            "required": True,
            "pattern": "^[A-Z0-9]{6,}$"  
        }
    },
    "Insured Information": {
        "Name": {
            "field_id": "field_4",
            "type": "string",
            "required": True
        },
        "Contact #": {
            "field_id": "field_5",
            "type": "string",
            "required": True,
            "pattern": "^\\+?[1-9]\\d{1,14}$"  
        },
        "Loss Address": {
            "field_id": "field_6",
            "type": "string",
            "required": True
        },
        "Public Adjuster": {
            "field_id": "field_7",
            "type": "string",
            "required": False
        },
        "Is the insured an Owner or a Tenant of the loss location?": {
            "field_id": "field_8",
            "type": "boolean",
            "required": True
        }
    },
    "Adjuster Information": {
        "Adjuster Name": {
            "field_id": "field_9",
            "type": "string",
            "required": True
        },
        "Adjuster Phone Number": {
            "field_id": "field_10",
            "type": "string",
            "required": True,
            "pattern": "^\\+?[1-9]\\d{1,14}$"  
        },
        "Adjuster Email": {
            "field_id": "field_11",
            "type": "string",
            "required": True,
            "format": "email"
        },
        "Job Title": {
            "field_id": "field_12",
            "type": "string",
            "required": False
        },
        "Address": {
            "field_id": "field_13",
            "type": "string",
            "required": False
        },
        "Policy #": {
            "field_id": "field_14",
            "type": "string",
            "required": True,
            "pattern": "^POL\\d{6}$"  
        }
    },
    "Assignment Information": {
        "Date of Loss/Occurrence": {
            "field_id": "field_15",
            "type": "string",
            "required": True,
            "format": "date"
        },
        "Cause of loss": {
            "field_id": "field_16",
            "type": "string",
            "required": True
        },
        "Facts of Loss": {
            "field_id": "field_17",
            "type": "string",
            "required": False
        },
        "Loss Description": {
            "field_id": "field_18",
            "type": "string",
            "required": True
        },
        "Residence Occupied During Loss": {
            "field_id": "field_19",
            "type": "boolean",
            "required": True
        },
        "Was Someone home at time of damage": {
            "field_id": "field_20",
            "type": "boolean",
            "required": True
        },
        "Repair or Mitigation Progress": {
            "field_id": "field_21",
            "type": "string",
            "required": False
        },
        "Type": {
            "field_id": "field_22",
            "type": "string",
            "required": False,
            "enum": ["Wind", "Structural", "Hail", "Foundation", "Other"]
        },
        "Inspection type": {
            "field_id": "field_23",
            "type": "string",
            "required": False
        }
    },
    "Assignment Type": {
        "Wind": {
            "field_id": "field_24",
            "type": "boolean",
            "required": False
        },
        "Structural": {
            "field_id": "field_25",
            "type": "boolean",
            "required": False
        },
        "Hail": {
            "field_id": "field_26",
            "type": "boolean",
            "required": False
        },
        "Foundation": {
            "field_id": "field_27",
            "type": "boolean",
            "required": False
        },
        "Other": {
            "field_id": "field_28",
            "type": "object",
            "required": False,
            "properties": {
                "Checked": {
                    "type": "boolean",
                    "required": True
                },
                "Details": {
                    "type": "string",
                    "required": False
                }
            },
            "additionalProperties": False
        }
    },
    "Additional details/Special Instructions": {
        "field_id": "field_29",
        "type": "string",
        "required": False
    },
    "Attachment(s)": {
        "field_id": "field_30",
        "type": "array",
        "items": {
            "type": "string",
            "format": "uri"  
        },
        "required": False
    },
    "Entities": {
        "field_id": "field_31",
        "type": "object",
        "additionalProperties": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "TransformerEntities": {
        "field_id": "field_32",
        "type": "object",
        "additionalProperties": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "missing_fields": {
        "field_id": "field_33",
        "type": "array",
        "items": {"type": "string"}
    },
    "inconsistent_fields": {
        "field_id": "field_34",
        "type": "array",
        "items": {"type": "string"}
    },
    "user_notifications": {
        "field_id": "field_35",
        "type": "array",
        "items": {"type": "string"},
    },
}

