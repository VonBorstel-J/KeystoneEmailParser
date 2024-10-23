# src/parsers/enhanced_parser.py

import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as ConcurrentTimeoutError
from typing import Any, Dict, List, Optional, Union

import dateutil.parser
import phonenumbers
import torch
from huggingface_hub import login
from PIL import Image
from thefuzz import fuzz
from transformers import DonutProcessor, VisionEncoderDecoderModel, pipeline
from dataclasses import dataclass
from copy import deepcopy

from src.parsers.base_parser import BaseParser
from src.utils.config_loader import ConfigLoader
from src.utils.quickbase_schema import QUICKBASE_SCHEMA
from src.utils.validation import validate_json, assignment_schema

LLM_TIMEOUT_SECONDS = 500


class TimeoutException(Exception):
    pass


@dataclass
class MergeChange:
    section: str
    field: Optional[str]
    old_value: Any
    new_value: Any
    change_type: str

    def __str__(self) -> str:
        if self.field:
            return f"{self.change_type.title()}: {self.section}.{self.field}: {self.old_value} -> {self.new_value}"
        return f"{self.change_type.title()}: {self.section}: {self.old_value} -> {self.new_value}"


class DataMerger:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.changes: List[MergeChange] = []
        self._seen_values: Set[str] = set()

    @staticmethod
    def ensure_list(value: Any) -> List[Any]:
        if value is None:
            return ["N/A"]
        if isinstance(value, list):
            return value
        if isinstance(value, (dict, set)):
            return [value]
        return [value]

    def merge_field_values(
        self, existing: Any, new: Any, field_config: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        existing_list = self.ensure_list(existing)
        new_list = self.ensure_list(new)
        if field_config:
            field_type = field_config.get("type")
            if field_type == "boolean":
                return [bool(new_list[-1])]
            elif field_type == "date":
                return self._format_dates(new_list)
            elif field_type == "email":
                return [email.lower().strip() for email in new_list if email != "N/A"]
        if any(v != "N/A" for v in new_list):
            existing_list = [v for v in existing_list if v != "N/A"]
        self._seen_values.clear()
        merged = []
        for item in existing_list + new_list:
            if item != "N/A":
                item_str = str(item)
                if item_str not in self._seen_values:
                    self._seen_values.add(item_str)
                    merged.append(item)
        return merged if merged else ["N/A"]

    def _format_dates(self, dates: List[str]) -> List[str]:
        from datetime import datetime

        formatted = []
        for date in dates:
            try:
                if date != "N/A":
                    dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
                    formatted.append(dt.strftime("%Y-%m-%d"))
            except ValueError:
                self.logger.warning(f"Invalid date format: {date}")
        return formatted if formatted else ["N/A"]


class EnhancedParser(BaseParser):
    def __init__(
        self,
        socketio: Optional[Any] = None,
        sid: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
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
            self.init_initial_parsing()
            self.init_ner()
            self.init_donut()
            self.init_sequence_model()
            self.init_validation_model()
            self.init_sentiment_model()
            self.socketio = socketio
            self.sid = sid
            self.timeouts = self._set_timeouts()
            self.logger.info("EnhancedParser initialized successfully.")
        except (ValueError, OSError) as e:
            self.logger.error(
                "Error during EnhancedParser initialization: %s", e, exc_info=True
            )
            raise

    def init_initial_parsing(self):
        try:
            self.logger.info("Initializing Initial Parsing Model pipeline.")
            repo_id = "gpt2"  
            self.initial_parsing_pipeline = pipeline(
                "text-generation",
                model=repo_id,
                tokenizer=repo_id,
                device=0 if self.device == "cuda" else -1,
            )
            self.logger.info("Loaded Initial Parsing Model '%s' successfully.", repo_id)
        except (OSError, ValueError) as e:
            self.logger.error("Failed to load Initial Parsing Model: %s", e, exc_info=True)
            self.initial_parsing_pipeline = None

    def init_sentiment_model(self):
        try:
            self.logger.info("Initializing Sentiment Analysis Model pipeline.")
            repo_id = "nlptown/bert-base-multilingual-uncased-sentiment"
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=repo_id,
                tokenizer=repo_id,
                device=0 if self.device == "cuda" else -1,
            )
            self.logger.info("Loaded Sentiment Analysis Model '%s' successfully.", repo_id)
        except (OSError, ValueError) as e:
            self.logger.error("Failed to load Sentiment Analysis Model: %s", e, exc_info=True)
            self.sentiment_pipeline = None

    def health_check(self) -> bool:
        components_healthy = all(
            [
                hasattr(self, "initial_parsing_pipeline")
                and self.initial_parsing_pipeline is not None,
                hasattr(self, "ner_pipeline")
                and self.ner_pipeline is not None,
                hasattr(self, "donut_model")
                and self.donut_model is not None,
                hasattr(self, "sequence_model_pipeline")
                and self.sequence_model_pipeline is not None,
                hasattr(self, "validation_pipeline")
                and self.validation_pipeline is not None,
                hasattr(self, "sentiment_pipeline")
                and self.sentiment_pipeline is not None,
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
                raise ValueError("Hugging Face token not found in environment variables.")
            login(token=hf_token)
            self.logger.info("Logged in to Hugging Face Hub successfully.")
            repo_id = "facebook/bart-large"
            self.validation_pipeline = pipeline(
                "text2text-generation",
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
            "initial_parsing": self.config.get("model_timeouts", {}).get(
                "initial_parsing", 30
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
            "sentiment_analysis": self.config.get("model_timeouts", {}).get(
                "sentiment_analysis", 30
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
                "Initial Parsing",
                self._stage_initial_parsing,
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
                "Comprehensive Validation",
                self._stage_comprehensive_validation,
                {"email_content": email_content, "parsed_data": parsed_data},
            ),
            (
                "Sentiment Analysis",
                self._stage_sentiment_analysis,
                {"email_content": email_content, "parsed_data": parsed_data},
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
        try:
            is_valid, error_message = validate_json(parsed_data)
            if not is_valid:
                self.logger.warning(f"JSON validation failed: {error_message}")
                parsed_data["validation_issues"] = parsed_data.get(
                    "validation_issues", []
                )
                parsed_data["validation_issues"].append(error_message)
            formatted_data = {}
            missing_fields = []
            for section, fields in QUICKBASE_SCHEMA.items():
                if isinstance(fields, dict):
                    formatted_section = {}
                    for field, field_config in fields.items():
                        if (
                            isinstance(field_config, dict)
                            and "field_id" in field_config
                        ):
                            section_data = parsed_data.get(section, {})
                            value = (
                                section_data.get(field, ["N/A"])[0]
                                if isinstance(section_data.get(field), list)
                                else section_data.get(field, "N/A")
                            )
                            if field_config.get("required", False) and (
                                not value or value == "N/A"
                            ):
                                missing_fields.append(f"{section} -> {field}")
                            formatted_data.setdefault(section, {})[field] = value
            parsed_data["formatted_output"] = formatted_data
            if missing_fields:
                parsed_data["validation_issues"] = parsed_data.get(
                    "validation_issues", []
                )
                parsed_data["validation_issues"].extend(
                    [f"Missing required field: {field}" for field in missing_fields]
                )
            return parsed_data
        except Exception as e:
            self.logger.error(f"Error in parse_email: {str(e)}", exc_info=True)
            return parsed_data

    def _validate_merged_data(self, data: Dict[str, Any]) -> None:
        required_sections = {
            "Requesting Party": {
                "Insurance Company": list,
                "Handler": list,
                "Carrier Claim Number": list,
            },
            "Insured Information": {
                "Name": list,
                "Contact #": list,
                "Loss Address": list,
                "Public Adjuster": list,
                "Is the insured an Owner or a Tenant of the loss location?": list,
            },
            "Adjuster Information": {
                "Adjuster Name": list,
                "Adjuster Phone Number": list,
                "Adjuster Email": list,
                "Job Title": list,
                "Address": list,
                "Policy #": list,
            },
            "Assignment Information": {
                "Date of Loss/Occurrence": list,
                "Cause of loss": list,
                "Facts of Loss": list,
                "Loss Description": list,
                "Residence Occupied During Loss": list,
                "Was Someone home at time of damage": list,
                "Repair or Mitigation Progress": list,
                "Type": list,
                "Inspection type": list,
            },
            "Assignment Type": {
                "Wind": list,
                "Structural": list,
                "Hail": list,
                "Foundation": list,
                "Other": list,
            },
        }
        try:
            for section, fields in required_sections.items():
                if section not in data:
                    self.logger.warning(f"Missing required section: {section}")
                    data[section] = {}
                for field, field_type in fields.items():
                    if field not in data[section]:
                        if field_type == list:
                            data[section][field] = ["N/A"]
                        else:
                            data[section][field] = "N/A"
                    if field_type == list and not isinstance(
                        data[section][field], list
                    ):
                        data[section][field] = [data[section][field]]
            if "Assignment Type" in data and "Other" in data["Assignment Type"]:
                other_data = data["Assignment Type"]["Other"]
                if isinstance(other_data, list) and other_data:
                    if isinstance(other_data[0], dict):
                        if not all(
                            key in other_data[0] for key in ["Checked", "Details"]
                        ):
                            self.logger.warning(
                                "Invalid Other field format in Assignment Type"
                            )
                            data["Assignment Type"]["Other"] = [
                                {"Checked": False, "Details": "N/A"}
                            ]
                    else:
                        data["Assignment Type"]["Other"] = [
                            {"Checked": False, "Details": "N/A"}
                        ]
            for section in [
                "Entities",
                "TransformerEntities",
                "Additional details/Special Instructions",
                "Attachment(s)",
            ]:
                if section not in data:
                    data[section] = {} if section != "Attachment(s)" else []
            self.logger.debug("Data validation completed successfully")
        except Exception as e:
            self.logger.error(f"Error during data validation: {str(e)}", exc_info=True)
            raise ValueError(f"Data validation failed: {str(e)}")

    def merge_parsed_data(
        self, original_data: Dict[str, Any], new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        merger = DataMerger(self.logger)
        try:
            if not isinstance(original_data, dict):
                raise ValueError(
                    f"original_data must be dict, got {type(original_data)}"
                )
            if not isinstance(new_data, dict):
                raise ValueError(f"new_data must be dict, got {type(new_data)}")
            result = deepcopy(original_data)
            for section, fields in new_data.items():
                try:
                    schema_config = QUICKBASE_SCHEMA.get(section, {})
                    if section in QUICKBASE_SCHEMA:
                        if section not in result:
                            result[section] = {}
                            merger.changes.append(
                                MergeChange(
                                    section=section,
                                    field=None,
                                    old_value=None,
                                    new_value={},
                                    change_type="create",
                                )
                            )
                        if isinstance(fields, dict):
                            for field, value in fields.items():
                                field_config = schema_config.get(field, {})
                                old_value = result[section].get(field, ["N/A"])
                                new_value = merger.merge_field_values(
                                    old_value, value, field_config
                                )
                                if old_value != new_value:
                                    result[section][field] = new_value
                                    merger.changes.append(
                                        MergeChange(
                                            section=section,
                                            field=field,
                                            old_value=old_value,
                                            new_value=new_value,
                                            change_type="update",
                                        )
                                    )
                        elif isinstance(fields, list):
                            old_value = result.get(section, [])
                            new_value = merger.merge_field_values(old_value, fields)
                            if old_value != new_value:
                                result[section] = new_value
                                merger.changes.append(
                                    MergeChange(
                                        section=section,
                                        field=None,
                                        old_value=old_value,
                                        new_value=new_value,
                                        change_type="update",
                                    )
                                )
                        else:
                            old_value = result.get(section)
                            result[section] = fields
                            merger.changes.append(
                                MergeChange(
                                    section=section,
                                    field=None,
                                    old_value=old_value,
                                    new_value=fields,
                                    change_type="update",
                                )
                            )
                    else:
                        self.logger.debug(f"Handling non-schema section: {section}")
                        if isinstance(fields, list):
                            if section not in result:
                                result[section] = []
                                merger.changes.append(
                                    MergeChange(
                                        section=section,
                                        field=None,
                                        old_value=None,
                                        new_value=[],
                                        change_type="create",
                                    )
                                )
                            old_value = result[section]
                            new_items = [x for x in fields if x not in result[section]]
                            result[section].extend(new_items)
                            if new_items:
                                merger.changes.append(
                                    MergeChange(
                                        section=section,
                                        field=None,
                                        old_value=old_value,
                                        new_value=result[section],
                                        change_type="update",
                                    )
                                )
                        else:
                            old_value = result.get(section)
                            result[section] = fields
                            merger.changes.append(
                                MergeChange(
                                    section=section,
                                    field=None,
                                    old_value=old_value,
                                    new_value=fields,
                                    change_type="update",
                                )
                            )
                except Exception as section_error:
                    self.logger.error(
                        f"Error processing section '{section}': {str(section_error)}",
                        exc_info=True,
                    )
                    continue
            if merger.changes:
                self.logger.debug(
                    "Merge changes:\n"
                    + "\n".join(f"- {change}" for change in merger.changes)
                )
            self._validate_merged_data(result)
            return result
        except ValueError as ve:
            self.logger.error(f"Invalid input data: {str(ve)}")
            raise
        except Exception as e:
            self.logger.error(f"Error in merge_parsed_data: {str(e)}", exc_info=True)
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
        if email_content and not isinstance(email_content, str):
            self.logger.error("Invalid email_content type: %s", type(email_content))
            return False
        return True

    def validate_with_bart(self, parsed_data: Dict[str, Any], original_email: str) -> Dict[str, Any]:
        if not self.validation_pipeline:
            self.logger.error("Validation pipeline is not initialized.")
            return parsed_data

        self.logger.info("Starting BART validation.")

        validation_prompts = {
            "Requesting Party": f"""\
Please validate the following section and provide suggestions for missing or incorrect fields in JSON format.

Section: Requesting Party
Parsed Data: {json.dumps(parsed_data.get('Requesting Party', {}), indent=2)}
Email Content: {original_email}

Provide your suggestions within the following JSON structure, enclosed between <BEGIN JSON> and <END JSON>:

<BEGIN JSON>
{{
    "suggestions": {{
        "Insurance Company": "Ensure the company name is spelled correctly.",
        "Handler": "Provide contact information if missing.",
        "Carrier Claim Number": "Verify the format of the claim number."
    }}
}}
<END JSON>
""",
            "Insured Information": f"""\
Please validate the following section and provide suggestions for missing or incorrect fields in JSON format.

Section: Insured Information
Parsed Data: {json.dumps(parsed_data.get('Insured Information', {}), indent=2)}
Email Content: {original_email}

Provide your suggestions within the following JSON structure, enclosed between <BEGIN JSON> and <END JSON>:

<BEGIN JSON>
{{
    "suggestions": {{
        "Name": "Ensure the insured's name is complete and correctly spelled.",
        "Contact #": "Verify the contact number format.",
        "Loss Address": "Confirm the completeness of the loss address.",
        "Public Adjuster": "Provide contact details if missing.",
        "Is the insured an Owner or a Tenant of the loss location?": "Confirm the ownership status."
    }}
}}
<END JSON>
""",
            "Adjuster Information": f"""\
Please validate the following section and provide suggestions for missing or incorrect fields in JSON format.

Section: Adjuster Information
Parsed Data: {json.dumps(parsed_data.get('Adjuster Information', {}), indent=2)}
Email Content: {original_email}

Provide your suggestions within the following JSON structure, enclosed between <BEGIN JSON> and <END JSON>:

<BEGIN JSON>
{{
    "suggestions": {{
        "Adjuster Name": "Ensure the adjuster's name is correctly spelled.",
        "Adjuster Phone Number": "Verify the phone number format.",
        "Adjuster Email": "Confirm the email format is valid.",
        "Job Title": "Provide the adjuster's job title if missing.",
        "Address": "Ensure the address is complete and correctly formatted.",
        "Policy #": "Check if the policy number follows the required pattern."
    }}
}}
<END JSON>
""",
            "Assignment Information": f"""\
Please validate the following section and provide suggestions for missing or incorrect fields in JSON format.

Section: Assignment Information
Parsed Data: {json.dumps(parsed_data.get('Assignment Information', {}), indent=2)}
Email Content: {original_email}

Provide your suggestions within the following JSON structure, enclosed between <BEGIN JSON> and <END JSON>:

<BEGIN JSON>
{{
    "suggestions": {{
        "Date of Loss/Occurrence": "Ensure the date follows the YYYY-MM-DD format.",
        "Cause of loss": "Specify the exact cause of the loss.",
        "Facts of Loss": "Provide detailed facts related to the loss.",
        "Loss Description": "Ensure the description is comprehensive.",
        "Residence Occupied During Loss": "Confirm whether the residence was occupied.",
        "Was Someone home at time of damage": "Specify if someone was present during the damage.",
        "Repair or Mitigation Progress": "Update the current status of repairs or mitigation.",
        "Type": "Clarify the type of loss or damage.",
        "Inspection type": "Specify the type of inspection conducted."
    }}
}}
<END JSON>
""",
            "Assignment Type": f"""\
Please validate the following section and provide suggestions for missing or incorrect fields in JSON format.

Section: Assignment Type
Parsed Data: {json.dumps(parsed_data.get('Assignment Type', {}), indent=2)}
Email Content: {original_email}

Provide your suggestions within the following JSON structure, enclosed between <BEGIN JSON> and <END JSON>:

<BEGIN JSON>
{{
    "suggestions": {{
        "Wind": "Confirm if wind-related damage is applicable.",
        "Structural": "Verify if structural damage is present.",
        "Hail": "Check for any hail-related issues.",
        "Foundation": "Ensure foundation damage is assessed.",
        "Other": "Provide details for any other types of damage."
    }}
}}
<END JSON>
""",
            "Additional details/Special Instructions": f"""\
Please validate the following section and provide suggestions for missing or incorrect fields in JSON format.

Section: Additional details/Special Instructions
Parsed Data: {json.dumps(parsed_data.get('Additional details/Special Instructions', {}), indent=2)}
Email Content: {original_email}

Provide your suggestions within the following JSON structure, enclosed between <BEGIN JSON> and <END JSON>:

<BEGIN JSON>
{{
    "suggestions": {{
        "Additional details/Special Instructions": "Ensure all special instructions are clearly stated."
    }}
}}
<END JSON>
""",
            "Attachment(s)": f"""\
Please validate the following section and provide suggestions for missing or incorrect fields in JSON format.

Section: Attachment(s)
Parsed Data: {json.dumps(parsed_data.get('Attachment(s)', {}), indent=2)}
Email Content: {original_email}

Provide your suggestions within the following JSON structure, enclosed between <BEGIN JSON> and <END JSON>:

<BEGIN JSON>
{{
    "suggestions": {{
        "Attachment(s)": "Verify that all mentioned attachments are included and accessible."
    }}
}}
<END JSON>
""",
        }

        validation_results = {}
        for section, prompt in validation_prompts.items():
            try:
                self.logger.debug(f"Generating BART response for section: {section}")
                self.logger.debug(f"Prompt for section '{section}':\n{prompt}")
                output = self.validation_pipeline(prompt, max_length=300, num_return_sequences=1)
                generated_text = output[0]['generated_text'].strip()
                self.logger.debug(f"Raw BART response for {section}:\n{generated_text}")

                json_str = self.extract_json(generated_text)
                if json_str:
                    suggestions = json.loads(json_str)
                    validation_results[section] = suggestions.get("suggestions", {})
                    self.logger.debug(f"Extracted JSON for {section}: {suggestions.get('suggestions', {})}")
                else:
                    validation_results[section] = {"validation_issue": generated_text}
                    self.logger.warning(f"BART response for {section} is not valid JSON.")
            except Exception as e:
                self.logger.error(f"Error during BART validation for section '{section}': {e}", exc_info=True)
                validation_results[section] = {"validation_issue": "Validation Failed"}

        for section, result in validation_results.items():
            if "validation_issue" in result:
                parsed_data.setdefault("validation_issues", []).append(f"{section}: {result['validation_issue']}")
            else:
                for field, suggestion in result.items():
                    parsed_data.setdefault("validation_issues", []).append(f"{section} -> {field}: {suggestion}")
                    self.logger.info(f"BART suggests reviewing '{field}' in section '{section}': {suggestion}")

        self.logger.info("BART validation completed.")
        return parsed_data

    def extract_json(self, text: str) -> Optional[str]:
        try:
            start_delimiter = '<BEGIN JSON>'
            end_delimiter = '<END JSON>'
            json_start = text.find(start_delimiter)
            json_end = text.find(end_delimiter)
            if json_start == -1 or json_end == -1:
                return None
            json_content = text[
                json_start + len(start_delimiter):json_end
            ].strip()
            json.loads(json_content)
            return json_content
        except json.JSONDecodeError:
            self.logger.warning("Failed to decode JSON from BART response.")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during JSON extraction: {e}", exc_info=True)
            return None

    def cleanup_resources(self):
        self.logger.info("Cleaning up resources.")
        try:
            if hasattr(self, "donut_model") and self.donut_model is not None:
                self.donut_model.cpu()
                self.logger.debug("Donut model moved to CPU.")
            if hasattr(self, "ner_pipeline") and self.ner_pipeline is not None:
                if hasattr(self.ner_pipeline, "model"):
                    self.ner_pipeline.model.cpu()
                    self.logger.debug("NER pipeline model moved to CPU.")
            if hasattr(self, "sequence_model_pipeline") and self.sequence_model_pipeline is not None:
                if hasattr(self.sequence_model_pipeline, "model"):
                    self.sequence_model_pipeline.model.cpu()
                    self.logger.debug("Sequence model pipeline model moved to CPU.")
            if hasattr(self, "validation_pipeline") and self.validation_pipeline is not None:
                if hasattr(self.validation_pipeline, "model"):
                    self.validation_pipeline.model.cpu()
                    self.logger.debug("Validation pipeline model moved to CPU.")
            if hasattr(self, "initial_parsing_pipeline") and self.initial_parsing_pipeline is not None:
                if hasattr(self.initial_parsing_pipeline, "model"):
                    self.initial_parsing_pipeline.model.cpu()
                    self.logger.debug("Initial Parsing pipeline model moved to CPU.")
            if hasattr(self, "sentiment_pipeline") and self.sentiment_pipeline is not None:
                if hasattr(self.sentiment_pipeline, "model"):
                    self.sentiment_pipeline.model.cpu()
                    self.logger.debug("Sentiment Analysis pipeline model moved to CPU.")
        except AttributeError as ae:
            self.logger.error(f"Attribute error during cleanup: {ae}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Unexpected error during cleanup: {e}", exc_info=True)
        torch.cuda.empty_cache()
        self.logger.info("Resources cleaned up successfully.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_resources()

    def recover_from_failure(self, stage: str) -> bool:
        self.logger.warning("Attempting to recover from %s failure", stage)
        if stage.lower().replace(" ", "_") in [
            "initial_parsing",
            "ner_parsing",
            "donut_parsing",
            "sequence_model_parsing",
            "validation_parsing",
            "schema_validation",
            "post_processing",
            "json_validation",
            "sentiment_analysis",
        ]:
            return self._reinitialize_models()
        return False

    def _reinitialize_models(self) -> bool:
        try:
            self.logger.info("Reinitializing all models.")
            self.init_initial_parsing()
            self.init_ner()
            self.init_donut()
            self.init_sequence_model()
            self.init_validation_model()
            self.init_sentiment_model()
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

    def _stage_initial_parsing(
        self, email_content: Optional[str] = None
    ) -> Dict[str, Any]:
        if not email_content:
            self.logger.warning("No email content provided for Initial Parsing.")
            return {}
        self.logger.debug("Executing Initial Parsing stage.")
        try:
            self._lazy_load_initial_parsing()
            if self.initial_parsing_pipeline is None:
                self.logger.warning(
                    "Initial Parsing pipeline is not available. Skipping Initial Parsing."
                )
                return {}
            return self.initial_parsing(email_content)
        except Exception as e:
            self.logger.error("Error during Initial Parsing stage: %s", e, exc_info=True)
            return {}

    def initial_parsing(self, email_content: str) -> Dict[str, Any]:
        self.logger.debug("Starting Initial Parsing pipeline.")
        try:
            extraction = self.initial_parsing_pipeline(
                email_content,
                max_length=500,
                num_return_sequences=1,
            )
            extracted_text = extraction[0]["generated_text"].strip()
            self.logger.debug("Initial Parsing Extraction: %s", extracted_text)
            return self.parse_initial_extraction(extracted_text)
        except Exception as e:
            self.logger.error(
                "Error during Initial Parsing inference: %s", e, exc_info=True
            )
            return {}

    def parse_initial_extraction(self, extracted_text: str) -> Dict[str, Any]:
        extracted_data: Dict[str, Any] = {}
        try:
            for line in extracted_text.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    for section, fields in QUICKBASE_SCHEMA.items():
                        for field in fields:
                            if key.lower() == field.lower():
                                extracted_data.setdefault(section, {}).setdefault(
                                    field, []
                                ).append(value)
                                self.logger.debug(
                                    "Extracted %s: %s into section %s",
                                    key,
                                    value,
                                    section,
                                )
            self.logger.debug("Initial Parsing Extraction Result: %s", extracted_data)
            return extracted_data
        except Exception as e:
            self.logger.error(
                "Error during Initial Parsing extraction: %s", e, exc_info=True
            )
            return {}

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
        except Exception as e:
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
        except Exception as e:
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
        except Exception as e:
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
        except Exception as e:
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
        except Exception as e:
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
        except Exception as e:
            self.logger.error(
                "Error during Sequence Model extraction: %s", e, exc_info=True
            )
            return {}

    def _stage_comprehensive_validation(
        self,
        email_content: Optional[str] = None,
        parsed_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not email_content or not parsed_data:
            self.logger.warning(
                "Insufficient data for Comprehensive Validation. Skipping this stage."
            )
            return
        self.logger.debug("Executing Comprehensive Validation stage.")
        try:
            self._stage_validation_internal(email_content, parsed_data)
            self._stage_schema_validation_internal(parsed_data)
        except Exception as e:
            self.logger.error(
                "Error during Comprehensive Validation stage: %s", e, exc_info=True
            )

    def _stage_validation_internal(self, email_content: str, parsed_data: Dict[str, Any]):
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
                ("Requesting Party", "Insurance Company"),
                ("Requesting Party", "Handler"),
                ("Requesting Party", "Carrier Claim Number"),
                ("Insured Information", "Name"),
                ("Insured Information", "Contact #"),
                ("Insured Information", "Loss Address"),
                ("Insured Information", "Public Adjuster"),
                ("Insured Information", "Is the insured an Owner or a Tenant of the loss location?"),
                ("Adjuster Information", "Adjuster Name"),
                ("Adjuster Information", "Adjuster Phone Number"),
                ("Adjuster Information", "Adjuster Email"),
                ("Adjuster Information", "Job Title"),
                ("Adjuster Information", "Policy #"),
                ("Assignment Information", "Date of Loss/Occurrence"),
                ("Assignment Information", "Cause of loss"),
                ("Assignment Information", "Loss Description"),
                ("Assignment Information", "Residence Occupied During Loss"),
                ("Assignment Information", "Was Someone home at time of damage"),
                ("Assignment Information", "Repair or Mitigation Progress"),
                ("Assignment Information", "Type"),
                ("Assignment Information", "Inspection type"),
            ]
            for section, field in required_fields:
                if not parsed_data.get(section, {}).get(field):
                    inconsistencies.append(
                        f"Missing required field: {section} - {field}"
                    )
            if inconsistencies:
                parsed_data["validation_issues"] = (
                    parsed_data.get("validation_issues", []) + inconsistencies
                )
                self.logger.warning("Validation issues found: %s", inconsistencies)
            else:
                self.logger.info("Validation parsing completed successfully.")

            parsed_data = self.validate_with_bart(parsed_data, email_content)
        except Exception as e:
            self.logger.error("Error during Validation Parsing stage: %s", e, exc_info=True)

    def _stage_schema_validation_internal(self, parsed_data: Dict[str, Any]):
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
                    is_valid, error_msg = self._validate_against_schema(
                        section, field, value
                    )
                    if not is_valid:
                        validation_errors.append(error_msg)
                        continue
                    if value and value != ["N/A"]:
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
                        if rules.get("required", False):
                            missing_fields.append(f"{section} -> {field}")
                            self.logger.debug("Missing field: %s -> %s", section, field)
            if missing_fields:
                parsed_data["missing_fields"] = (
                    parsed_data.get("missing_fields", []) + missing_fields
                )
                self.logger.info("Missing fields identified: %s", missing_fields)
            if inconsistent_fields:
                parsed_data["inconsistent_fields"] = (
                    parsed_data.get("inconsistent_fields", []) + inconsistent_fields
                )
                self.logger.info(
                    "Inconsistent fields identified: %s", inconsistent_fields
                )
            if validation_errors:
                parsed_data["validation_issues"] = (
                    parsed_data.get("validation_issues", []) + validation_errors
                )
                self.logger.warning("Validation errors found: %s", validation_errors)
        except Exception as e:
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
        except Exception as e:
            self.logger.error(
                "Error during Post Processing stage: %s", e, exc_info=True
            )
            return parsed_data

    def _stage_post_processing_internal(
        self, parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
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
                        if "Date" in field or "Loss/Occurrence" in field:
                            formatted_date = self.format_date(value)
                            parsed_data[section][field][idx] = formatted_date
                            self.logger.debug(
                                "Formatted date for %s: %s", field, formatted_date
                            )
                        if any(
                            phone_term in field
                            for phone_term in ["Contact #", "Phone Number", "Phone"]
                        ):
                            formatted_phone = self.format_phone_number(value)
                            parsed_data[section][field][idx] = formatted_phone
                            self.logger.debug(
                                "Formatted phone number for %s: %s",
                                field,
                                formatted_phone,
                            )
                        if field in [
                            "Wind",
                            "Structural",
                            "Hail",
                            "Foundation",
                            "Residence Occupied During Loss",
                            "Was Someone home at time of damage",
                        ]:
                            if isinstance(value, str):
                                parsed_data[section][field][idx] = (
                                    value.lower() == "yes" or value.lower() == "true"
                                )
                        if "Address" in field:
                            formatted_address = self._format_address(value)
                            parsed_data[section][field][idx] = formatted_address
                            self.logger.debug(
                                "Formatted address for %s: %s", field, formatted_address
                            )
                        if "Email" in field:
                            formatted_email = value.lower().strip()
                            parsed_data[section][field][idx] = formatted_email
                            self.logger.debug(
                                "Formatted email for %s: %s", field, formatted_email
                            )
                        if isinstance(value, str):
                            cleaned_text = self._clean_text(value)
                            parsed_data[section][field][idx] = cleaned_text
            attachments = parsed_data.get("Attachment(s)", {}).get("Files", [])
            if attachments:
                if not self.verify_attachments(
                    attachments, parsed_data.get("email_content", "")
                ):
                    parsed_data.setdefault("user_notifications", []).append(
                        "Attachments mentioned in email may be missing or inconsistent."
                    )
            return parsed_data
        except Exception as e:
            self.logger.error("Error during post-processing: %s", e, exc_info=True)
            return parsed_data

    def _stage_json_validation(
        self, parsed_data: Optional[Dict[str, Any]] = None
    ) -> None:
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

    def ner_parsing(self, email_content: str) -> Dict[str, Any]:
        try:
            self.logger.debug("Starting NER pipeline.")
            entities = self.ner_pipeline(email_content)
            extracted_entities: Dict[str, Any] = {}
            for entity in entities:
                if self.is_relevant_entity(entity, email_content):
                    section, field = self.map_entity_to_field(entity, email_content)
                    if section and field:
                        extracted_entities.setdefault(section, {}).setdefault(
                            field, []
                        ).append(entity.get("word").strip())
                        self.logger.debug(
                            "Extracted entity '%s' mapped to %s - %s",
                            entity.get("word"),
                            section,
                            field,
                        )
            return extracted_entities
        except Exception as e:
            self.logger.error("Error during NER parsing: %s", e, exc_info=True)
            return {}

    def is_relevant_entity(self, entity, email_content):
        label = entity.get("entity_group")
        text = entity.get("word")
        if label == "PER":
            patterns = [
                r"insured",
                r"adjuster",
                r"handler",
                r"public adjuster",
            ]
        elif label == "ORG":
            patterns = [
                r"insurance company",
                r"claims adjuster",
            ]
        elif label in ["LOC", "GPE"]:
            patterns = [
                r"loss location",
                r"property",
                r"address",
            ]
        elif label in ["DATE", "EVENT"]:
            patterns = [
                r"loss",
                r"incident",
                r"damage",
            ]
        elif label in ["PHONE", "EMAIL"]:
            patterns = []
        else:
            patterns = []
        for pattern in patterns:
            if re.search(pattern, email_content, re.IGNORECASE):
                return True
        return False

    def map_entity_to_field(self, entity, email_content):
        label = entity.get("entity_group")
        text = entity.get("word")
        if label == "PER":
            if re.search(r"insured", email_content, re.IGNORECASE):
                return "Insured Information", "Name"
            elif re.search(r"adjuster", email_content, re.IGNORECASE):
                return "Adjuster Information", "Adjuster Name"
            elif re.search(r"handler", email_content, re.IGNORECASE):
                return "Requesting Party", "Handler"
            elif re.search(r"public adjuster", email_content, re.IGNORECASE):
                return "Insured Information", "Public Adjuster"
        elif label == "ORG":
            if re.search(r"insurance company", email_content, re.IGNORECASE):
                return "Requesting Party", "Insurance Company"
            elif re.search(r"claims adjuster", email_content, re.IGNORECASE):
                return "Adjuster Information", "Job Title"
        elif label in ["LOC", "GPE"]:
            if re.search(r"loss location", email_content, re.IGNORECASE):
                return "Insured Information", "Loss Address"
            elif re.search(r"address", email_content, re.IGNORECASE):
                return "Adjuster Information", "Address"
        elif label in ["DATE", "EVENT"]:
            if re.search(r"loss", email_content, re.IGNORECASE):
                return "Assignment Information", "Date of Loss/Occurrence"
            elif re.search(r"incident", email_content, re.IGNORECASE):
                return "Assignment Information", "Date of Loss/Occurrence"
            elif re.search(r"damage", email_content, re.IGNORECASE):
                return "Assignment Information", "Cause of loss"
        elif label == "PHONE":
            if re.search(r"contact number", email_content, re.IGNORECASE):
                return "Insured Information", "Contact #"
            elif re.search(r"adjuster phone", email_content, re.IGNORECASE):
                return "Adjuster Information", "Adjuster Phone Number"
        elif label == "EMAIL":
            return "Adjuster Information", "Adjuster Email"
        return None, None

    def donut_parsing(self, document_image: Union[str, Image.Image]) -> Dict[str, Any]:
        try:
            self.logger.debug("Starting Donut parsing.")
            if isinstance(document_image, str):
                document_image = Image.open(document_image).convert("RGB")
                self.logger.debug("Loaded image from path.")
            elif isinstance(document_image, Image.Image):
                pass
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
        except Exception as e:
            self.logger.error("Error during Donut parsing: %s", e, exc_info=True)
            return {}

    def map_donut_output_to_schema(self, donut_json: Dict[str, Any]) -> Dict[str, Any]:
        mapped_data: Dict[str, Any] = {}
        try:
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
                "inspection_type": ("Assignment Information", "Inspection type"),
                "repair_progress": ("Assignment Information", "Repair or Mitigation Progress"),
                "residence_occupied": ("Assignment Information", "Residence Occupied During Loss"),
                "someone_home": ("Assignment Information", "Was Someone home at time of damage"),
                "type": ("Assignment Information", "Type"),
                "additional_instructions": ("Additional details/Special Instructions", "Details"),
                "attachments": ("Attachment(s)", "Files"),
                "owner_tenant": ("Insured Information", "Is the insured an Owner or a Tenant of the loss location?"),
            }
            for item in donut_json.get("form", []):
                field_name = item.get("name")
                field_value = item.get("value")
                if field_name in field_mapping:
                    section, qb_field = field_mapping[field_name]
                    if field_name in ["residence_occupied", "someone_home"]:
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
        except Exception as e:
            self.logger.error(
                "Error during mapping Donut output to schema: %s", e, exc_info=True
            )
            return {}

    def initial_parsing(self, email_content: str) -> Dict[str, Any]:
        self.logger.debug("Starting Initial Parsing pipeline.")
        try:
            extraction = self.initial_parsing_pipeline(
                email_content,
                max_length=500,
                num_return_sequences=1,
            )
            extracted_text = extraction[0]["generated_text"].strip()
            self.logger.debug("Initial Parsing Extraction: %s", extracted_text)
            return self.parse_initial_extraction(extracted_text)
        except Exception as e:
            self.logger.error(
                "Error during Initial Parsing inference: %s", e, exc_info=True
            )
            return {}

    def parse_initial_extraction(self, extracted_text: str) -> Dict[str, Any]:
        extracted_data: Dict[str, Any] = {}
        try:
            for line in extracted_text.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    for section, fields in QUICKBASE_SCHEMA.items():
                        for field in fields:
                            if key.lower() == field.lower():
                                extracted_data.setdefault(section, {}).setdefault(
                                    field, []
                                ).append(value)
                                self.logger.debug(
                                    "Extracted %s: %s into section %s",
                                    key,
                                    value,
                                    section,
                                )
            self.logger.debug("Initial Parsing Extraction Result: %s", extracted_data)
            return extracted_data
        except Exception as e:
            self.logger.error(
                "Error during Initial Parsing extraction: %s", e, exc_info=True
            )
            return {}

    def _stage_validation(
        self,
        email_content: Optional[str] = None,
        parsed_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not email_content or not parsed_data:
            self.logger.warning(
                "Insufficient data for Validation Parsing. Skipping this stage."
            )
            return
        self.logger.debug("Executing Validation Parsing stage.")
        try:
            self._stage_validation_internal(email_content, parsed_data)
        except Exception as e:
            self.logger.error(
                "Error during Validation Parsing stage: %s", e, exc_info=True
            )

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
        except Exception as e:
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

    def _clean_text(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        text = " ".join(text.split())
        text = re.sub(r"_{2,}", "", text)
        text = re.sub(r"\[cid:[^\]]+\]", "", text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"([.!?])\1+", r"\1", text)
        text = text.replace('"', '"').replace('"', '"')
        return text.strip()

    def _format_address(self, address: str) -> str:
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

    def verification_resources(self):
        pass

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
        except Exception as e:
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
        memory_info = {}
        if torch.cuda.is_available():
            memory_info["cuda"] = {
                "allocated": torch.cuda.memory_allocated() / 1024**2,
                "cached": torch.cuda.memory_reserved() / 1024**2,
                "max_allocated": torch.cuda.max_memory_allocated() / 1024**2,
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


# Example Usage After Fixes
if __name__ == "__main__":
    parser = EnhancedParser()
    try:
        result = parser.parse_email(
            email_content="example email content", document_image=None
        )
        print("Parsed Result:", result)
    except Exception as e:
        print("Error during parsing:", e)
    finally:
        parser.cleanup_resources()
