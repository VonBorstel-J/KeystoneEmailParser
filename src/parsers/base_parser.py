# src/parsers/base_parser.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from PIL import Image

class BaseParser(ABC):
    @abstractmethod
    def parse_email(
        self, 
        email_content: Optional[str] = None,
        document_image: Optional[Union[str, Image.Image]] = None
    ) -> Dict[str, Any]:
        """Parse email content and/or document image.

        Args:
            email_content (Optional[str]): The email content to parse
            document_image (Optional[Union[str, Image.Image]]): Image to parse

        Returns:
            Dict[str, Any]: Parsed data dictionary
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, bool]:
        """Check health status of parser components.

        Returns:
            Dict[str, bool]: Status of each component
        """
        pass
