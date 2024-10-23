import logging
from typing import Dict, Any
import re
from datetime import datetime

def post_process_parsed_data(parsed_data: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """
    Cleans and normalizes the parsed data.

    Args:
        parsed_data (Dict[str, Any]): Parsed data from previous stages.
        logger (logging.Logger): Logger instance.

    Returns:
        Dict[str, Any]: Post-processed data.
    """
    try:
        logger.debug("Starting post-processing of parsed data.")
        for section, fields in parsed_data.items():
            if isinstance(fields, dict):
                for field, values in fields.items():
                    if isinstance(values, list):
                        # Deduplicate values
                        unique_values = list(set(values))
                        parsed_data[section][field] = unique_values
                        logger.debug(f"Deduplicated field '{field}' in section '{section}': {unique_values}")

                        # Normalize data
                        if "Date" in field or "date" in field.lower():
                            parsed_data[section][field] = [normalize_date(v, logger) for v in unique_values]
                        elif "Phone" in field:
                            parsed_data[section][field] = [normalize_phone_number(v, logger) for v in unique_values]
                        elif "Email" in field:
                            parsed_data[section][field] = [v.lower() for v in unique_values if validate_email(v)]
        logger.debug("Post-processing completed successfully.")
    except Exception as e:
        logger.error(f"Error during post-processing: {e}", exc_info=True)
    return parsed_data

def normalize_date(date_str: str, logger: logging.Logger) -> str:
    """
    Normalizes date strings to ISO format.

    Args:
        date_str (str): Date string to normalize.
        logger (logging.Logger): Logger instance.

    Returns:
        str: Normalized date string or original string if parsing fails.
    """
    from src.utils.config_loader import ConfigLoader
    config = ConfigLoader.load_config()
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
    """
    Normalizes phone numbers to a standard format.

    Args:
        phone_str (str): Phone number string to normalize.
        logger (logging.Logger): Logger instance.

    Returns:
        str: Normalized phone number or original string if parsing fails.
    """
    try:
        # Example: Normalize to E.164 format
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

def validate_email(email: str) -> bool:
    """
    Validates email format.

    Args:
        email (str): Email string to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.match(regex, email) is not None
