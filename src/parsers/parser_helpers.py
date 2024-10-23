# src/parsers/parser_helpers.py

import re
from typing import Any
import dateutil.parser
import phonenumbers
from PIL import Image


def format_date(date_string: str) -> str:
    """
    Formats a date string to 'YYYY-MM-DD'. Returns 'N/A' if formatting fails.

    Args:
        date_string (str): The date string to format.

    Returns:
        str: The formatted date or 'N/A'.
    """
    if date_string == "N/A":
        return date_string
    try:
        parsed_date = dateutil.parser.parse(date_string)
        formatted_date = parsed_date.strftime("%Y-%m-%d")
        return formatted_date
    except (ValueError, TypeError):
        return "N/A"


def format_phone_number(phone_number: str) -> str:
    """
    Formats a phone number to the international format. Returns 'N/A' if invalid.

    Args:
        phone_number (str): The phone number to format.

    Returns:
        str: The formatted phone number or 'N/A'.
    """
    try:
        parsed_number = phonenumbers.parse(phone_number, "US")  # Assuming US
        if phonenumbers.is_valid_number(parsed_number):
            formatted_number = phonenumbers.format_number(
                parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
            return formatted_number
        else:
            return "N/A"
    except phonenumbers.NumberParseException:
        return "N/A"


def clean_text(text: str) -> str:
    """
    Cleans and normalizes text by removing unnecessary characters and formatting.

    Args:
        text (str): The text to clean.

    Returns:
        str: The cleaned and normalized text.
    """
    if not isinstance(text, str):
        return text
    text = " ".join(text.split())
    text = re.sub(r"_{2,}", "", text)
    text = re.sub(r"\[cid:[^\]]+\]", "", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"([.!?])\1+", r"\1", text)
    text = re.sub(r'["“”]', '"', text)  # Simplified quote normalization
    return text.strip()


def format_address(address: str) -> str:
    """
    Formats an address string by normalizing spaces, commas, and state abbreviations.

    Args:
        address (str): The address string to format.

    Returns:
        str: The formatted address.
    """
    if not isinstance(address, str):
        return address
    address = re.sub(r"\s+", " ", address.strip())
    address = re.sub(r"\s*,\s*", ", ", address)
    state_pattern = r"\b([A-Za-z]{2})\b\s*(\d{5}(?:-\d{4})?)?$"
    match = re.search(state_pattern, address)
    if match:
        state = match.group(1)
        if len(state) == 2:
            address = (
                address[: match.start(1)] + state.upper() + address[match.end(1) :]
            )
    return address
