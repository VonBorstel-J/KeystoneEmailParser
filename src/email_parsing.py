# src/email_parsing.py

from src.parsers.parser_registry import ParserRegistry
from src.parsers.parser_options import ParserOption
from src.utils.validation import validate_json
from typing import Dict, Any


class EmailParser:
    """
    EmailParser handles the selection and usage of different parsing strategies.
    """

    def __init__(self):
        pass  # Initialization logic if needed

    def parse_email(self, email_content: str, parser_option: ParserOption, socketio, sid) -> Dict[str, Any]:
        """
        Parse the email content using the specified parser option.

        Args:
            email_content (str): The raw email content to parse.
            parser_option (ParserOption): The parser option to use.
            socketio: The SocketIO instance for emitting events.
            sid: The session ID of the connected client.

        Returns:
            Dict[str, Any]: Parsed data as a dictionary.
        """
        if not isinstance(parser_option, ParserOption):
            raise TypeError("parser_option must be an instance of ParserOption Enum.")

        parser_instance = ParserRegistry.get_parser(
            parser_option, socketio=socketio, sid=sid
        )
        parsed_data = parser_instance.parse(email_content)

        # Validate the parsed data against a JSON schema
        is_valid, error_message = validate_json(parsed_data)
        if not is_valid:
            raise ValueError(f"Parsed data validation failed: {error_message}")

        return parsed_data

    # Optional: Implement CSV conversion if required
    # def convert_to_csv(self, parsed_data: dict) -> Tuple[str, str]:
    #     # Conversion logic here
    #     pass
