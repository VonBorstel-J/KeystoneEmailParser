import logging
from typing import Dict, Any, List
import re
from datetime import datetime
from src.utils.config import Config

def post_process_parsed_data(parsed_data: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """
    Post-processes parsed data by normalizing values and ensuring all fields are processed.
    Handles missing fields by logging them for potential capture by subsequent stages.
    """
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
                            # Ensure value is processed even if it’s None
                            if isinstance(value, dict) and 'value' in value:
                                processed_value = normalize_value(value.get('value'), field, logger)
                                confidence = value.get('confidence', 0.5)  # Conservative default confidence
                                processed_values.append({"value": processed_value, "confidence": confidence})
                            else:
                                processed_value = normalize_value(value, field, logger)
                                processed_values.append({"value": processed_value, "confidence": 0.5})
                    else:
                        processed_value = normalize_value(values, field, logger)
                        processed_values.append({"value": processed_value, "confidence": 0.5})
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
    """
    Normalize values like dates, phone numbers, and emails.
    """
    if value is None:
        logger.debug(f"Skipping normalization for None value in field: {field}")
        return value  # If value is None, return it as is
    
    if "date" in field.lower():
        return normalize_date(value, logger)
    elif "phone" in field.lower():
        return normalize_phone_number(value, logger)
    elif "email" in field.lower():
        return value.lower() if isinstance(value, str) else value
    return value

def normalize_date(date_str: str, logger: logging.Logger) -> str:
    config = Config.get_full_config()
    date_formats = config.get("date_formats", ["%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"])  # Add common date formats here
    for fmt in date_formats:
        try:
            normalized_date = datetime.strptime(date_str, fmt).isoformat()
            logger.debug(f"Normalized date '{date_str}' to '{normalized_date}'.")
            return normalized_date
        except ValueError:
            continue
    logger.warning(f"Failed to normalize date: {date_str}")
    return date_str  # Return original if no format matched

def normalize_phone_number(phone_str: str, logger: logging.Logger) -> str:
    """
    Normalize phone numbers to the +1XXXXXXXXXX format if possible.
    """
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
    """
    Validate key fields in parsed data against the original email content.
    """
    errors = []
    key_fields = {
        'claim_number': parsed_data.get('Requesting Party', {}).get('Carrier Claim Number', []),
        'adjuster_name': parsed_data.get('Adjuster Information', {}).get('Adjuster Name', []),
        'date_of_loss': parsed_data.get('Assignment Information', {}).get('Date of Loss/Occurrence', []),
    }
    
    # Compare parsed values to email content for mismatches
    for field_name, parsed_values in key_fields.items():
        if not parsed_values:
            errors.append(f"Missing key field: {field_name}")
            logger.warning(f"Missing key field: {field_name} in parsed data")
            continue
        for value in parsed_values:
            if isinstance(value, dict):
                value = value.get('value')  # Handle nested values
            if value and value not in email_content:
                errors.append(f"Mismatch for field '{field_name}': Parsed value '{value}' not found in email content")
                logger.warning(f"Mismatch for field '{field_name}': Parsed value '{value}' not found in email content")
    
    return errors
