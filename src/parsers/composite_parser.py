# src/parsers/composite_parser.py

from typing import Optional, Dict, Any, Tuple
from PIL import Image
import torch
import logging

class CompositeParser:
    def __init__(self, ner, donut_processor, donut_model, validation, summarization):
        self.ner = ner
        self.donut_processor = donut_processor
        self.donut_model = donut_model
        self.validation = validation
        self.summarization = summarization

    def __enter__(self):
        # Initialize resources if needed
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup resources if needed
        pass

    def parse_email(self, email_content: str, document_image: Optional[Image.Image] = None) -> Dict[str, Any]:
        """
        Implements the multi-stage parsing process.

        Args:
            email_content (str): The content of the email.
            document_image (Optional[Image.Image]): The document image.

        Returns:
            Dict[str, Any]: The aggregated parsed data.
        """
        parsed_data = {}

        # NER Parsing
        if self.ner:
            logging.debug("Starting NER Parsing.")
            ner_results = self.ner(email_content)
            parsed_data['entities'] = ner_results
            logging.debug("NER Parsing completed.")

        # Donut Parsing
        if self.donut_model and self.donut_processor and document_image:
            logging.debug("Starting Donut Parsing.")
            inputs = self.donut_processor(images=document_image, return_tensors="pt")
            outputs = self.donut_model.generate(**inputs)
            donut_results = self.donut_processor.batch_decode(outputs, skip_special_tokens=True)
            parsed_data['donut'] = donut_results
            logging.debug("Donut Parsing completed.")

        # Validation
        if self.validation:
            logging.debug("Starting Validation.")
            validation_results = self.validation(email_content, parsed_data)
            parsed_data['validation'] = validation_results
            logging.debug("Validation completed.")

        # Summarization
        if self.summarization:
            logging.debug("Starting Summarization.")
            summary = self.summarization(email_content, max_length=142)
            parsed_data['summary'] = summary
            logging.debug("Summarization completed.")

        return parsed_data

    def health_check(self) -> bool:
        """
        Perform health checks for all parser components.

        Returns:
            bool: True if all components are healthy, False otherwise.
        """
        try:
            if self.ner is None:
                return False
            if self.donut_model is None or self.donut_processor is None:
                return False
            if self.validation is None:
                return False
            if self.summarization is None:
                return False
            # Add more detailed checks as needed
            return True
        except Exception as e:
            logging.error("Health check failed: %s", e)
            return False
