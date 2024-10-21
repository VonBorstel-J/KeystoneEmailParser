"""
Enhanced Parser with Linter Fixes

This file contains the EnhancedParser class with modifications to address linter warnings and errors.
"""

import logging
import os
import re
from typing import Optional, Dict, Any, List, Union
from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as ConcurrentTimeoutError,
)

import torch
from PIL import Image
from transformers import pipeline, DonutProcessor, VisionEncoderDecoderModel
from huggingface_hub import hf_hub_download, login
from thefuzz import fuzz
import phonenumbers
from phonenumbers import PhoneNumberFormat

from src.parsers.base_parser import BaseParser
from src.utils.validation import validate_json
from src.utils.config_loader import ConfigLoader
from src.utils.quickbase_schema import QUICKBASE_SCHEMA

# Define a timeout constant for long-running LLM processes
LLM_TIMEOUT_SECONDS = 500


# Custom exception for handling timeouts
class TimeoutException(Exception):
    """Exception raised when a timeout occurs."""


class EnhancedParser(BaseParser):
    """
    EnhancedParser class extends the BaseParser to implement advanced parsing techniques
    using various NLP and computer vision models. It orchestrates the parsing stages and
    handles exceptions, logging, and validations throughout the process.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        # Initialize the logger
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.logger.info("Initializing EnhancedParser.")

        try:
            # Load configuration settings
            self.config = ConfigLoader.load_config()
            self.logger.debug("Loaded configuration: %s", self.config)

            # Check for required environment variables
            self._check_environment_variables()

            # Initialize model attributes to None for lazy loading
            self.ner_pipeline: Optional[pipeline] = None
            self.donut_processor: Optional[DonutProcessor] = None
            self.donut_model: Optional[VisionEncoderDecoderModel] = None
            self.sequence_model_pipeline: Optional[pipeline] = None
            self.validation_pipeline: Optional[pipeline] = None

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.logger.info("Using device: %s", self.device)

            self.logger.info("EnhancedParser initialized successfully.")
        except Exception as e:
            self.logger.error(
                "Error during EnhancedParser initialization: %s", e, exc_info=True
            )
            # Re-raise the exception to prevent initialization in a degraded state
            raise

    def _check_environment_variables(self):
        required_vars = ["HF_TOKEN"]  # Add other required variables here
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            self.logger.error(
                "Missing required environment variables: %s", ", ".join(missing_vars)
            )
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

    def _get_model_path(self, repo_id: str, filename: str) -> str:
        """
        Downloads the model file from Hugging Face Hub if not already cached.

        Args:
            repo_id (str): The repository ID on Hugging Face Hub.
            filename (str): The filename to download.

        Returns:
            str: The local path to the downloaded file.
        """
        try:
            self.logger.debug("Checking cache for model '%s/%s'.", repo_id, filename)
            model_path = hf_hub_download(
                repo_id=repo_id, filename=filename, cache_dir=".cache"
            )
            self.logger.debug(
                "Model '%s/%s' is available at '%s'.", repo_id, filename, model_path
            )
            return model_path
        except Exception as e:
            self.logger.error(
                "Failed to download model '%s/%s': %s",
                repo_id,
                filename,
                e,
                exc_info=True,
            )
            raise

    def _lazy_load_ner(self):
        if self.ner_pipeline is None:
            self.init_ner()

    def _lazy_load_donut(self):
        if self.donut_model is None or self.donut_processor is None:
            self.init_donut()

    def _lazy_load_sequence_model(self):
        if self.sequence_model_pipeline is None:
            self.init_sequence_model()

    def _lazy_load_validation_model(self):
        if self.validation_pipeline is None:
            self.init_validation_model()

    def init_ner(self):
        """
        Initialize the Named Entity Recognition (NER) pipeline using a pre-trained model.
        """
        try:
            self.logger.info("Initializing NER pipeline.")
            repo_id = "dslim/bert-base-NER"
            model_path = self._get_model_path(repo_id, "pytorch_model.bin")
            tokenizer_path = self._get_model_path(repo_id, "tokenizer.json")
            self.ner_pipeline = pipeline(
                "ner",
                model=model_path,
                tokenizer=tokenizer_path,
                aggregation_strategy="simple",
                device=0 if self.device == "cuda" else -1,
            )
            self.logger.info("Loaded NER model '%s' successfully.", repo_id)
        except MemoryError:
            self.logger.critical(
                "MemoryError: Not enough memory to load the NER model.", exc_info=True
            )
            self.ner_pipeline = None
        except Exception as e:
            self.logger.error(
                "Failed to load NER model '%s': %s", repo_id, e, exc_info=True
            )
            self.ner_pipeline = None

    def init_donut(self):
        """
        Initialize the Donut model and processor for OCR-free document parsing.
        """
        try:
            self.logger.info("Initializing Donut model and processor.")
            repo_id = "naver-clova-ix/donut-base-finetuned-cord-v2"
            processor_path = self._get_model_path(repo_id, "processor_config.json")
            model_path = self._get_model_path(repo_id, "pytorch_model.bin")
            self.donut_processor = DonutProcessor.from_pretrained(
                repo_id, cache_dir=".cache"
            )
            self.donut_model = VisionEncoderDecoderModel.from_pretrained(
                repo_id, cache_dir=".cache"
            )
            self.donut_model.to(self.device)
            self.logger.info("Loaded Donut model '%s' successfully.", repo_id)
        except MemoryError:
            self.logger.critical(
                "MemoryError: Not enough memory to load the Donut model.", exc_info=True
            )
            self.donut_model = None
            self.donut_processor = None
        except Exception as e:
            self.logger.error(
                "Failed to load Donut model '%s': %s", repo_id, e, exc_info=True
            )
            self.donut_model = None
            self.donut_processor = None

    def init_sequence_model(self):
        """
        Initialize the Sequence Model pipeline using a pre-trained model for summarization.
        """
        try:
            self.logger.info("Initializing Sequence Model pipeline.")
            repo_id = "facebook/bart-large"
            model_path = self._get_model_path(repo_id, "pytorch_model.bin")
            tokenizer_path = self._get_model_path(repo_id, "tokenizer.json")
            self.sequence_model_pipeline = pipeline(
                "summarization",
                model=model_path,
                tokenizer=tokenizer_path,
                device=0 if self.device == "cuda" else -1,
            )
            self.logger.info("Loaded Sequence Model '%s' successfully.", repo_id)
        except MemoryError:
            self.logger.critical(
                "MemoryError: Not enough memory to load the Sequence Model.",
                exc_info=True,
            )
            self.sequence_model_pipeline = None
        except Exception as e:
            self.logger.error(
                "Failed to load Sequence Model '%s': %s", repo_id, e, exc_info=True
            )
            self.sequence_model_pipeline = None

    def init_validation_model(self):
        """
        Initialize the Validation Model pipeline using a pre-trained model for text generation.
        """
        try:
            self.logger.info("Initializing Validation Model pipeline.")

            # Retrieve the Hugging Face token from environment variables
            hf_token = os.getenv("HF_TOKEN")
            if not hf_token:
                raise ValueError(
                    "Hugging Face token not found in environment variables."
                )

            # Login to Hugging Face Hub using the token
            login(token=hf_token)
            self.logger.info("Logged in to Hugging Face Hub successfully.")

            repo_id = "gpt2"
            model_path = self._get_model_path(repo_id, "pytorch_model.bin")
            tokenizer_path = self._get_model_path(repo_id, "tokenizer.json")
            self.validation_pipeline = pipeline(
                "text-generation",
                model=model_path,
                tokenizer=tokenizer_path,
                device=0 if self.device == "cuda" else -1,
            )
            self.logger.info("Loaded Validation Model '%s' successfully.", repo_id)
        except MemoryError:
            self.logger.critical(
                "MemoryError: Not enough memory to load the Validation Model.",
                exc_info=True,
            )
            self.validation_pipeline = None
        except Exception as e:
            self.logger.error("Failed to load Validation Model: %s", e, exc_info=True)
            self.validation_pipeline = None

    def parse(
        self,
        email_content: Optional[str] = None,
        document_image: Optional[Union[str, Image.Image]] = None,
    ) -> Dict[str, Any]:
        """
        Orchestrates the parsing process by executing each parsing stage sequentially.

        Args:
            email_content (Optional[str]): The raw email content to be parsed.
            document_image (Optional[Union[str, Image.Image]]): The path to the document image or a PIL Image object.

        Returns:
            Dict[str, Any]: A dictionary containing the parsed data.
        """
        self.logger.info("Starting parsing process.")
        parsed_data: Dict[str, Any] = {}

        # List of parsing stages with their corresponding methods
        stages = [
            (
                "Regex Extraction",
                self._stage_regex_extraction,
                {"email_content": email_content},
            ),
            ("NER Parsing", self._stage_ner_parsing, {"email_content": email_content}),
            (
                "Donut Parsing",
                self._stage_donut_parsing,
                {"document_image": document_image},
            ),
            (
                "Sequence Model Parsing",
                self._stage_sequence_model_parsing,
                {"email_content": email_content},
            ),
            (
                "Validation Parsing",
                self._stage_validation,
                {"email_content": email_content, "parsed_data": parsed_data},
            ),
            (
                "Schema Validation",
                self._stage_schema_validation,
                {"parsed_data": parsed_data},
            ),
            (
                "Post Processing",
                self._stage_post_processing,
                {"parsed_data": parsed_data},
            ),
            (
                "JSON Validation",
                self._stage_json_validation,
                {"parsed_data": parsed_data},
            ),
        ]

        for stage_name, stage_method, kwargs in stages:
            try:
                if stage_name == "Donut Parsing" and not document_image:
                    self.logger.warning(
                        "No document image provided for Donut parsing. Skipping this stage."
                    )
                    continue
                if stage_name.startswith("Stage"):
                    # Skip if already handled
                    continue

                self.logger.info("Stage: %s", stage_name)
                stage_result = stage_method(**kwargs)
                if isinstance(stage_result, dict) and stage_result:
                    parsed_data = self.merge_parsed_data(parsed_data, stage_result)
            except Exception as e:
                self.logger.error(
                    "Error in stage '%s': %s", stage_name, e, exc_info=True
                )
                # Continue to next stage without halting the pipeline

        self.logger.info("Parsing process completed.")
        return parsed_data

    def merge_parsed_data(
        self, original_data: Dict[str, Any], new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merges new parsed data into the original data, combining lists and avoiding duplicates.

        Args:
            original_data (Dict[str, Any]): The original parsed data.
            new_data (Dict[str, Any]): The new parsed data to merge.

        Returns:
            Dict[str, Any]: The merged parsed data.
        """
        for section, fields in new_data.items():
            if section not in original_data:
                original_data[section] = fields
            else:
                for field, value in fields.items():
                    if field not in original_data[section]:
                        original_data[section][field] = value
                    else:
                        if isinstance(
                            original_data[section][field], list
                        ) and isinstance(value, list):
                            combined_list = original_data[section][field] + value
                            # Remove duplicates while preserving order
                            seen = set()
                            original_data[section][field] = [
                                x
                                for x in combined_list
                                if not (x in seen or seen.add(x))
                            ]
                        else:
                            # Overwrite with the new value
                            original_data[section][field] = value
        return original_data

    def _stage_regex_extraction(
        self, email_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the Regex Extraction parsing stage.

        Args:
            email_content (Optional[str]): The email content to parse.

        Returns:
            Dict[str, Any]: Parsed data from Regex Extraction.
        """
        if not email_content:
            self.logger.warning("No email content provided for Regex Extraction.")
            return {}
        self.logger.debug("Executing Regex Extraction stage.")
        return self.regex_extraction(email_content)

    def _stage_ner_parsing(self, email_content: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes the NER Parsing stage.

        Args:
            email_content (Optional[str]): The email content to parse.

        Returns:
            Dict[str, Any]: Parsed data from NER Parsing.
        """
        if not email_content:
            self.logger.warning("No email content provided for NER Parsing.")
            return {}
        self.logger.debug("Executing NER Parsing stage.")
        try:
            self._lazy_load_ner()
            if self.ner_pipeline is None:
                self.logger.warning(
                    "NER pipeline is not available. Skipping NER Parsing."
                )
                return {}
            return self.ner_parsing
        except Exception as e:
            self.logger.error("Error during NER Parsing stage: %s", e, exc_info=True)
            return {}

    def _stage_donut_parsing(
        self, document_image: Optional[Union[str, Image.Image]] = None
    ) -> Dict[str, Any]:
        """
        Executes the Donut Parsing stage.

        Args:
            document_image (Optional[Union[str, Image.Image]]): The path to the document image or a PIL Image object.

        Returns:
            Dict[str, Any]: Parsed data from Donut Parsing.
        """
        if not document_image:
            self.logger.warning("No document image provided for Donut Parsing.")
            return {}
        self.logger.debug("Executing Donut Parsing stage.")
        try:
            self._lazy_load_donut()
            if self.donut_model is None or self.donut_processor is None:
                self.logger.warning(
                    "Donut model or processor is not available. Skipping Donut Parsing."
                )
                return {}
            return self.donut_parsing(document_image)
        except Exception as e:
            self.logger.error("Error during Donut Parsing stage: %s", e, exc_info=True)
            return {}

    def _stage_sequence_model_parsing(
        self, email_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the Sequence Model Parsing stage with timeout handling.

        Args:
            email_content (Optional[str]): The email content to parse.

        Returns:
            Dict[str, Any]: Parsed data from Sequence Model Parsing.
        """
        if not email_content:
            self.logger.warning("No email content provided for Sequence Model Parsing.")
            return {}
        self.logger.debug("Executing Sequence Model Parsing stage.")
        try:
            self._lazy_load_sequence_model()
            if self.sequence_model_pipeline is None:
                self.logger.warning(
                    "Sequence Model pipeline is not available. Skipping Sequence Model Parsing."
                )
                return {}
            return self.sequence_model_parsing_with_timeout(email_content)
        except Exception as e:
            self.logger.error(
                "Error during Sequence Model Parsing stage: %s", e, exc_info=True
            )
            return {}

    def sequence_model_parsing_with_timeout(self, email_content: str) -> Dict[str, Any]:
        """
        Executes the Sequence Model parsing with timeout management.

        Args:
            email_content (str): The email content to parse.

        Returns:
            Dict[str, Any]: Parsed data from the Sequence Model.
        """
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.sequence_model_parsing, email_content)
                summary = future.result(timeout=LLM_TIMEOUT_SECONDS)
                return summary
        except ConcurrentTimeoutError:
            self.logger.error("Sequence Model parsing timed out.", exc_info=True)
            return {}
        except Exception as e:
            self.logger.error(
                "Error during Sequence Model parsing with timeout: %s", e, exc_info=True
            )
            return {}

    def sequence_model_parsing(self, email_content: str) -> Dict[str, Any]:
        """
        Executes the Sequence Model parsing.

        Args:
            email_content (str): The email content to parse.

        Returns:
            Dict[str, Any]: Parsed data from the Sequence Model.
        """
        self.logger.debug("Starting Sequence Model pipeline.")
        try:
            summary = self.sequence_model_pipeline(
                email_content,
                max_length=150,
                min_length=40,
                do_sample=False,
            )
            summary_text = summary[0]["summary_text"]
            self.logger.debug("Sequence Model Summary: %s", summary_text)
            return self.sequence_model_extract(summary_text)
        except Exception as e:
            self.logger.error(
                "Error during Sequence Model inference: %s", e, exc_info=True
            )
            return {}

    def _stage_validation(
        self,
        email_content: Optional[str] = None,
        parsed_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Executes the Validation Parsing stage.

        Args:
            email_content (Optional[str]): The original email content.
            parsed_data (Optional[Dict[str, Any]]): The data parsed so far.
        """
        if not email_content or not parsed_data:
            self.logger.warning(
                "Insufficient data for Validation Parsing. Skipping this stage."
            )
            return
        self.logger.debug("Executing Validation Parsing stage.")
        try:
            self._lazy_load_validation_model()
            if self.validation_pipeline is None:
                self.logger.warning(
                    "Validation Model pipeline is not available. Skipping Validation Parsing."
                )
                return
            self.validation_parsing(email_content, parsed_data)
        except Exception as e:
            self.logger.error(
                "Error during Validation Parsing stage: %s", e, exc_info=True
            )

    def _stage_schema_validation(self, parsed_data: Optional[Dict[str, Any]] = None):
        """
        Executes the Schema Validation stage.

        Args:
            parsed_data (Optional[Dict[str, Any]]): The data to validate.
        """
        if not parsed_data:
            self.logger.warning(
                "No parsed data available for Schema Validation. Skipping this stage."
            )
            return
        self.logger.debug("Executing Schema Validation stage.")
        try:
            self._stage_schema_validation_internal(parsed_data)
        except Exception as e:
            self.logger.error(
                "Error during Schema Validation stage: %s", e, exc_info=True
            )

    def _stage_post_processing(
        self, parsed_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes the Post Processing stage.

        Args:
            parsed_data (Optional[Dict[str, Any]]): The data to post-process.

        Returns:
            Dict[str, Any]: The post-processed data.
        """
        if not parsed_data:
            self.logger.warning(
                "No parsed data available for Post Processing. Skipping this stage."
            )
            return {}
        self.logger.debug("Executing Post Processing stage.")
        try:
            return self._stage_post_processing_internal(parsed_data)
        except Exception as e:
            self.logger.error(
                "Error during Post Processing stage: %s", e, exc_info=True
            )
            return parsed_data

    def _stage_schema_validation_internal(self, parsed_data: Dict[str, Any]):
        """
        Internal method to validate parsed data against the schema.

        Args:
            parsed_data (Dict[str, Any]): The data to validate.
        """
        self.logger.debug("Starting schema validation.")
        missing_fields: List[str] = []
        inconsistent_fields: List[str] = []

        try:
            # Iterate over the schema to check for missing and inconsistent fields
            for section, fields in QUICKBASE_SCHEMA.items():
                for field in fields:
                    value = parsed_data.get(section, {}).get(field)
                    if not value or value == ["N/A"]:
                        missing_fields.append(f"{section} -> {field}")
                        self.logger.debug("Missing field: %s -> %s", section, field)
                        continue

                    # Perform fuzzy matching for known values
                    known_values = self.config.get("known_values", {}).get(field, [])
                    if known_values:
                        best_match = max(
                            known_values,
                            key=lambda x: fuzz.partial_ratio(
                                x.lower(), value[0].lower()
                            ),
                            default=None,
                        )
                        if best_match and fuzz.partial_ratio(
                            best_match.lower(), value[0].lower()
                        ) >= self.config.get("fuzzy_threshold", 90):
                            parsed_data[section][field] = [best_match]
                            self.logger.debug(
                                "Updated %s in %s with best match: %s",
                                field,
                                section,
                                best_match,
                            )
                        else:
                            inconsistent_fields.append(f"{section} -> {field}")
                            self.logger.debug(
                                "Inconsistent field: %s -> %s with value %s",
                                section,
                                field,
                                value,
                            )

            # Add missing and inconsistent fields to parsed data
            if missing_fields:
                parsed_data["missing_fields"] = missing_fields
                self.logger.info("Missing fields identified: %s", missing_fields)

            if inconsistent_fields:
                parsed_data["inconsistent_fields"] = inconsistent_fields
                self.logger.info(
                    "Inconsistent fields identified: %s", inconsistent_fields
                )
        except Exception as e:
            self.logger.error("Error during schema validation: %s", e, exc_info=True)

    def _stage_post_processing_internal(
        self, parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Internal method to perform post-processing on parsed data.

        Args:
            parsed_data (Dict[str, Any]): The data to post-process.

        Returns:
            Dict[str, Any]: The post-processed data.
        """
        self.logger.debug("Starting post-processing of parsed data.")
        skip_sections = [
            "TransformerEntities",
            "Entities",
            "missing_fields",
            "inconsistent_fields",
            "user_notifications",
            "validation_issues",
        ]

        try:
            # Iterate over sections and fields to format dates and phone numbers
            for section, fields in parsed_data.items():
                if section in skip_sections:
                    continue
                if not isinstance(fields, dict):
                    continue

                for field, value_list in fields.items():
                    if not isinstance(value_list, list):
                        continue
                    for idx, value in enumerate(value_list):
                        if "Date" in field:
                            formatted_date = self.format_date(value)
                            parsed_data[section][field][idx] = formatted_date
                            self.logger.debug(
                                "Formatted date for %s in %s: %s",
                                field,
                                section,
                                formatted_date,
                            )
                        if (
                            "Phone Number" in field
                            or "Contact #" in field
                            or "Phone" in field
                        ):
                            formatted_phone = self.format_phone_number(value)
                            parsed_data[section][field][idx] = formatted_phone
                            self.logger.debug(
                                "Formatted phone number for %s in %s: %s",
                                field,
                                section,
                                formatted_phone,
                            )

            # Verify attachments if mentioned
            attachments = parsed_data.get("Assignment Information", {}).get(
                "Attachment(s)", []
            )
            if attachments and not self.verify_attachments(
                attachments, parsed_data.get("email_content", "")
            ):
                parsed_data["user_notifications"] = parsed_data.get(
                    "user_notifications", []
                ) + ["Attachments mentioned but not found in the email."]
                self.logger.info(
                    "Attachments mentioned in email but not found. User notification added."
                )

            self.logger.debug("Post-processing completed.")
            return parsed_data
        except Exception as e:
            self.logger.error("Error during post-processing: %s", e, exc_info=True)
            return parsed_data

    def _stage_json_validation(self, parsed_data: Optional[Dict[str, Any]] = None):
        """
        Executes the JSON Validation stage.

        Args:
            parsed_data (Optional[Dict[str, Any]]): The data to validate.
        """
        if not parsed_data:
            self.logger.warning(
                "No parsed data available for JSON Validation. Skipping this stage."
            )
            return
        self.logger.debug("Executing JSON Validation stage.")
        try:
            self._stage_json_validation_internal(parsed_data)
        except Exception as e:
            self.logger.error(
                "Error during JSON Validation stage: %s", e, exc_info=True
            )

    def _stage_json_validation_internal(self, parsed_data: Dict[str, Any]):
        """
        Internal method to validate parsed data against a JSON schema.

        Args:
            parsed_data (Dict[str, Any]): The data to validate.
        """
        self.logger.debug("Starting JSON validation.")
        try:
            is_valid, error_message = validate_json(parsed_data)
            if is_valid:
                self.logger.info("JSON validation passed.")
            else:
                self.logger.error("JSON validation failed: %s", error_message)
                parsed_data["validation_issues"] = parsed_data.get(
                    "validation_issues", []
                ) + [error_message]
        except Exception as e:
            self.logger.error("Error during JSON validation: %s", e, exc_info=True)
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(e)]

    def parse_email(
        self,
        email_content: Optional[str] = None,
        document_image: Optional[Union[str, Image.Image]] = None,
    ) -> Dict[str, Any]:
        """
        Parses the email content and document image using the enhanced parser.

        Args:
            email_content (Optional[str]): The email content to parse.
            document_image (Optional[Union[str, Image.Image]]): The path to the document image or a PIL Image object.

        Returns:
            Dict[str, Any]: The parsed data.
        """
        self.logger.info("parse_email called.")
        return self.parse(email_content=email_content, document_image=document_image)

    def ner_parsing(self, email_content: str) -> Dict[str, Any]:
        """
        Performs Named Entity Recognition parsing on the email content.

        Args:
            email_content (str): The email content to parse.

        Returns:
            Dict[str, Any]: Extracted named entities.
        """
        try:
            self.logger.debug("Starting NER pipeline.")
            entities = self.ner_pipeline(email_content)
            extracted_entities: Dict[str, Any] = {}

            # Enhanced mapping of NER labels to schema fields
            label_field_mapping = {
                "PER": [
                    ("Insured Information", "Name"),
                    ("Adjuster Information", "Adjuster Name"),
                ],
                "ORG": [("Requesting Party", "Insurance Company")],
                "LOC": [("Insured Information", "Loss Address")],
                "DATE": [("Assignment Information", "Date of Loss/Occurrence")],
                "MONEY": [("Assignment Information", "Estimated Damage")],
                "GPE": [("Insured Information", "Loss Address")],  # Geopolitical Entity
                "PRODUCT": [("Adjuster Information", "Policy #")],
                "EVENT": [("Assignment Information", "Cause of loss")],
            }

            for entity in entities:
                label = entity.get("entity_group")
                text = entity.get("word")

                if label and text:
                    mappings = label_field_mapping.get(label, [])
                    for section, field in mappings:
                        extracted_entities.setdefault(section, {}).setdefault(
                            field, []
                        ).append(text.strip())
                        self.logger.debug(
                            "Extracted %s entity '%s' mapped to %s - %s",
                            label,
                            text,
                            section,
                            field,
                        )

            return extracted_entities
        except Exception as e:
            self.logger.error("Error during NER parsing: %s", e, exc_info=True)
            return {}

    def donut_parsing(self, document_image: Union[str, Image.Image]) -> Dict[str, Any]:
        """
        Performs Donut parsing on the provided document image.

        Args:
            document_image (Union[str, Image.Image]): The path to the document image or a PIL Image object.

        Returns:
            Dict[str, Any]: Extracted data from Donut in JSON format mapped to the existing schema.
        """
        try:
            self.logger.debug("Starting Donut parsing.")

            # Load image if a path is provided
            if isinstance(document_image, str):
                document_image = Image.open(document_image).convert("RGB")
                self.logger.debug("Loaded image from path: %s", document_image)

            # Preprocess image and prepare input for Donut
            encoding = self.donut_processor(document_image, return_tensors="pt")
            pixel_values = encoding.pixel_values.to(self.device)
            task_prompt = "<s_cord-v2>"  # Task-specific prompt for parsing
            decoder_input_ids = self.donut_processor.tokenizer(
                task_prompt, add_special_tokens=False, return_tensors="pt"
            ).input_ids.to(self.device)

            # Generate output from the Donut model
            self.logger.debug("Generating output from Donut model.")
            outputs = self.donut_model.generate(
                pixel_values=pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=self.donut_model.config.max_position_embeddings,
                pad_token_id=self.donut_processor.tokenizer.pad_token_id,
                eos_token_id=self.donut_processor.tokenizer.eos_token_id,
                use_cache=True,
            )

            # Decode and convert to JSON
            self.logger.debug("Decoding Donut model output.")
            sequence = self.donut_processor.batch_decode(
                outputs, skip_special_tokens=True
            )[0]
            sequence = sequence.replace(
                self.donut_processor.tokenizer.eos_token, ""
            ).replace(self.donut_processor.tokenizer.pad_token, "")
            json_data = self.donut_processor.token2json(sequence)

            # Map Donut JSON output to existing schema
            mapped_data = self.map_donut_output_to_schema(json_data)
            self.logger.debug("Donut Parsing Result: %s", mapped_data)
            return mapped_data
        except Exception as e:
            self.logger.error("Error during Donut parsing: %s", e, exc_info=True)
            return {}

    def map_donut_output_to_schema(self, donut_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maps the Donut JSON output to the existing schema.

        Args:
            donut_json (Dict[str, Any]): The JSON output from Donut parsing.

        Returns:
            Dict[str, Any]: Mapped data according to the existing schema.
        """
        mapped_data: Dict[str, Any] = {}
        try:
            # Define a mapping from Donut fields to QUICKBASE_SCHEMA
            field_mapping = {
                "policy_number": ("Adjuster Information", "Policy #"),
                "claim_number": ("Requesting Party", "Carrier Claim Number"),
                "insured_name": ("Insured Information", "Name"),
                "loss_address": ("Insured Information", "Loss Address"),
                "adjuster_name": ("Adjuster Information", "Adjuster Name"),
                "adjuster_phone": ("Adjuster Information", "Adjuster Phone Number"),
                "adjuster_email": ("Adjuster Information", "Adjuster Email"),
                "date_of_loss": ("Assignment Information", "Date of Loss/Occurrence"),
                "cause_of_loss": ("Assignment Information", "Cause of loss"),
                "loss_description": ("Assignment Information", "Loss Description"),
                # Add more mappings as needed
            }

            for item in donut_json.get("form", []):
                field_name = item.get("name")
                field_value = item.get("value")

                if field_name in field_mapping:
                    section, qb_field = field_mapping[field_name]
                    mapped_data.setdefault(section, {}).setdefault(qb_field, []).append(
                        field_value
                    )
                    self.logger.debug(
                        "Mapped Donut field '%s' to '%s - %s' with value '%s'",
                        field_name,
                        section,
                        qb_field,
                        field_value,
                    )

            return mapped_data
        except Exception as e:
            self.logger.error(
                "Error during mapping Donut output to schema: %s", e, exc_info=True
            )
            return {}

    def regex_extraction(self, email_content: str) -> Dict[str, Any]:
        """
        Performs regex-based extraction on the email content.

        Args:
            email_content (str): The email content to parse.

        Returns:
            Dict[str, Any]: Extracted data using regex patterns.
        """
        extracted_data = {}
        try:
            self.logger.debug("Starting regex extraction.")

            # Patterns for extraction
            patterns = {
                "Policy #": r"Policy (?:Number|#):\s*(\S+)",
                "Carrier Claim Number": r"Claim (?:Number|#):\s*(\S+)",
                "Date of Loss/Occurrence": r"Date of Loss:\s*([^\n]+)",
                "Adjuster Name": r"Your adjuster, (.+?) \(",
                "Adjuster Email": r"Your adjuster, .+? \(([^)]+)\)",
                "Adjuster Phone Number": r"Phone:\s*([\d-]+)",
                "Public Adjuster": r"Best regards,\s*(.+?)\n",
                "Public Adjuster Phone": r"Phone:\s*([\d-]+)",
                "Public Adjuster Email": r"Email:\s*([^\s]+)",
                "Name": r"Policyholder:\s*([^\n]+)",
                "Loss Address": r"Property Address:\s*([^\n]+)",
                "Cause of loss": r"Peril:\s*([^\n]+)",
                "Loss Description": r"Claim Details:\s*\n(.*?)\n\n",
                "Attachment(s)": r"Please find attached (.+?)\.",
            }

            for field, pattern in patterns.items():
                matches = re.findall(pattern, email_content, re.DOTALL)
                if matches:
                    value = matches[0].strip()
                    # Map the field to the appropriate section in your schema
                    if field in [
                        "Policy #",
                        "Adjuster Name",
                        "Adjuster Email",
                        "Adjuster Phone Number",
                    ]:
                        section = "Adjuster Information"
                    elif field in ["Carrier Claim Number"]:
                        section = "Requesting Party"
                    elif field in [
                        "Public Adjuster",
                        "Public Adjuster Phone",
                        "Public Adjuster Email",
                    ]:
                        section = "Insured Information"
                    elif field in ["Name", "Loss Address"]:
                        section = "Insured Information"
                    elif field in [
                        "Date of Loss/Occurrence",
                        "Cause of loss",
                        "Loss Description",
                    ]:
                        section = "Assignment Information"
                    elif field in ["Attachment(s)"]:
                        section = "Assignment Information"
                    else:
                        section = "Additional Information"

                    extracted_data.setdefault(section, {}).setdefault(field, []).append(
                        value
                    )
                    self.logger.debug("Extracted %s: %s", field, value)

            self.logger.debug("Regex Extraction Result: %s", extracted_data)
            return extracted_data
        except Exception as e:
            self.logger.error("Error during regex extraction: %s", e, exc_info=True)
            return {}

    def sequence_model_extract(self, summary_text: str) -> Dict[str, Any]:
        """
        Extracts key-value pairs from the summary text generated by the Sequence Model.

        Args:
            summary_text (str): The summary text to parse.

        Returns:
            Dict[str, Any]: Extracted data from the summary.
        """
        extracted_sequence: Dict[str, Any] = {}
        try:
            self.logger.debug("Extracting data from Sequence Model summary.")
            # Split the summary text into items
            for item in summary_text.split(","):
                if ":" in item:
                    key, value = item.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    # Map keys to the appropriate sections and fields
                    for section, fields in QUICKBASE_SCHEMA.items():
                        for field in fields:
                            if key.lower() == field.lower():
                                extracted_sequence.setdefault(section, {}).setdefault(
                                    field, []
                                ).append(value)
                                self.logger.debug(
                                    "Extracted %s: %s into section %s",
                                    key,
                                    value,
                                    section,
                                )

            self.logger.debug(
                "Sequence Model Extraction Result: %s", extracted_sequence
            )
            return extracted_sequence
        except Exception as e:
            self.logger.error(
                "Error during Sequence Model extraction: %s", e, exc_info=True
            )
            return {}

    def validation_parsing(self, email_content: str, parsed_data: Dict[str, Any]):
        """
        Performs validation parsing on the email content and parsed data.

        Args:
            email_content (str): The original email content.
            parsed_data (Dict[str, Any]): The data parsed so far.
        """
        try:
            self.logger.debug("Starting validation parsing.")
            inconsistencies = []

            # Check for consistency between parsed data and email content
            for section, fields in parsed_data.items():
                for field, value in fields.items():
                    if isinstance(value, list) and value:
                        value = value[0]  # Take the first item if it's a list
                    if isinstance(value, str) and value != "N/A":
                        # Check if the value appears in the email content
                        if value.lower() not in email_content.lower():
                            inconsistencies.append(
                                f"Inconsistency in {section} - {field}: '{value}' not found in email content"
                            )

            # Check for missing required fields
            required_fields = [
                ("Requesting Party", "Insurance Company"),
                ("Requesting Party", "Carrier Claim Number"),
                ("Insured Information", "Name"),
                ("Insured Information", "Loss Address"),
                ("Adjuster Information", "Adjuster Name"),
                ("Adjuster Information", "Policy #"),
                ("Assignment Information", "Date of Loss/Occurrence"),
                ("Assignment Information", "Cause of loss"),
            ]

            for section, field in required_fields:
                if not parsed_data.get(section, {}).get(field):
                    inconsistencies.append(
                        f"Missing required field: {section} - {field}"
                    )

            if inconsistencies:
                self.logger.warning("Validation issues found: %s", inconsistencies)
                parsed_data["validation_issues"] = inconsistencies
            else:
                self.logger.info("Validation parsing completed successfully.")

        except Exception as e:
            self.logger.error("Error during validation parsing: %s", e, exc_info=True)

    def format_phone_number(self, phone: str) -> str:
        """
        Formats a phone number into E.164 format.

        Args:
            phone (str): The phone number string to format.

        Returns:
            str: The formatted phone number or "N/A" if invalid.
        """
        if phone == "N/A":
            return phone

        self.logger.debug("Formatting phone number: %s", phone)
        try:
            parsed_number = phonenumbers.parse(phone, "US")
            if phonenumbers.is_valid_number(parsed_number):
                formatted_number = phonenumbers.format_number(
                    parsed_number, PhoneNumberFormat.E164
                )
                self.logger.debug("Formatted phone number: %s", formatted_number)
                return formatted_number
            self.logger.warning("Invalid phone number: %s", phone)
            return "N/A"
        except phonenumbers.NumberParseException as e:
            self.logger.warning("Failed to parse phone number: %s - %s", phone, e)
            return "N/A"

    def verify_attachments(self, attachments: List[str], email_content: str) -> bool:
        """
        Verifies if the attachments mentioned in the email content are present in the provided list.

        Args:
            attachments (List[str]): List of attachments.
            email_content (str): The email content.

        Returns:
            bool: True if all mentioned attachments are present, False otherwise.
        """
        self.logger.debug("Verifying attachments: %s", attachments)
        try:
            # Check if attachments are mentioned in the email content
            mentioned_attachments = re.findall(
                r"attached\s+([\w\s.,]+)", email_content, re.IGNORECASE
            )
            mentioned_attachments = [
                att.strip()
                for sublist in mentioned_attachments
                for att in sublist.split(",")
            ]

            # Check if all mentioned attachments are in the provided list
            all_mentioned_present = all(
                any(mention.lower() in att.lower() for att in attachments)
                for mention in mentioned_attachments
            )

            # Check if the number of attachments matches
            count_matches = len(attachments) == len(mentioned_attachments)

            if all_mentioned_present and count_matches:
                self.logger.debug("All attachments verified successfully.")
                return True
            self.logger.warning("Discrepancy in attachments detected.")
            return False
        except Exception as e:
            self.logger.error(
                "Error during attachment verification: %s", e, exc_info=True
            )
            return False

    def format_date(self, date_string: str) -> str:
        """
        Formats a date string into a consistent format.

        Args:
            date_string (str): The date string to format.

        Returns:
            str: The formatted date string or the original string if parsing fails.
        """

        pass
