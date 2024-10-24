# src/utils/email_utils.py

import email
from email.header import decode_header
from bs4 import BeautifulSoup
from typing import Tuple, List
import logging

logger = logging.getLogger(__name__)

def decode_email_header(header: str) -> str:
    try:
        decoded_header = decode_header(header)
        return ' '.join([text.decode(encoding or 'utf-8') if isinstance(text, bytes) else text for text, encoding in decoded_header])
    except Exception as e:
        logger.error(f"Error decoding email header: {e}", exc_info=True)
        return header

def extract_email_content(msg) -> Tuple[str, List[Tuple[str, bytes]]]:
    body = ""
    attachments = []
    try:
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body += part.get_payload(decode=True).decode()
            elif part.get_content_type() == "text/html":
                soup = BeautifulSoup(part.get_payload(decode=True), 'html.parser')
                body += soup.get_text()
            elif part.get_content_maintype() == 'image':
                filename = part.get_filename()
                attachments.append((filename, part.get_payload(decode=True)))
    except Exception as e:
        logger.error(f"Error extracting email content: {e}", exc_info=True)
    return body, attachments

def parse_email(email_content: str) -> Tuple[str, str, str, List[Tuple[str, bytes]]]:
    try:
        msg = email.message_from_string(email_content)
        subject = decode_email_header(msg['Subject'])
        from_address = decode_email_header(msg['From'])
        body, attachments = extract_email_content(msg)
        return subject, from_address, body, attachments
    except Exception as e:
        logger.error(f"Error parsing email: {e}", exc_info=True)
        return "", "", "", []

