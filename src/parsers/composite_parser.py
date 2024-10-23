# src/parsers/composite_parser.py

from transformers import Pipeline
from typing import Optional, Any, Dict

class CompositeParser:
    def __init__(
        self,
        ner: Optional[Pipeline] = None,
        donut_processor: Optional[Any] = None,
        donut_model: Optional[Any] = None,
        validation: Optional[Pipeline] = None,
        summarization: Optional[Pipeline] = None,
    ):
        """
        Initializes the CompositeParser with various parser components.

        Args:
            ner (Optional[Pipeline]): Named Entity Recognition pipeline.
            donut_processor (Optional[Any]): Donut processor.
            donut_model (Optional[Any]): Donut model.
            validation (Optional[Pipeline]): Validation pipeline.
            summarization (Optional[Pipeline]): Summarization pipeline.
        """
        self.ner = ner
        self.donut_processor = donut_processor
        self.donut_model = donut_model
        self.validation = validation
        self.summarization = summarization

    def health_check(self) -> bool:
        """
        Performs a health check on all parser components.

        Returns:
            bool: True if all components are healthy, False otherwise.
        """
        try:
            if self.ner:
                self.ner("Test")
            if self.donut_processor and self.donut_model:
                # Example minimal operation for Donut
                pass
            if self.validation:
                self.validation("Test")
            if self.summarization:
                self.summarization("Test")
            return True
        except Exception as e:
            return False

    def parse_email(self, email_content: str, document_image: Optional[Any] = None) -> Dict[str, Any]:
        """
        Parses the email content and document image using the respective parsers.

        Args:
            email_content (str): The email content to parse.
            document_image (Optional[Any]): The document image to parse.

        Returns:
            Dict[str, Any]: Parsed results from all parser components.
        """
        results = {}

        if self.ner:
            entities = self.ner(email_content)
            results['entities'] = entities

        if self.donut_processor and self.donut_model and document_image:
            # Example processing for Donut
            inputs = self.donut_processor(images=document_image, return_tensors="pt")
            outputs = self.donut_model.generate(**inputs)
            decoded = self.donut_processor.batch_decode(outputs, skip_special_tokens=True)
            results['document'] = decoded

        if self.validation:
            validation_result = self.validation(email_content)
            results['validation'] = validation_result

        if self.summarization:
            summary = self.summarization(email_content)
            results['summary'] = summary

        return results
