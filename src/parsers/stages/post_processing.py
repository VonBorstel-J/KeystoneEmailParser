# src/parsers/stages/post_processing.py

import logging
from typing import Dict, Any, List
import re
from datetime import datetime
from src.utils.config import Config

def post_process_parsed_data(parsed_data: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    try:
        logger.debug("Starting post-processing of parsed data.")
        processed_data = {}
        for section, fields in parsed_data.items():
            if isinstance(fields, dict):
                processed_section = {}
                for field, values in fields.items():
                    processed_values = []
                    if isinstance(values, list):
                        for value in values:
                            if isinstance(value, dict) and 'value' in value:
                                processed_value = normalize_value(value['value'], field, logger)
                                confidence = value.get('confidence', 1.0)
                                processed_values.append({"value": processed_value, "confidence": confidence})
                            else:
                                processed_value = normalize_value(value, field, logger)
                                processed_values.append({"value": processed_value, "confidence": 1.0})
                    else:
                        processed_value = normalize_value(values, field, logger)
                        processed_values.append({"value": processed_value, "confidence": 1.0})
                    processed_section[field] = processed_values
                processed_data[section] = processed_section
            else:
                processed_data[section] = fields
        logger.debug("Post-processing completed successfully.")
        return processed_data
    except Exception as e:
        logger.error(f"Error during post-processing: {e}", exc_info=True)
        return parsed_data

def normalize_value(value: Any, field: str, logger: logging.Logger) -> Any:
    if "date" in field.lower():
        return normalize_date(value, logger)
    elif "phone" in field.lower():
        return normalize_phone_number(value, logger)
    elif "email" in field.lower():
        return value.lower() if isinstance(value, str) else value
    return value

def normalize_date(date_str: str, logger: logging.Logger) -> str:
    config = Config.get_full_config()
    date_formats = config.get("date_formats", [])
    for fmt in date_formats:
        try:
            normalized_date = datetime.strptime(date_str, fmt).isoformat()
            logger.debug(f"Normalized date '{date_str}' to '{normalized_date}'.")
            return normalized_date
        except ValueError:
            continue
    logger.warning(f"Failed to normalize date: {date_str}")
    return date_str

def normalize_phone_number(phone_str: str, logger: logging.Logger) -> str:
    try:
        phone_digits = re.sub(r'\D', '', phone_str)
        if len(phone_digits) == 10:
            normalized_phone = f"+1{phone_digits}"
            logger.debug(f"Normalized phone '{phone_str}' to '{normalized_phone}'.")
            return normalized_phone
        else:
            logger.warning(f"Unexpected phone number format: {phone_str}")
            return phone_str
    except Exception as e:
        logger.error(f"Error normalizing phone number '{phone_str}': {e}", exc_info=True)
        return phone_str

def validate_against_email(parsed_data: Dict[str, Any], email_content: str, logger: logging.Logger) -> List[str]:
    errors = []
    key_fields = {
        'claim_number': parsed_data.get('Requesting_Party', {}).get('Carrier_Claim_Number', []),
        'adjuster_name': parsed_data.get('Adjuster_Information', {}).get('Adjuster_Name', []),
        'date_of_loss': parsed_data.get('Assignment_Information', {}).get('Date_of_Loss/Occurrence', []),
    }
    for field_name, parsed_values in key_fields.items():
        if not parsed_values:
            errors.append(f"Missing key field: {field_name}")
            logger.warning(f"Missing key field: {field_name} in parsed data")
            continue
        for value in parsed_values:
            if value not in email_content:
                errors.append(f"Mismatch for field '{field_name}': Parsed value '{value}' not found in email content")
                logger.warning(f"Mismatch for field '{field_name}': Parsed value '{value}' not found in email content")
    return errors
