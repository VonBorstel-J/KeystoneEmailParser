from typing import Dict, Any

QUICKBASE_SCHEMA: Dict[str, Dict[str, Dict[str, Any]]] = {
    "Requesting Party": {
        "Insurance Company": {
            "field_id": "field_1",
            "type": "string",
            "required": True,
            "enum": ["Allianz", "State Farm", "GEICO"],
            "description": "Name of the insurance company."
        },
        "Handler": {
            "field_id": "field_2",
            "type": "string",
            "required": True,
            "description": "Handler's name and contact information."
        },
        "Carrier Claim Number": {
            "field_id": "field_3",
            "type": "string",
            "required": True,
            "pattern": "^[A-Z0-9]{6,}$",
            "description": "Unique claim number assigned by the carrier."
        }
    },
    "Insured Information": {
        "Name": {
            "field_id": "field_4",
            "type": "string",
            "required": True,
            "description": "Full name of the insured individual."
        },
        "Contact #": {
            "field_id": "field_5",
            "type": "string",
            "required": True,
            "pattern": "^\\+?[1-9]\\d{1,14}$",
            "description": "Contact number of the insured."
        },
        "Loss Address": {
            "field_id": "field_6",
            "type": "string",
            "required": True,
            "description": "Address where the loss occurred."
        },
        "Public Adjuster": {
            "field_id": "field_7",
            "type": "string",
            "required": False,
            "description": "Information about the public adjuster, if any."
        },
        "Is the insured an Owner or a Tenant of the loss location?": {
            "field_id": "field_8",
            "type": "boolean",
            "required": True,
            "description": "Whether the insured is an owner or tenant of the loss location."
        }
    },
    "Adjuster Information": {
        "Adjuster Name": {
            "field_id": "field_9",
            "type": "string",
            "required": True,
            "description": "Name of the adjuster."
        },
        "Adjuster Phone Number": {
            "field_id": "field_10",
            "type": "string",
            "required": True,
            "pattern": "^\\+?[1-9]\\d{1,14}$",
            "description": "Phone number of the adjuster."
        },
        "Adjuster Email": {
            "field_id": "field_11",
            "type": "string",
            "required": True,
            "format": "email",
            "pattern": "^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$",
            "description": "Email address of the adjuster."
        },
        "Job Title": {
            "field_id": "field_12",
            "type": "string",
            "required": False,
            "description": "Job title of the adjuster."
        },
        "Address": {
            "field_id": "field_13",
            "type": "string",
            "required": False,
            "description": "Address of the adjuster."
        },
        "Policy #": {
            "field_id": "field_14",
            "type": "string",
            "required": True,
            "pattern": "^POL\\d{6}$",
            "description": "Policy number associated with the claim."
        }
    },
    "Assignment Information": {
        "Date of Loss/Occurrence": {
            "field_id": "field_15",
            "type": "string",
            "required": True,
            "format": "date",
            "description": "Date when the loss or occurrence happened."
        },
        "Cause of loss": {
            "field_id": "field_16",
            "type": "string",
            "required": True,
            "description": "Cause behind the loss."
        },
        "Facts of Loss": {
            "field_id": "field_17",
            "type": "string",
            "required": False,
            "description": "Detailed facts surrounding the loss."
        },
        "Loss Description": {
            "field_id": "field_18",
            "type": "string",
            "required": True,
            "description": "Description of the loss."
        },
        "Residence Occupied During Loss": {
            "field_id": "field_19",
            "type": "boolean",
            "required": True,
            "description": "Whether the residence was occupied during the loss."
        },
        "Was Someone home at time of damage": {
            "field_id": "field_20",
            "type": "boolean",
            "required": True,
            "description": "Whether someone was home at the time of damage."
        },
        "Repair or Mitigation Progress": {
            "field_id": "field_21",
            "type": "string",
            "required": False,
            "description": "Progress on repair or mitigation."
        },
        "Type": {
            "field_id": "field_22",
            "type": "string",
            "required": False,
            "enum": ["Wind", "Structural", "Hail", "Foundation", "Other"],
            "description": "Type of loss or claim."
        },
        "Inspection type": {
            "field_id": "field_23",
            "type": "string",
            "required": False,
            "description": "Type of inspection conducted."
        }
    },
    "Assignment Type": {
        "Wind": {
            "field_id": "field_24",
            "type": "boolean",
            "required": False,
            "description": "Wind-related damage."
        },
        "Structural": {
            "field_id": "field_25",
            "type": "boolean",
            "required": False,
            "description": "Structural damage."
        },
        "Hail": {
            "field_id": "field_26",
            "type": "boolean",
            "required": False,
            "description": "Hail-related damage."
        },
        "Foundation": {
            "field_id": "field_27",
            "type": "boolean",
            "required": False,
            "description": "Foundation-related damage."
        },
        "Other": {
            "field_id": "field_28",
            "type": "object",
            "required": False,
            "description": "Other types of damage.",
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
        "required": False,
        "description": "Any additional details or special instructions."
    },
    "Attachment(s)": {
        "field_id": "field_30",
        "type": "array",
        "items": {
            "type": "string",
            "format": "uri"
        },
        "required": False,
        "description": "List of attachments related to the email."
    },
    "Entities": {
        "field_id": "field_31",
        "type": "object",
        "additionalProperties": {
            "type": "array",
            "items": {"type": "string"},
        },
        "description": "Entity extraction results"
    },
    "TransformerEntities": {
        "field_id": "field_32",
        "type": "object",
        "additionalProperties": {
            "type": "array",
            "items": {"type": "string"},
        },
        "description": "Transformer model entity extraction results"
    },
    "missing_fields": {
        "field_id": "field_33",
        "type": "array",
        "items": {"type": "string"},
        "description": "List of missing required fields"
    },
    "inconsistent_fields": {
        "field_id": "field_34",
        "type": "array",
        "items": {"type": "string"},
        "description": "List of fields with inconsistent values"
    },
    "user_notifications": {
        "field_id": "field_35",
        "type": "array",
        "items": {"type": "string"},
        "description": "User notifications and warnings"
    }
}