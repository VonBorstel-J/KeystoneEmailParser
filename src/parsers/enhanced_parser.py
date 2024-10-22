# src/parsers/enhanced_parser.py

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as ConcurrentTimeoutError
from typing import Any, Dict, List, Optional, Union, Tuple

import dateutil.parser
import phonenumbers
import torch
from huggingface_hub import login
from phonenumbers import PhoneNumberFormat
from PIL import Image
from thefuzz import fuzz
from transformers import DonutProcessor, VisionEncoderDecoderModel, pipeline

from src.parsers.base_parser import BaseParser
from src.utils.config_loader import ConfigLoader
from src.utils.quickbase_schema import QUICKBASE_SCHEMA
from src.utils.validation import validate_json

LLM_TIMEOUT_SECONDS = 500

# Constants to avoid duplicate string literals
RESIDENCE_OCCUPIED = "Residence Occupied During Loss"
SOMEONE_HOME = "Was Someone home at time of damage"
ASSIGNMENT_TYPE = "Assignment Type"
INSURED_INFO = "Insured Information"
ADJUSTER_INFO = "Adjuster Information"
REQUESTING_PARTY = "Requesting Party"
PUBLIC_ADJUSTER = "Public Adjuster"
JOB_TITLE = "Job Title"
LOSS_ADDRESS = "Loss Address"
ASSIGNMENT_INFO = "Assignment Information"
DATE_OF_LOSS = "Date of Loss/Occurrence"
POLICY_NUMBER = "Policy #"
CAUSE_OF_LOSS = "Cause of loss"
ADJUSTER_PHONE_NUMBER = "Adjuster Phone Number"
ADJUSTER_EMAIL = "Adjuster Email"
CONTACT_NUMBER = "Contact #"
ATTACHMENTS = "Attachment(s)"
CARRIER_CLAIM_NUMBER = "Carrier Claim Number"
LOSS_DESCRIPTION = "Loss Description"
INSPECTION_TYPE = "Inspection type"
REPAIR_PROGRESS = "Repair or Mitigation Progress"
SPECIAL_INSTRUCTIONS = "Additional details/Special Instructions"
OWNER_TENANT = "Is the insured an Owner or a Tenant of the loss location?"
NAME = "Name"

# Additional Constants for Patterns
EMAIL_PATTERN = r"^[\w\.-]+@[\w\.-]+\.\w+$"
PHONE_PATTERN = r"^\+?\d[\d\- ]+$"
POLICY_NUMBER_PATTERN = r"^[A-Z0-9\-]+$"
CLAIM_NUMBER_PATTERN = r"^[A-Z0-9\-]+$"

class TimeoutException(Exception):
    pass


class EnhancedParser(BaseParser):
    def __init__(
        self,
        socketio: Optional["SocketIO"] = None,
        sid: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the EnhancedParser with optional SocketIO and session ID.

        Args:
            socketio (Optional[SocketIO]): The SocketIO instance for emitting events.
            sid (Optional[str]): The session ID of the connected client.
            logger (Optional[logging.Logger]): Logger instance.
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.info("Initializing EnhancedParser.")
        try:
            self.config = ConfigLoader.load_config()
            self.logger.debug("Loaded configuration: %s", self.config)
            self._check_environment_variables()
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.logger.info("Using device: %s", self.device)
            self.init_ner()
            self.init_donut()
            self.init_sequence_model()
            self.init_validation_model()
            self.socketio = socketio
            self.sid = sid
            self.timeouts = self._set_timeouts()
            self.logger.info("EnhancedParser initialized successfully.")
        except (ValueError, OSError) as e:
            self.logger.error(
                "Error during EnhancedParser initialization: %s", e, exc_info=True
            )
            raise

    def health_check(self) -> bool:
        components_healthy = all(
            [
                self.ner_pipeline is not None,
                self.donut_model is not None,
                self.sequence_model_pipeline is not None,
                self.validation_pipeline is not None,
            ]
        )
        if not components_healthy:
            self.logger.error("One or more components failed to initialize.")
            return False
        self.logger.info("All components are initialized and healthy.")
        return True

    def _check_environment_variables(self):
        required_vars = ["HF_TOKEN"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            self.logger.error(
                "Missing required environment variables: %s", ", ".join(missing_vars)
            )
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

    def init_ner(self):
        try:
            self.logger.info("Initializing NER pipeline.")
            repo_id = "dslim/bert-base-NER"
            self.ner_pipeline = pipeline(
                "ner",
                model=repo_id,
                tokenizer=repo_id,
                aggregation_strategy="simple",
                device=0 if self.device == "cuda" else -1,
            )
            self.logger.info("Loaded NER model '%s' successfully.", repo_id)
        except (OSError, ValueError) as e:
            self.logger.error(
                "Failed to load NER model '%s': %s", repo_id, e, exc_info=True
            )
            self.ner_pipeline = None

    def init_donut(self):
        try:
            self.logger.info("Initializing Donut model and processor.")
            repo_id = "naver-clova-ix/donut-base-finetuned-cord-v2"
            self.donut_processor = DonutProcessor.from_pretrained(
                repo_id, cache_dir=".cache"
            )
            self.donut_model = VisionEncoderDecoderModel.from_pretrained(
                repo_id, cache_dir=".cache"
            )
            self.donut_model.to(self.device)
            self.logger.info("Loaded Donut model '%s' successfully.", repo_id)
        except (OSError, ValueError) as e:
            self.logger.error(
                "Failed to load Donut model '%s': %s", repo_id, e, exc_info=True
            )
            self.donut_model = None
            self.donut_processor = None

    def init_sequence_model(self):
        try:
            self.logger.info("Initializing Sequence Model pipeline.")
            repo_id = "facebook/bart-large-cnn"
            self.sequence_model_pipeline = pipeline(
                "summarization",
                model=repo_id,
                tokenizer=repo_id,
                device=0 if self.device == "cuda" else -1,
            )
            self.logger.info("Loaded Sequence Model '%s' successfully.", repo_id)
        except (OSError, ValueError) as e:
            self.logger.error(
                "Failed to load Sequence Model '%s': %s", repo_id, e, exc_info=True
            )
            self.sequence_model_pipeline = None

    def init_validation_model(self):
        try:
            self.logger.info("Initializing Validation Model pipeline.")
            hf_token = os.getenv("HF_TOKEN")
            if not hf_token:
                raise ValueError(
                    "Hugging Face token not found in environment variables."
                )
            login(token=hf_token)
            self.logger.info("Logged in to Hugging Face Hub successfully.")
            repo_id = "gpt2"
            self.validation_pipeline = pipeline(
                "text-generation",
                model=repo_id,
                tokenizer=repo_id,
                device=0 if self.device == "cuda" else -1,
            )
            self.logger.info("Loaded Validation Model '%s' successfully.", repo_id)
        except (OSError, ValueError) as e:
            self.logger.error("Failed to load Validation Model: %s", e, exc_info=True)
            self.validation_pipeline = None

    def _set_timeouts(self) -> Dict[str, int]:
        timeouts = {
            "regex_extraction": self.config.get("model_timeouts", {}).get(
                "regex_extraction", 30
            ),
            "ner_parsing": self.config.get("model_timeouts", {}).get("ner_parsing", 30),
            "donut_parsing": self.config.get("model_timeouts", {}).get(
                "donut_parsing", 60
            ),
            "sequence_model_parsing": self.config.get("model_timeouts", {}).get(
                "sequence_model_parsing", 45
            ),
            "validation_parsing": self.config.get("model_timeouts", {}).get(
                "validation_parsing", 30
            ),
            "schema_validation": self.config.get("model_timeouts", {}).get(
                "schema_validation", 30
            ),
            "post_processing": self.config.get("model_timeouts", {}).get(
                "post_processing", 30
            ),
            "json_validation": self.config.get("model_timeouts", {}).get(
                "json_validation", 30
            ),
        }
        self.logger.debug("Set processing timeouts: %s", timeouts)
        return timeouts

    def parse(
        self,
        email_content: Optional[str] = None,
        document_image: Optional[Union[str, Image.Image]] = None,
    ) -> Dict[str, Any]:
        self.logger.info("Starting parsing process.")
        parsed_data: Dict[str, Any] = {}
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
                self.logger.info("Stage: %s", stage_name)
                timeout_seconds = self.timeouts.get(
                    stage_name.lower().replace(" ", "_"), 60
                )
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(stage_method, **kwargs)
                    stage_result = future.result(timeout=timeout_seconds)
                if isinstance(stage_result, dict) and stage_result:
                    parsed_data = self.merge_parsed_data(parsed_data, stage_result)
            except ConcurrentTimeoutError:
                self.logger.error(
                    "Stage '%s' timed out after %d seconds.",
                    stage_name,
                    timeout_seconds,
                )
                self.recover_from_failure(stage_name)
            except Exception as e:
                self.logger.error(
                    "Error in stage '%s': %s", stage_name, e, exc_info=True
                )
        self.logger.info("Parsing process completed.")
        return parsed_data

    def parse_email(
        self,
        email_content: Optional[str] = None,
        document_image: Optional[Union[str, Image.Image]] = None,
    ) -> Dict[str, Any]:
        if not self.validate_input(email_content, document_image):
            self.logger.error("Invalid input provided to parse_email.")
            return {}

        parsed_data = self.parse(email_content, document_image)

        # Load schema template
        schema_template_path = os.path.join(
            os.path.dirname(__file__), "importSchema.txt"
        )
        try:
            with open(schema_template_path, "r", encoding="utf-8") as f:
                schema_template = f.read()
            self.logger.debug("Loaded schema template from %s", schema_template_path)
        except FileNotFoundError:
            self.logger.error(
                "Schema template file not found at %s", schema_template_path
            )
            return parsed_data
        except (OSError, ValueError) as e:
            self.logger.error("Error reading schema template: %s", e, exc_info=True)
            return parsed_data

        # Validate against schema
        is_valid, missing_fields, formatted_data = self.validate_against_schema(
            parsed_data, schema_template
        )

        # Add validation results to output
        if not is_valid:
            parsed_data["validation_issues"] = parsed_data.get("validation_issues", [])
            parsed_data["validation_issues"].extend(
                [f"Missing required field: {field}" for field in missing_fields]
            )

        parsed_data["formatted_output"] = formatted_data

        return parsed_data

    def merge_parsed_data(
        self, original_data: Dict[str, Any], new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
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
                            seen = set()
                            original_data[section][field] = [
                                x
                                for x in combined_list
                                if not (x in seen or seen.add(x))
                            ]
                        else:
                            original_data[section][field] = value
        return original_data

    def validate_input(
        self,
        email_content: Optional[str] = None,
        document_image: Optional[Union[str, Image.Image]] = None,
    ) -> bool:
        if not email_content and not document_image:
            self.logger.error("No input provided")
            return False
        if document_image and not isinstance(document_image, (str, Image.Image)):
            self.logger.error("Invalid document_image type: %s", type(document_image))
            return False
        return True

    def validate_against_schema(
        self, parsed_data: Dict[str, Any], schema_template: str
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validates parsed data against the import schema template and formats it accordingly.

        Args:
            parsed_data: Dictionary containing the parsed email data
            schema_template: String containing the schema template format

        Returns:
            Tuple containing:
            - Boolean indicating if all required fields are present
            - List of missing or invalid fields
            - Dictionary of formatted data matching the schema
        """
        # Parse schema template into structured format
        schema_sections = {}
        current_section = None
        missing_fields = []
        formatted_data = {}

        for line in schema_template.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            if ":" not in line and not line.startswith("["):
                # This is a section header
                current_section = line
                schema_sections[current_section] = {}
                formatted_data[current_section] = {}
            elif ":" in line:
                # This is a field
                field_name = line.split(":")[0].strip()
                if current_section:
                    schema_sections[current_section][field_name] = True

        # Validate each section and field
        for section, fields in schema_sections.items():
            section_data = parsed_data.get(section, {})
            for field in fields:
                value = section_data.get(field)
                if not value or value == ["N/A"]:
                    missing_fields.append(f"{section} -> {field}")
                else:
                    # Format the value appropriately
                    if isinstance(value, list):
                        formatted_value = value[0] if value else "N/A"
                    else:
                        formatted_value = value

                    # Special handling for boolean fields
                    if field in [
                        RESIDENCE_OCCUPIED,
                        SOMEONE_HOME,
                    ]:
                        formatted_value = "Yes" if formatted_value else "No"

                    # Special handling for assignment type checkboxes
                    if field in ["Wind", "Structural", "Hail", "Foundation"]:
                        formatted_value = "[X]" if formatted_value else "[ ]"

                    formatted_data[section][field] = formatted_value

        # Handle the "Other" checkbox specially
        if ASSIGNMENT_TYPE in parsed_data:
            other_data = parsed_data[ASSIGNMENT_TYPE].get(
                "Other", [{"Checked": False, "Details": ""}]
            )[0]
            formatted_data["Check the box of applicable assignment type"] = {
                "Other": f"[{'X' if other_data['Checked'] else ' '}] - provide details: {other_data['Details']}"
            }

        is_valid = len(missing_fields) == 0

        return is_valid, missing_fields, formatted_data

    def cleanup_resources(self):
        self.logger.info("Cleaning up resources.")
        if self.donut_model is not None:
            self.donut_model.cpu()
            self.logger.debug("Donut model moved to CPU.")
        if hasattr(self, "ner_pipeline") and self.ner_pipeline is not None:
            self.ner_pipeline.model.cpu()
            self.logger.debug("NER pipeline model moved to CPU.")
        if (
            hasattr(self, "sequence_model_pipeline")
            and self.sequence_model_pipeline is not None
        ):
            self.sequence_model_pipeline.model.cpu()
            self.logger.debug("Sequence model pipeline moved to CPU.")
        if (
            hasattr(self, "validation_pipeline")
            and self.validation_pipeline is not None
        ):
            self.validation_pipeline.model.cpu()
            self.logger.debug("Validation pipeline model moved to CPU.")
        torch.cuda.empty_cache()
        self.logger.info("Resources cleaned up successfully.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_resources()

    def recover_from_failure(self, stage: str) -> bool:
        self.logger.warning("Attempting to recover from %s failure", stage)
        if stage.lower().replace(" ", "_") in [
            "regex_extraction",
            "ner_parsing",
            "donut_parsing",
            "sequence_model_parsing",
            "validation_parsing",
            "schema_validation",
            "post_processing",
            "json_validation",
        ]:
            return self._reinitialize_models()
        return False

    def _reinitialize_models(self) -> bool:
        try:
            self.logger.info("Reinitializing all models.")
            self.init_ner()
            self.init_donut()
            self.init_sequence_model()
            self.init_validation_model()
            health = self.health_check()
            if health:
                self.logger.info("Reinitialization successful.")
                return True
            else:
                self.logger.error("Reinitialization failed.")
                return False
        except (OSError, ValueError) as e:
            self.logger.error(
                "Error during model reinitialization: %s", e, exc_info=True
            )
            return False

    def _stage_regex_extraction(
        self, email_content: Optional[str] = None
    ) -> Dict[str, Any]:
        if not email_content:
            self.logger.warning("No email content provided for Regex Extraction.")
            return {}
        self.logger.debug("Executing Regex Extraction stage.")
        return self.regex_extraction(email_content)

    def _stage_ner_parsing(self, email_content: Optional[str] = None) -> Dict[str, Any]:
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
            return self.ner_parsing(email_content)
        except (OSError, ValueError) as e:
            self.logger.error("Error during NER Parsing stage: %s", e, exc_info=True)
            return {}

    def _stage_donut_parsing(
        self, document_image: Optional[Union[str, Image.Image]] = None
    ) -> Dict[str, Any]:
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
        except (OSError, ValueError) as e:
            self.logger.error("Error during Donut Parsing stage: %s", e, exc_info=True)
            return {}

    def _stage_sequence_model_parsing(
        self, email_content: Optional[str] = None
    ) -> Dict[str, Any]:
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
        except (OSError, ValueError) as e:
            self.logger.error(
                "Error during Sequence Model Parsing stage: %s", e, exc_info=True
            )
            return {}

    def sequence_model_parsing_with_timeout(self, email_content: str) -> Dict[str, Any]:
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.sequence_model_parsing, email_content)
                summary = future.result(timeout=LLM_TIMEOUT_SECONDS)
                return summary
        except ConcurrentTimeoutError:
            self.logger.error("Sequence Model parsing timed out.", exc_info=True)
            return {}
        except (OSError, ValueError) as e:
            self.logger.error(
                "Error during Sequence Model parsing with timeout: %s", e, exc_info=True
            )
            return {}

    def sequence_model_parsing(self, email_content: str) -> Dict[str, Any]:
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
        except (OSError, ValueError) as e:
            self.logger.error(
                "Error during Sequence Model inference: %s", e, exc_info=True
            )
            return {}

    def sequence_model_extract(self, summary_text: str) -> Dict[str, Any]:
        extracted_sequence: Dict[str, Any] = {}
        try:
            self.logger.debug("Extracting data from Sequence Model summary.")
            for item in summary_text.split(","):
                if ":" in item:
                    key, value = item.split(":", 1)
                    key = key.strip()
                    value = value.strip()
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
        except (OSError, ValueError) as e:
            self.logger.error(
                "Error during Sequence Model extraction: %s", e, exc_info=True
            )
            return {}

    def _stage_validation(
        self,
        email_content: Optional[str] = None,
        parsed_data: Optional[Dict[str, Any]] = None,
    ):
        if not email_content or not parsed_data:
            self.logger.warning(
                "Insufficient data for Validation Parsing. Skipping this stage."
            )
            return
        self.logger.debug("Executing Validation Parsing stage.")
        try:
            self._stage_validation_internal(email_content, parsed_data)
        except (OSError, ValueError) as e:
            self.logger.error(
                "Error during Validation Parsing stage: %s", e, exc_info=True
            )

    def _stage_validation_internal(
        self, email_content: str, parsed_data: Dict[str, Any]
    ):
        """Internal method for validation parsing."""
        self.logger.debug("Starting validation parsing.")
        inconsistencies = []
        try:
            for section, fields in parsed_data.items():
                for field, value in fields.items():
                    if isinstance(value, list) and value:
                        value = value[0]
                    if isinstance(value, str) and value != "N/A":
                        if value.lower() not in email_content.lower():
                            inconsistencies.append(
                                f"Inconsistency in {section} - {field}: '{value}' not found in email content"
                            )
            required_fields = [
                (REQUESTING_PARTY, "Insurance Company"),
                (REQUESTING_PARTY, "Handler"),
                (REQUESTING_PARTY, CARRIER_CLAIM_NUMBER),
                (INSURED_INFO, NAME),
                (INSURED_INFO, CONTACT_NUMBER),
                (INSURED_INFO, LOSS_ADDRESS),
                (INSURED_INFO, PUBLIC_ADJUSTER),
                (
                    INSURED_INFO,
                    OWNER_TENANT,
                ),
                (ADJUSTER_INFO, "Adjuster Name"),
                (ADJUSTER_INFO, ADJUSTER_PHONE_NUMBER),
                (ADJUSTER_INFO, ADJUSTER_EMAIL),
                (ADJUSTER_INFO, JOB_TITLE),
                (ADJUSTER_INFO, POLICY_NUMBER),
                (ASSIGNMENT_INFO, DATE_OF_LOSS),
                (ASSIGNMENT_INFO, CAUSE_OF_LOSS),
                (ASSIGNMENT_INFO, LOSS_DESCRIPTION),
                (ASSIGNMENT_INFO, RESIDENCE_OCCUPIED),
                (ASSIGNMENT_INFO, SOMEONE_HOME),
                (ASSIGNMENT_INFO, REPAIR_PROGRESS),
                (ASSIGNMENT_INFO, "Type"),
                (ASSIGNMENT_INFO, INSPECTION_TYPE),
            ]
            for section, field in required_fields:
                if not parsed_data.get(section, {}).get(field):
                    inconsistencies.append(
                        f"Missing required field: {section} - {field}"
                    )
            if inconsistencies:
                parsed_data["validation_issues"] = parsed_data.get(
                    "validation_issues", []
                ) + inconsistencies
                self.logger.warning("Validation issues found: %s", inconsistencies)
            else:
                self.logger.info("Validation parsing completed successfully.")
        except (OSError, ValueError) as e:
            self.logger.error("Error during validation parsing: %s", e, exc_info=True)

    def _stage_schema_validation(self, parsed_data: Optional[Dict[str, Any]] = None):
        if not parsed_data:
            self.logger.warning(
                "No parsed data available for Schema Validation. Skipping this stage."
            )
            return
        self.logger.debug("Executing Schema Validation stage.")
        try:
            self._stage_schema_validation_internal(parsed_data)
        except (OSError, ValueError) as e:
            self.logger.error(
                "Error during Schema Validation stage: %s", e, exc_info=True
            )

    def _stage_schema_validation_internal(self, parsed_data: Dict[str, Any]):
        """Internal method for schema validation with enhanced validation rules."""
        self.logger.debug("Starting schema validation.")
        missing_fields: List[str] = []
        inconsistent_fields: List[str] = []
        validation_errors: List[str] = []

        try:
            for section, fields in QUICKBASE_SCHEMA.items():
                if section in [
                    "Entities",
                    "TransformerEntities",
                    "missing_fields",
                    "inconsistent_fields",
                    "user_notifications",
                    "validation_issues",
                ]:
                    continue

                for field, rules in fields.items():
                    value = parsed_data.get(section, {}).get(field)

                    # Schema validation
                    is_valid, error_msg = self._validate_against_schema(
                        section, field, value
                    )
                    if not is_valid:
                        validation_errors.append(error_msg)
                        continue

                    # Process valid values
                    if value and value != ["N/A"]:
                        # Fuzzy matching for known values
                        known_values = self.config.get("known_values", {}).get(
                            field, []
                        )
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
                    else:
                        # Track missing required fields
                        if rules.get("required", False):
                            missing_fields.append(f"{section} -> {field}")
                            self.logger.debug("Missing field: %s -> %s", section, field)

            # Update parsed data with validation results
            if missing_fields:
                parsed_data["missing_fields"] = parsed_data.get("missing_fields", []) + missing_fields
                self.logger.info("Missing fields identified: %s", missing_fields)

            if inconsistent_fields:
                parsed_data["inconsistent_fields"] = parsed_data.get("inconsistent_fields", []) + inconsistent_fields
                self.logger.info(
                    "Inconsistent fields identified: %s", inconsistent_fields
                )

            if validation_errors:
                parsed_data["validation_issues"] = (
                    parsed_data.get("validation_issues", []) + validation_errors
                )
                self.logger.warning("Validation errors found: %s", validation_errors)

        except (OSError, ValueError) as e:
            self.logger.error("Error during schema validation: %s", e, exc_info=True)
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(e)]

    def _stage_post_processing(
        self, parsed_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not parsed_data:
            self.logger.warning(
                "No parsed data available for Post Processing. Skipping this stage."
            )
            return {}
        self.logger.debug("Executing Post Processing stage.")
        try:
            return self._stage_post_processing_internal(parsed_data)
        except (OSError, ValueError) as e:
            self.logger.error(
                "Error during Post Processing stage: %s", e, exc_info=True
            )
            return parsed_data

    def _stage_post_processing_internal(
        self, parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhanced post-processing with additional data cleanup and formatting."""
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
            for section, fields in parsed_data.items():
                if section in skip_sections or not isinstance(fields, dict):
                    continue

                for field, value_list in fields.items():
                    if not isinstance(value_list, list):
                        continue

                    for idx, value in enumerate(value_list):
                        # Date formatting
                        if "Date" in field or "Loss/Occurrence" in field:
                            formatted_date = self.format_date(value)
                            parsed_data[section][field][idx] = formatted_date
                            self.logger.debug(
                                "Formatted date for %s: %s", field, formatted_date
                            )

                        # Phone number formatting
                        if any(
                            phone_term in field
                            for phone_term in [CONTACT_NUMBER, "Phone Number", "Phone"]
                        ):
                            formatted_phone = self.format_phone_number(value)
                            parsed_data[section][field][idx] = formatted_phone
                            self.logger.debug(
                                "Formatted phone number for %s: %s",
                                field,
                                formatted_phone,
                            )

                        # Boolean value standardization
                        if field in [
                            "Wind",
                            "Structural",
                            "Hail",
                            "Foundation",
                            RESIDENCE_OCCUPIED,
                            SOMEONE_HOME,
                        ]:
                            if isinstance(value, str):
                                parsed_data[section][field][idx] = (
                                    value.lower() == "yes" or value.lower() == "true"
                                )

                        # Address formatting
                        if "Address" in field:
                            formatted_address = self._format_address(value)
                            parsed_data[section][field][idx] = formatted_address
                            self.logger.debug(
                                "Formatted address for %s: %s", field, formatted_address
                            )

                        # Email formatting
                        if "Email" in field:
                            formatted_email = value.lower().strip()
                            parsed_data[section][field][idx] = formatted_email
                            self.logger.debug(
                                "Formatted email for %s: %s", field, formatted_email
                            )

                        # Clean up text fields
                        if isinstance(value, str):
                            cleaned_text = self._clean_text(value)
                            parsed_data[section][field][idx] = cleaned_text

            # Verify attachments if present
            attachments = parsed_data.get(ATTACHMENTS, {}).get("Files", [])
            if attachments:
                if not self.verify_attachments(
                    attachments, parsed_data.get("email_content", "")
                ):
                    parsed_data.setdefault("user_notifications", []).append(
                        "Attachments mentioned in email may be missing or inconsistent."
                    )

            return parsed_data

        except (OSError, ValueError) as e:
            self.logger.error("Error during post-processing: %s", e, exc_info=True)
            return parsed_data

    def _stage_json_validation(self, parsed_data: Optional[Dict[str, Any]] = None):
        if not parsed_data:
            self.logger.warning(
                "No parsed data available for JSON Validation. Skipping this stage."
            )
            return
        self.logger.debug("Executing JSON Validation stage.")
        try:
            self._stage_json_validation_internal(parsed_data)
        except (OSError, ValueError) as e:
            self.logger.error(
                "Error during JSON Validation stage: %s", e, exc_info=True
            )

    def _stage_json_validation_internal(self, parsed_data: Dict[str, Any]):
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
        except (OSError, ValueError) as e:
            self.logger.error("Error during JSON validation: %s", e, exc_info=True)
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(e)]

    def ner_parsing(self, email_content: str) -> Dict[str, Any]:
        try:
            self.logger.debug("Starting NER pipeline.")
            entities = self.ner_pipeline(email_content)
            extracted_entities: Dict[str, Any] = {}

            label_field_mapping = {
                "PER": [
                    (INSURED_INFO, NAME),
                    (ADJUSTER_INFO, "Adjuster Name"),
                    (REQUESTING_PARTY, "Handler"),
                    (INSURED_INFO, PUBLIC_ADJUSTER),
                ],
                "ORG": [
                    (REQUESTING_PARTY, "Insurance Company"),
                    (ADJUSTER_INFO, JOB_TITLE),
                ],
                "LOC": [
                    (INSURED_INFO, LOSS_ADDRESS),
                    (ADJUSTER_INFO, "Address"),
                ],
                "DATE": [(ASSIGNMENT_INFO, DATE_OF_LOSS)],
                "MONEY": [(ASSIGNMENT_INFO, "Estimated Damage")],
                "GPE": [
                    (INSURED_INFO, LOSS_ADDRESS),
                    (ADJUSTER_INFO, "Address"),
                ],
                "PRODUCT": [(ADJUSTER_INFO, POLICY_NUMBER)],
                "EVENT": [(ASSIGNMENT_INFO, CAUSE_OF_LOSS)],
                "PHONE": [
                    (INSURED_INFO, CONTACT_NUMBER),
                    (ADJUSTER_INFO, ADJUSTER_PHONE_NUMBER),
                ],
                "EMAIL": [(ADJUSTER_INFO, ADJUSTER_EMAIL)],
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
        except (OSError, ValueError) as e:
            self.logger.error("Error during NER parsing: %s", e, exc_info=True)
            return {}

    def donut_parsing(self, document_image: Union[str, Image.Image]) -> Dict[str, Any]:
        try:
            self.logger.debug("Starting Donut parsing.")
            if isinstance(document_image, str):
                document_image = Image.open(document_image).convert("RGB")
                self.logger.debug("Loaded image from path.")
            elif isinstance(document_image, Image.Image):
                pass  # Image is already an Image object; no action needed
            else:
                self.logger.warning(
                    "Invalid document_image type: %s. Skipping Donut parsing.",
                    type(document_image),
                )
                return {}
            encoding = self.donut_processor(document_image, return_tensors="pt")
            pixel_values = encoding.pixel_values.to(self.device)
            task_prompt = "<s_cord-v2>"
            decoder_input_ids = self.donut_processor.tokenizer(
                task_prompt, add_special_tokens=False, return_tensors="pt"
            ).input_ids.to(self.device)
            self.logger.debug("Generating output from Donut model.")
            outputs = self.donut_model.generate(
                pixel_values=pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=self.donut_model.config.max_position_embeddings,
                pad_token_id=self.donut_processor.tokenizer.pad_token_id,
                eos_token_id=self.donut_processor.tokenizer.eos_token_id,
                use_cache=True,
            )
            self.logger.debug("Decoding Donut model output.")
            sequence = self.donut_processor.batch_decode(
                outputs, skip_special_tokens=True
            )[0]
            sequence = sequence.replace(
                self.donut_processor.tokenizer.eos_token, ""
            ).replace(self.donut_processor.tokenizer.pad_token, "")
            json_data = self.donut_processor.token2json(sequence)
            mapped_data = self.map_donut_output_to_schema(json_data)
            self.logger.debug("Donut Parsing Result: %s", mapped_data)
            return mapped_data
        except (OSError, ValueError) as e:
            self.logger.error("Error during Donut parsing: %s", e, exc_info=True)
            return {}

    def map_donut_output_to_schema(self, donut_json: Dict[str, Any]) -> Dict[str, Any]:
        mapped_data: Dict[str, Any] = {}
        try:
            field_mapping = {
                "policy_number": (ADJUSTER_INFO, POLICY_NUMBER),
                "claim_number": (REQUESTING_PARTY, CARRIER_CLAIM_NUMBER),
                "insured_name": (INSURED_INFO, NAME),
                "loss_address": (INSURED_INFO, LOSS_ADDRESS),
                "adjuster_name": (ADJUSTER_INFO, "Adjuster Name"),
                "adjuster_phone": (ADJUSTER_INFO, ADJUSTER_PHONE_NUMBER),
                "adjuster_email": (ADJUSTER_INFO, ADJUSTER_EMAIL),
                "date_of_loss": (ASSIGNMENT_INFO, DATE_OF_LOSS),
                "cause_of_loss": (ASSIGNMENT_INFO, CAUSE_OF_LOSS),
                "loss_description": (ASSIGNMENT_INFO, LOSS_DESCRIPTION),
                "inspection_type": (ASSIGNMENT_INFO, INSPECTION_TYPE),
                "repair_progress": (
                    ASSIGNMENT_INFO,
                    REPAIR_PROGRESS,
                ),
                "residence_occupied": (
                    ASSIGNMENT_INFO,
                    RESIDENCE_OCCUPIED,
                ),
                "someone_home": (
                    ASSIGNMENT_INFO,
                    SOMEONE_HOME,
                ),
                "type": (ASSIGNMENT_INFO, "Type"),
                "additional_instructions": (
                    SPECIAL_INSTRUCTIONS,
                    "Details",
                ),
                "attachments": (ATTACHMENTS, "Files"),
            }
            for item in donut_json.get("form", []):
                field_name = item.get("name")
                field_value = item.get("value")
                if field_name in field_mapping:
                    section, qb_field = field_mapping[field_name]

                    # Handle boolean values
                    if field_name.startswith("assignment_"):
                        field_value = bool(field_value)
                    elif field_name in ["residence_occupied", "someone_home"]:
                        field_value = field_value.lower() == "yes"

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
        except (OSError, ValueError) as e:
            self.logger.error(
                "Error during mapping Donut output to schema: %s", e, exc_info=True
            )
            return {}

    def regex_extraction(self, email_content: str) -> Dict[str, Any]:
        extracted_data = {}
        try:
            self.logger.debug("Starting regex extraction.")
            patterns = {
                "Insurance Company": r"Insurance Company:\s*(.+?)\n",
                "Handler": r"Handler:\s*(.+?)\n",
                "Carrier Claim Number": r"Carrier Claim Number:\s*(\S+)",
                "Name": r"Name:\s*(.+?)\n",
                CONTACT_NUMBER: r"Contact #:\s*(\+?\d[\d\- ]+)",
                LOSS_ADDRESS: r"Loss Address:\s*(.+?)\n",
                PUBLIC_ADJUSTER: r"Public Adjuster:\s*(.+?)\n",
                OWNER_TENANT: r"Is the insured an Owner or a Tenant of the loss location\?\s*(Yes|No)",
                "Adjuster Name": r"Adjuster Name:\s*(.+?)\n",
                ADJUSTER_PHONE_NUMBER: r"Adjuster Phone Number:\s*(\+?\d[\d\- ]+)",
                ADJUSTER_EMAIL: r"Adjuster Email:\s*([\w\.-]+@[\w\.-]+)",
                JOB_TITLE: r"Job Title:\s*(.+?)\n",
                "Address": r"Address:\s*(.+?)\n",
                POLICY_NUMBER: r"Policy #:\s*(POL\d{6})",
                DATE_OF_LOSS: r"Date of Loss/Occurrence:\s*([^\n]+)",
                CAUSE_OF_LOSS: r"Cause of loss:\s*([^\n]+)",
                "Facts of Loss": r"Facts of Loss:\s*([\s\S]+?)\n\n",
                LOSS_DESCRIPTION: r"Loss Description:\s*([\s\S]+?)\n\n",
                RESIDENCE_OCCUPIED: r"Residence Occupied During Loss:\s*(Yes|No)",
                SOMEONE_HOME: r"Was Someone home at time of damage:\s*(Yes|No)",
                REPAIR_PROGRESS: r"Repair or Mitigation Progress:\s*([\s\S]+?)\n\n",
                "Type": r"Type:\s*(.+?)\n",
                INSPECTION_TYPE: r"Inspection type:\s*(.+?)\n",
                "Wind": r"Wind\s*\[([xX\s]*)\]",
                "Structural": r"Structural\s*\[([xX\s]*)\]",
                "Hail": r"Hail\s*\[([xX\s]*)\]",
                "Foundation": r"Foundation\s*\[([xX\s]*)\]",
                "Other": r"Other\s*\[([xX\s]*)\] - provide details:\s*(.+?)\n",
                SPECIAL_INSTRUCTIONS: r"Additional details/Special Instructions:\s*([\s\S]+?)\n\n",
                ATTACHMENTS: r"Attachment\(s\):\s*(.+?)\n",
            }
            section_mapping = {
                "Insurance Company": REQUESTING_PARTY,
                "Handler": REQUESTING_PARTY,
                "Carrier Claim Number": REQUESTING_PARTY,
                "Name": INSURED_INFO,
                CONTACT_NUMBER: INSURED_INFO,
                LOSS_ADDRESS: INSURED_INFO,
                PUBLIC_ADJUSTER: INSURED_INFO,
                OWNER_TENANT: INSURED_INFO,
                "Adjuster Name": ADJUSTER_INFO,
                ADJUSTER_PHONE_NUMBER: ADJUSTER_INFO,
                ADJUSTER_EMAIL: ADJUSTER_INFO,
                JOB_TITLE: ADJUSTER_INFO,
                "Address": ADJUSTER_INFO,
                POLICY_NUMBER: ADJUSTER_INFO,
                DATE_OF_LOSS: ASSIGNMENT_INFO,
                CAUSE_OF_LOSS: ASSIGNMENT_INFO,
                "Facts of Loss": ASSIGNMENT_INFO,
                LOSS_DESCRIPTION: ASSIGNMENT_INFO,
                RESIDENCE_OCCUPIED: ASSIGNMENT_INFO,
                SOMEONE_HOME: ASSIGNMENT_INFO,
                REPAIR_PROGRESS: ASSIGNMENT_INFO,
                "Type": ASSIGNMENT_INFO,
                INSPECTION_TYPE: ASSIGNMENT_INFO,
                SPECIAL_INSTRUCTIONS: SPECIAL_INSTRUCTIONS,
                ATTACHMENTS: ATTACHMENTS,
            }

            for field, pattern in patterns.items():
                match = re.search(pattern, email_content, re.IGNORECASE)
                if match:
                    if field in ["Wind", "Structural", "Hail", "Foundation"]:
                        value = bool(match.group(1).strip().lower() == "x")
                    elif field == "Other":
                        checked = bool(match.group(1).strip().lower() == "x")
                        details = match.group(2).strip()
                        value = {"Checked": checked, "Details": details}
                        extracted_data.setdefault(ASSIGNMENT_TYPE, {}).setdefault(
                            field, []
                        ).append(value)
                        self.logger.debug("Extracted %s: %s", field, value)
                        continue
                    elif field in [
                        RESIDENCE_OCCUPIED,
                        SOMEONE_HOME,
                    ]:
                        value = bool(match.group(1).strip().lower() == "yes")
                    else:
                        value = match.group(1).strip()
                    section = section_mapping.get(field, "Additional Information")
                    if field not in [
                        "Wind",
                        "Structural",
                        "Hail",
                        "Foundation",
                        "Other",
                    ]:
                        extracted_data.setdefault(section, {}).setdefault(
                            field, []
                        ).append(value)
                        self.logger.debug("Extracted %s: %s", field, value)
            self.logger.debug("Regex Extraction Result: %s", extracted_data)
            return extracted_data
        except (OSError, ValueError) as e:
            self.logger.error("Error during regex extraction: %s", e, exc_info=True)
            return {}

    def _validate_against_schema(
        self, section: str, field: str, value: Any
    ) -> Tuple[bool, str]:
        """Enhanced validation logic for schema fields."""
        try:
            if value is None or (isinstance(value, list) and not value):
                return False, f"Missing required field: {section} - {field}"

            if isinstance(value, list):
                value = value[0]

            if field.endswith("Email"):
                if not re.match(EMAIL_PATTERN, str(value)):
                    return False, f"Invalid email format: {section} - {field}"

            if "Phone" in field or "Contact" in field:
                try:
                    parsed_number = phonenumbers.parse(str(value), "US")
                    if not phonenumbers.is_valid_number(parsed_number):
                        return False, f"Invalid phone number: {section} - {field}"
                except phonenumbers.NumberParseException:
                    return False, f"Invalid phone number format: {section} - {field}"

            if field.endswith("Date") or "Loss/Occurrence" in field:
                try:
                    dateutil.parser.parse(str(value))
                except ValueError:
                    return False, f"Invalid date format: {section} - {field}"

            if field in ["Wind", "Structural", "Hail", "Foundation"]:
                if not isinstance(value, bool):
                    return (
                        False,
                        f"Invalid checkbox value for {section} - {field}: must be boolean",
                    )

            if field == "Other" and isinstance(value, dict):
                if not all(k in value for k in ["Checked", "Details"]):
                    return (
                        False,
                        "Invalid format for Other checkbox: must include Checked and Details",
                    )

            if field in [
                RESIDENCE_OCCUPIED,
                SOMEONE_HOME,
            ]:
                if not isinstance(value, bool):
                    return (
                        False,
                        f"Invalid Yes/No value for {section} - {field}: must be boolean",
                    )

            # Policy number format validation
            if field == POLICY_NUMBER:
                if not re.match(POLICY_NUMBER_PATTERN, str(value)):
                    return False, f"Invalid policy number format: {section} - {field}"

            # Carrier claim number validation
            if field == CARRIER_CLAIM_NUMBER:
                if not re.match(CLAIM_NUMBER_PATTERN, str(value)):
                    return False, f"Invalid claim number format: {section} - {field}"

            # Required non-empty string fields
            required_text_fields = [
                "Insurance Company",
                "Handler",
                "Name",
                LOSS_ADDRESS,
                "Adjuster Name",
                JOB_TITLE,
                CAUSE_OF_LOSS,
                LOSS_DESCRIPTION,
            ]
            if field in required_text_fields and not str(value).strip():
                return False, f"Required field cannot be empty: {section} - {field}"

            return True, ""

        except (OSError, ValueError) as e:
            self.logger.error(
                "Validation error for %s - %s: %s", section, field, str(e)
            )
            return False, f"Validation error: {str(e)}"

    def _clean_text(self, text: str) -> str:
        """Clean and standardize text content."""
        if not isinstance(text, str):
            return text

        # Remove extra whitespace
        text = " ".join(text.split())
        # Remove common email artifacts
        text = re.sub(r"_{2,}", "", text)
        text = re.sub(r"\[cid:[^\]]+\]", "", text)
        # Standardize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Remove duplicate punctuation
        text = re.sub(r"([.!?])\1+", r"\1", text)
        # Standardize quotes
        text = text.replace('"', '"').replace('"', '"')

        return text.strip()

    def _format_address(self, address: str) -> str:
        """Standardize address format."""
        if not isinstance(address, str):
            return address

        # Remove extra spaces and standardize commas
        address = re.sub(r"\s+", " ", address.strip())
        address = re.sub(r"\s*,\s*", ", ", address)

        # Try to identify and standardize state abbreviations
        state_pattern = r"\b([A-Za-z]{2})\b\s*(\d{5}(?:-\d{4})?)?$"
        match = re.search(state_pattern, address)
        if match:
            state = match.group(1)
            # Convert to uppercase state abbreviation if valid
            if len(state) == 2:
                address = (
                    address[: match.start(1)] + state.upper() + address[match.end(1) :]
                )

        return address

    def validation_parsing(self, email_content: str, parsed_data: Dict[str, Any]):
        try:
            self.logger.debug("Starting validation parsing.")
            inconsistencies = []
            for section, fields in parsed_data.items():
                for field, value in fields.items():
                    if isinstance(value, list) and value:
                        value = value[0]
                    if isinstance(value, str) and value != "N/A":
                        if value.lower() not in email_content.lower():
                            inconsistencies.append(
                                f"Inconsistency in {section} - {field}: '{value}' not found in email content"
                            )
            required_fields = [
                (REQUESTING_PARTY, "Insurance Company"),
                (REQUESTING_PARTY, "Handler"),
                (REQUESTING_PARTY, CARRIER_CLAIM_NUMBER),
                (INSURED_INFO, NAME),
                (INSURED_INFO, CONTACT_NUMBER),
                (INSURED_INFO, LOSS_ADDRESS),
                (INSURED_INFO, PUBLIC_ADJUSTER),
                (
                    INSURED_INFO,
                    OWNER_TENANT,
                ),
                (ADJUSTER_INFO, "Adjuster Name"),
                (ADJUSTER_INFO, ADJUSTER_PHONE_NUMBER),
                (ADJUSTER_INFO, ADJUSTER_EMAIL),
                (ADJUSTER_INFO, JOB_TITLE),
                (ADJUSTER_INFO, POLICY_NUMBER),
                (ASSIGNMENT_INFO, DATE_OF_LOSS),
                (ASSIGNMENT_INFO, CAUSE_OF_LOSS),
                (ASSIGNMENT_INFO, LOSS_DESCRIPTION),
                (ASSIGNMENT_INFO, RESIDENCE_OCCUPIED),
                (ASSIGNMENT_INFO, SOMEONE_HOME),
                (ASSIGNMENT_INFO, REPAIR_PROGRESS),
                (ASSIGNMENT_INFO, "Type"),
                (ASSIGNMENT_INFO, INSPECTION_TYPE),
            ]
            for section, field in required_fields:
                if not parsed_data.get(section, {}).get(field):
                    inconsistencies.append(
                        f"Missing required field: {section} - {field}"
                    )
            if inconsistencies:
                parsed_data["validation_issues"] = parsed_data.get(
                    "validation_issues", []
                ) + inconsistencies
                self.logger.warning("Validation issues found: %s", inconsistencies)
            else:
                self.logger.info("Validation parsing completed successfully.")
        except (OSError, ValueError) as e:
            self.logger.error("Error during validation parsing: %s", e, exc_info=True)

    def format_phone_number(self, phone: str) -> str:
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
        self.logger.debug("Verifying attachments: %s", attachments)
        try:
            mentioned_attachments = re.findall(
                r"attached\s+([\w\s.,]+)", email_content, re.IGNORECASE
            )
            mentioned_attachments = [
                att.strip()
                for sublist in mentioned_attachments
                for att in sublist.split(",")
            ]
            all_mentioned_present = all(
                any(mention.lower() in att.lower() for att in attachments)
                for mention in mentioned_attachments
            )
            count_matches = len(attachments) == len(mentioned_attachments)
            if all_mentioned_present and count_matches:
                self.logger.debug("All attachments verified successfully.")
                return True
            self.logger.warning("Discrepancy in attachments detected.")
            return False
        except (OSError, ValueError) as e:
            self.logger.error(
                "Error during attachment verification: %s", e, exc_info=True
            )
            return False

    def format_date(self, date_string: str) -> str:
        if date_string == "N/A":
            return date_string
        self.logger.debug("Formatting date string: %s", date_string)
        try:
            parsed_date = dateutil.parser.parse(date_string)
            formatted_date = parsed_date.strftime("%Y-%m-%d")
            self.logger.debug("Formatted date: %s", formatted_date)
            return formatted_date
        except (ValueError, TypeError) as e:
            self.logger.warning("Failed to parse date '%s': %s", date_string, e)
            return "N/A"

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring."""
        return {
            "memory_usage": self._check_memory_usage(),
            "model_status": self.health_check(),
            "processing_times": {
                "regex_extraction": self.timeouts.get("regex_extraction", 30),
                "ner_parsing": self.timeouts.get("ner_parsing", 30),
                "donut_parsing": self.timeouts.get("donut_parsing", 60),
                "sequence_model_parsing": self.timeouts.get(
                    "sequence_model_parsing", 45
                ),
                "validation_parsing": self.timeouts.get("validation_parsing", 30),
                "schema_validation": self.timeouts.get("schema_validation", 30),
                "post_processing": self.timeouts.get("post_processing", 30),
                "json_validation": self.timeouts.get("json_validation", 30),
            },
        }

    def _check_memory_usage(self) -> Dict[str, float]:
        """Check memory usage of models."""
        memory_info = {}
        if torch.cuda.is_available():
            memory_info["cuda"] = {
                "allocated": torch.cuda.memory_allocated() / 1024**2,  # MB
                "cached": torch.cuda.memory_reserved() / 1024**2,  # MB
                "max_allocated": torch.cuda.max_memory_allocated() / 1024**2,  # MB
            }
        return memory_info

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
