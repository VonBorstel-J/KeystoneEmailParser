# src/parsers/base_parser.py

import logging
from typing import Any, Dict, Optional, Union
from PIL import Image

from src.utils.config import Config

class BaseParser:
    """Base class for all parsers implementing common functionality."""
    
    def __init__(self):
        """Initialize base parser with configuration."""
        self.logger = logging.getLogger(self.__class__.__name__)
        Config.initialize()  # Ensure configuration is loaded
        self._setup_base_config()

    def _setup_base_config(self):
        """Set up basic configuration settings."""
        try:
            # Get processing configuration
            processing_config = Config.get_processing_config()
            self.batch_size = processing_config.get("batch_size", 1)
            self.max_length = processing_config.get("max_length", 512)
            
            # Set up device
            self.device = Config.get_device()
            self.fallback_to_cpu = Config.should_fallback_to_cpu()
            
            # Set up optimization flags
            self.enable_amp = Config.is_amp_enabled()
            self.optimize_memory = Config.should_optimize_memory()
            
        except Exception as e:
            self.logger.error(f"Failed to set up base configuration: {e}", exc_info=True)
            raise

    def parse(self, *args, **kwargs) -> Dict[str, Any]:
        """Abstract method for parsing. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement parse method")

    def health_check(self) -> bool:
        """Basic health check implementation."""
        return True

    def cleanup(self):
        """Base cleanup method."""
        pass

    def validate_input(self, email_content: Optional[str] = None,
                      document_image: Optional[Union[str, Image.Image]] = None) -> bool:
        """
        Validate input based on configuration settings.
        
        Args:
            email_content (Optional[str]): Email content to validate
            document_image (Optional[Union[str, Image.Image]]): Image to validate
            
        Returns:
            bool: True if input is valid, False otherwise
        """
        try:
            if document_image:
                valid_extensions = Config.get_valid_extensions()
                if isinstance(document_image, str):
                    ext = document_image.lower().split('.')[-1]
                    if f".{ext}" not in valid_extensions:
                        self.logger.error(f"Invalid file extension: .{ext}")
                        return False
                        
            return True
        except Exception as e:
            self.logger.error(f"Input validation error: {e}", exc_info=True)
            return False