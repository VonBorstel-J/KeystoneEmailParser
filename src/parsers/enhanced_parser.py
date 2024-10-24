# src/parsers/enhanced_parser.py

import logging
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as ConcurrentTimeoutError
from typing import Any, Dict, Optional, Union

import torch
from PIL import Image
import psutil
from jinja2 import Template  # Added for templating

from src.parsers.base_parser import BaseParser
from src.parsers.data_merger import DataMerger
from src.parsers.stages.post_processing import post_process_parsed_data
from src.parsers.stages.validation_parsing import validate_internal, validate_schema_internal
from src.parsers.stages.donut_parsing import perform_donut_parsing, initialize_donut
from src.parsers.stages.ner_parsing import perform_ner, initialize_ner_pipeline
from src.parsers.stages.summarization import perform_summarization, initialize_summarization_pipeline
from src.parsers.stages.model_based_parsing import perform_model_based_parsing, initialize_model_parser
from src.utils.config import Config
from src.utils.validation import init_validation_model
from src.utils.email_utils import parse_email

# Define Constants Directly Within This File
ADJUSTER_INFORMATION: str = "Adjuster Information"
REQUESTING_PARTY: str = "Requesting Party"
INSURED_INFORMATION: str = "Insured Information"
ASSIGNMENT_INFORMATION: str = "Assignment Information"

# Custom Exceptions
class EnhancedParserError(Exception):
    """Base exception class for EnhancedParser."""


class InitializationError(EnhancedParserError):
    """Raised when initialization of a component fails."""


class ParsingError(EnhancedParserError):
    """Raised when a parsing stage encounters an error."""


class ValidationError(EnhancedParserError):
    """Raised when validation fails."""


class EnhancedParser(BaseParser):
    REQUIRED_ENV_VARS = ['HF_TOKEN', 'TRANSFORMERS_CACHE']

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        socketio: Optional[Any] = None,
        sid: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize EnhancedParser with configuration."""
        super().__init__()

        # Set up configuration
        Config.initialize()
        self.config = config or Config.get_processing_config()

        # Set up logging
        self.logger = logger or self._setup_logging()

        # Socket.IO setup
        self.socketio = socketio
        self.sid = sid

        # Initialize asyncio loop
        self.loop = self._initialize_event_loop()

        # Initialize components
        self._initialize_components()

        self.logger.debug("EnhancedParser initialized with config: %s", self.config)

    def _initialize_event_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Initialize the asyncio event loop."""
        try:
            if not asyncio.get_event_loop().is_running():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self.logger.debug("Asyncio event loop initialized.")
                return loop
            else:
                self.logger.debug("Asyncio event loop already running.")
                return asyncio.get_event_loop()
        except Exception as e:
            self.logger.error("Failed to initialize asyncio loop: %s", e, exc_info=True)
            raise InitializationError(f"Asyncio loop initialization failed: {e}")

    def _check_environment_variables(self) -> None:
        """Verify that all required environment variables are set."""
        missing_vars = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing_vars:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger("EnhancedParser")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
        return logger

    def _initialize_components(self) -> None:
        """Initialize all parser components."""
        try:
            # Check environment variables first
            self._check_environment_variables()

            # Initialize models with error handling and prompt templates
            self.ner_pipeline = self._initialize_with_retry(
                initialize_ner_pipeline,
                self.logger,
                self.config
            )

            self.donut_processor, self.donut_model = self._initialize_with_retry(
                initialize_donut,
                self.logger,
                self.config
            )

            self.model_parser = self._initialize_with_retry(
                initialize_model_parser,
                self.logger,
                self.config,
                prompt_template=self._render_prompt('model_based_parsing')
            )

            self.validation_pipeline = self._initialize_with_retry(
                init_validation_model,
                self.logger,
                prompt_template=self._render_prompt('validation')
            )

            self.summarization_pipeline = self._initialize_with_retry(
                initialize_summarization_pipeline,
                self.logger,
                self.config,
                prompt_template=self._render_prompt('summarization')
            )

            # Initialize other components
            self.data_merger = DataMerger(self.logger)
            self.device = Config.get_device()

            # Set up thread pool
            self.executor = ThreadPoolExecutor(
                max_workers=self._determine_thread_count()
            )

            # Initialize timeouts
            self.timeouts = self._set_timeouts()

        except InitializationError:
            raise
        except Exception as e:
            self.logger.error("Failed to initialize components: %s", e, exc_info=True)
            raise InitializationError(f"Component initialization failed: {e}") from e

    def _render_prompt(self, model_key: str) -> str:
        """
        Renders the prompt template with the required data points.

        Args:
            model_key (str): The key of the model in the config (e.g., 'validation').

        Returns:
            str: The rendered prompt.
        """
        prompt_template = self.config.get('models', {}).get(model_key, {}).get('prompt_template', "")
        if not prompt_template:
            return ""

        # Prepare the data points for the prompt
        data_points = Config.data_points

        # Render the prompt using Jinja2
        template = Template(prompt_template)
        rendered_prompt = template.render(data_points=data_points)

        return rendered_prompt

    def _initialize_with_retry(self, init_func, *args, **kwargs) -> Any:
        """Initialize a component with retry logic."""
        max_retries = kwargs.pop('max_retries', 3)
        for attempt in range(max_retries):
            try:
                component = init_func(*args, **kwargs)
                self.logger.debug(
                    "Successfully initialized %s on attempt %d.",
                    init_func.__name__,
                    attempt + 1
                )
                return component
            except (ValueError, OSError) as e:
                if attempt == max_retries - 1:
                    self.logger.error(
                        "Failed to initialize %s after %d attempts: %s",
                        init_func.__name__,
                        max_retries,
                        e,
                        exc_info=True
                    )
                    raise InitializationError(
                        f"Initialization failed for {init_func.__name__}: {e}"
                    ) from e
                self.logger.warning(
                    "Initialization attempt %d for %s failed: %s. Retrying...",
                    attempt + 1,
                    init_func.__name__,
                    e
                )
                torch.cuda.empty_cache()  # Clear GPU memory if available

    def _determine_thread_count(self) -> int:
        """Determine optimal thread count based on system resources."""
        cpu_count = psutil.cpu_count(logical=True)
        available_memory = psutil.virtual_memory().available / (1024 * 1024 * 1024)  # GB

        # Base thread count on CPU cores and available memory
        thread_count = min(
            32,  # Maximum threads
            cpu_count * 2,  # CPU-based threads
            int(available_memory * 2)  # Memory-based threads
        )

        self.logger.debug("Determined thread count: %d", thread_count)
        return max(1, thread_count)  # Ensure at least 1 thread

    def _set_timeouts(self) -> Dict[str, int]:
        """Set timeout values for different processing stages."""
        return {
            "ner_parsing": Config.get_timeout("ner"),
            "donut_parsing": Config.get_timeout("donut"),
            "validation_parsing": Config.get_timeout("validation"),
            "schema_validation": Config.get_timeout("validation"),
            "post_processing": 30,
            "json_validation": 30,
            "summarization": Config.get_timeout("summarization"),
            "model_based_parsing": Config.get_timeout("model_based_parsing"),
        }

    def get_max_workers(self) -> int:
        """
        Retrieves the maximum number of workers from the ThreadPoolExecutor.

        Returns:
            int: Maximum number of worker threads.
        """
        return self.executor._max_workers

    async def parse_async(
        self,
        email_content: Optional[str] = None,
        document_image: Optional[Union[str, Image.Image]] = None,
    ) -> Dict[str, Any]:
        """
        Asynchronous wrapper for the parse method.

        Args:
            email_content (Optional[str]): The content of the email.
            document_image (Optional[Union[str, Image.Image]]): Path to the document image or a PIL Image object.

        Returns:
            Dict[str, Any]: Parsed data with potential validation issues.
        """
        if self.loop is None:
            self.logger.error("Asyncio event loop is not initialized.")
            return {}
        return await self.loop.run_in_executor(
            self.executor, self.parse, email_content, document_image
        )

    def parse_email(
        self,
        email_content: Optional[str] = None,
        document_image: Optional[Union[str, Image.Image]] = None,
    ) -> Dict[str, Any]:
        """
        Parses an email and associated document image.

        Args:
            email_content (Optional[str]): The content of the email.
            document_image (Optional[Union[str, Image.Image]]): Path to the document image or a PIL Image object.

        Returns:
            Dict[str, Any]: Parsed data with potential validation issues.
        """
        if not self.validate_input(email_content, document_image):
            self.logger.error("Invalid input provided to parse_email.")
            return {}
        parsed_data = self.parse(email_content, document_image)
        try:
            is_valid, error_message = validate_json(parsed_data)
            if not is_valid:
                self.logger.warning("JSON validation failed: %s", error_message)
                parsed_data["validation_issues"] = parsed_data.get(
                    "validation_issues", []
                )
                parsed_data["validation_issues"].append(error_message)
            # Additional validation and processing can be added here
            return parsed_data
        except ValidationError as ve:
            self.logger.error("ValidationError in parse_email: %s", ve)
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(ve)]
            return parsed_data
        except Exception as e:
            self.logger.error("Unexpected error in parse_email: %s", e, exc_info=True)
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(e)]
            return parsed_data

    def parse(
        self,
        email_content: Optional[str] = None,
        document_image: Optional[Union[str, Image.Image]] = None,
    ) -> Dict[str, Any]:
        """
        Orchestrates the multi-stage parsing process with timeouts and enhanced error handling.

        Args:
            email_content (Optional[str]): The content of the email.
            document_image (Optional[Union[str, Image.Image]]): Path to the document image or a PIL Image object.

        Returns:
            Dict[str, Any]: Aggregated parsed data from all stages.
        """
        self.logger.info("Starting parsing process.")
        parsed_data: Dict[str, Any] = {}
        stages = [
            (
                "Email Parsing",
                self._stage_email_parsing,
                {"email_content": email_content},
            ),
            ("NER Parsing", self._stage_ner_parsing, {"email_content": email_content}),
            (
                "Donut Parsing",
                self._stage_donut_parsing,
                {"document_image": document_image},
            ),
            (
                "Model-Based Parsing",
                self._stage_model_based_parsing,
                {"email_content": email_content},
            ),
            (
                "Comprehensive Validation",
                self._stage_comprehensive_validation,
                {"email_content": email_content, "parsed_data": parsed_data},
            ),
            (
                "Text Summarization",
                self._stage_text_summarization,
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
                self.logger.info("Starting stage: %s", stage_name)
                timeout_seconds = self.timeouts.get(
                    stage_name.lower().replace(" ", "_"), 60
                )
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(stage_method, **kwargs)
                    stage_result = future.result(timeout=timeout_seconds)
                if isinstance(stage_result, dict) and stage_result:
                    parsed_data = self.data_merger.merge_parsed_data(
                        parsed_data, stage_result
                    )
                self.logger.info("Completed stage: %s", stage_name)
            except ConcurrentTimeoutError:
                self.logger.error(
                    "Timeout in stage '%s': exceeded %d seconds.",
                    stage_name,
                    timeout_seconds
                )
                parsed_data["validation_issues"] = parsed_data.get(
                    "validation_issues", []
                ) + [f"Stage '{stage_name}' timed out."]
                if not self.recover_from_failure(stage_name.lower().replace(" ", "_")):
                    self.logger.warning(
                        "Failed to recover from timeout in stage '%s'. Continuing with next stage.",
                        stage_name
                    )
            except ParsingError as pe:
                self.logger.error(
                    "ParsingError in stage '%s': %s",
                    stage_name,
                    pe,
                    exc_info=True
                )
                if not self.recover_from_failure(stage_name.lower().replace(" ", "_")):
                    self.logger.warning(
                        "Failed to recover from error in stage '%s'. Continuing with next stage.",
                        stage_name
                    )
            except ValidationError as ve:
                self.logger.error(
                    "ValidationError in stage '%s': %s",
                    stage_name,
                    ve,
                    exc_info=True
                )
                if not self.recover_from_failure(stage_name.lower().replace(" ", "_")):
                    self.logger.warning(
                        "Failed to recover from validation error in stage '%s'. Continuing with next stage.",
                        stage_name
                    )
            except Exception as e:
                self.logger.error(
                    "Unexpected error in stage '%s': %s",
                    stage_name,
                    e,
                    exc_info=True
                )
                if not self.recover_from_failure(stage_name.lower().replace(" ", "_")):
                    self.logger.warning(
                        "Failed to recover from error in stage '%s'. Continuing with next stage.",
                        stage_name
                    )

        return parsed_data

    def _stage_email_parsing(
        self, email_content: Optional[str] = None
    ) -> Dict[str, Any]:
        if not email_content:
            self.logger.warning("No email content provided for Email Parsing.")
            return {}
        try:
            subject, from_address, body, attachments = parse_email(email_content)
            return {
                "email_metadata": {
                    "subject": subject,
                    "from": from_address,
                    "body": body,
                    "attachments": [att[0] for att in attachments],
                }
            }
        except ParsingError as pe:
            self.logger.error(
                "ParsingError during Email Parsing stage: %s", pe
            )
            raise
        except Exception as e:
            self.logger.error(
                "Error during Email Parsing stage: %s", e, exc_info=True
            )
            raise ParsingError(f"Email Parsing failed: {e}") from e

    def _stage_ner_parsing(self, email_content: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes the NER Parsing stage.

        Args:
            email_content (Optional[str]): The content of the email.

        Returns:
            Dict[str, Any]: Extracted entities from NER parsing.
        """
        if not email_content:
            self.logger.warning("No email content provided for NER Parsing.")
            return {}
        self.logger.debug("Executing NER Parsing stage.")
        try:
            if self.ner_pipeline is None:
                self.logger.warning(
                    "NER pipeline is not available. Skipping NER Parsing."
                )
                return {}
            return perform_ner(email_content, self.ner_pipeline)
        except (ValueError, OSError) as e:
            self.logger.error("Error during NER Parsing stage: %s", e)
            raise ParsingError(f"NER Parsing failed: {e}") from e
        except Exception as e:
            self.logger.error("Unexpected error during NER Parsing stage: %s", e, exc_info=True)
            raise ParsingError(f"NER Parsing failed: {e}") from e

    def _stage_donut_parsing(
        self, document_image: Optional[Union[str, Image.Image]] = None
    ) -> Dict[str, Any]:
        """
        Executes the Donut Parsing stage.

        Args:
            document_image (Optional[Union[str, Image.Image]]): Path to the document image or a PIL Image object.

        Returns:
            Dict[str, Any]: Parsed data from Donut parsing.
        """
        if not document_image:
            self.logger.warning("No document image provided for Donut Parsing.")
            return {}
        self.logger.debug("Executing Donut Parsing stage.")
        try:
            if self.donut_model is None or self.donut_processor is None:
                self.logger.warning(
                    "Donut model or processor is not available. Skipping Donut Parsing."
                )
                return {}

            # Use external perform_donut_parsing function
            donut_output = perform_donut_parsing(
                document_image=document_image,
                processor=self.donut_processor,
                model=self.donut_model,
                device=self.device,
                logger=self.logger,
            )

            if not donut_output:
                self.logger.warning("Donut Parsing returned empty output.")
                return {}

            # Map Donut output to schema
            mapped_data = self.map_donut_output_to_schema(donut_output)
            return mapped_data
        except (ValueError, OSError) as e:
            self.logger.error("Error during Donut Parsing stage: %s", e)
            raise ParsingError(f"Donut Parsing failed: {e}") from e
        except Exception as e:
            self.logger.error("Unexpected error during Donut Parsing stage: %s", e, exc_info=True)
            raise ParsingError(f"Donut Parsing failed: {e}") from e

    def _stage_model_based_parsing(
        self, email_content: Optional[str] = None
    ) -> Dict[str, Any]:
        if not email_content:
            self.logger.warning("No email content provided for Model-Based Parsing.")
            return {}
        try:
            self._lazy_load_model_parser()
            if self.model_parser is None:
                self.logger.warning(
                    "Model parser is not available. Skipping Model-Based Parsing."
                )
                return {}
            
            # Retrieve the rendered prompt
            prompt = self._render_prompt('model_based_parsing')

            # Pass the prompt to the model-based parser
            return perform_model_based_parsing(prompt, self.model_parser)
        except ParsingError as pe:
            self.logger.error(
                "ParsingError during Model-Based Parsing stage: %s", pe
            )
            raise
        except Exception as e:
            self.logger.error(
                "Unexpected error during Model-Based Parsing stage: %s", e, exc_info=True
            )
            raise ParsingError(f"Model-Based Parsing failed: {e}") from e

    def _stage_comprehensive_validation(
        self,
        email_content: Optional[str] = None,
        parsed_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the Comprehensive Validation stage.

        Args:
            email_content (Optional[str]): The content of the email.
            parsed_data (Optional[Dict[str, Any]]): Parsed data from previous stages.

        Returns:
            Dict[str, Any]: Updated parsed data after validation.
        """
        if not email_content or not parsed_data:
            self.logger.warning(
                "Insufficient data for Comprehensive Validation. Skipping this stage."
            )
            return parsed_data
        self.logger.debug("Executing Comprehensive Validation stage.")
        try:
            parsed_data = validate_internal(email_content, parsed_data, self.logger)
            parsed_data = validate_schema_internal(parsed_data, self.logger)
            return parsed_data
        except (ValueError, OSError) as e:
            self.logger.error("ValidationError during Comprehensive Validation stage: %s", e)
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(e)]
            raise ValidationError(f"Comprehensive Validation failed: {e}") from e
        except Exception as e:
            self.logger.error(
                "Unexpected error during Comprehensive Validation stage: %s", e, exc_info=True
            )
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(e)]
            raise ValidationError(f"Comprehensive Validation failed: {e}") from e

    def _stage_text_summarization(
        self,
        email_content: Optional[str] = None,
        parsed_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not email_content or not parsed_data:
            self.logger.warning(
                "Insufficient data for Text Summarization. Skipping this stage."
            )
            return
        try:
            if self.summarization_pipeline is None:
                self.logger.warning(
                    "Summarization pipeline is not available. Skipping Text Summarization."
                )
                return
            
            # Retrieve the rendered prompt
            prompt = self._render_prompt('summarization')

            # Pass the prompt to the summarization model
            summary = perform_summarization(
                prompt=prompt,
                summarization_pipeline=self.summarization_pipeline,
                logger=self.logger,
            )
            if summary:
                parsed_data["summary"] = summary
                self.logger.debug("Summarization Result: %s", parsed_data["summary"])
        except ParsingError as pe:
            self.logger.error("ParsingError during Text Summarization stage: %s", pe)
            raise
        except Exception as e:
            self.logger.error(
                "Unexpected error during Text Summarization stage: %s", e, exc_info=True
            )
            raise ParsingError(f"Text Summarization failed: {e}") from e

    def _stage_post_processing(
        self, parsed_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes the Post Processing stage.

        Args:
            parsed_data (Optional[Dict[str, Any]]): Parsed data from previous stages.

        Returns:
            Dict[str, Any]: Post-processed data.
        """
        if not parsed_data:
            self.logger.warning(
                "No parsed data available for Post Processing. Skipping this stage."
            )
            return {}
        self.logger.debug("Executing Post Processing stage.")
        try:
            return post_process_parsed_data(parsed_data, self.logger)
        except (ValueError, OSError) as e:
            self.logger.error("Error during Post Processing stage: %s", e)
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(e)]
            raise ParsingError(f"Post Processing failed: {e}") from e
        except Exception as e:
            self.logger.error(
                "Unexpected error during Post Processing stage: %s", e, exc_info=True
            )
            raise ParsingError(f"Post Processing failed: {e}") from e

    def _stage_json_validation(
        self, parsed_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Executes the JSON Validation stage.

        Args:
            parsed_data (Optional[Dict[str, Any]]): Parsed data from previous stages.
        """
        if not parsed_data:
            self.logger.warning(
                "No parsed data available for JSON Validation. Skipping this stage."
            )
            return
        self.logger.debug("Executing JSON Validation stage.")
        try:
            is_valid, error_message = validate_json(parsed_data)
            if is_valid:
                self.logger.info("JSON validation passed.")
            else:
                self.logger.error("JSON validation failed: %s", error_message)
                parsed_data["validation_issues"] = parsed_data.get(
                    "validation_issues", []
                ) + [error_message]
        except ValidationError as ve:
            self.logger.error("ValidationError during JSON validation: %s", ve)
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(ve)]
            raise
        except Exception as e:
            self.logger.error(
                "Unexpected error during JSON validation: %s", e, exc_info=True
            )
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(e)]
            raise ValidationError(f"JSON Validation failed: {e}") from e

    def map_donut_output_to_schema(self, donut_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maps the Donut model's JSON output to the predefined schema.

        Args:
            donut_json (Dict[str, Any]): JSON output from the Donut model.

        Returns:
            Dict[str, Any]: Mapped data according to the schema.
        """
        mapped_data: Dict[str, Any] = {}
        try:
            field_mapping = {
                "policy_number": (ADJUSTER_INFORMATION, "Policy #"),
                "claim_number": (REQUESTING_PARTY, "Carrier Claim Number"),
                "insured_name": (INSURED_INFORMATION, "Name"),
                "loss_address": (INSURED_INFORMATION, "Loss Address"),
                "adjuster_name": (ADJUSTER_INFORMATION, "Adjuster Name"),
                "adjuster_phone": (ADJUSTER_INFORMATION, "Adjuster Phone Number"),
                "adjuster_email": (ADJUSTER_INFORMATION, "Adjuster Email"),
                "date_of_loss": (
                    ASSIGNMENT_INFORMATION,
                    "Date of Loss/Occurrence",
                ),
                "cause_of_loss": (ASSIGNMENT_INFORMATION, "Cause of loss"),
                "loss_description": (ASSIGNMENT_INFORMATION, "Loss Description"),
                "inspection_type": (ASSIGNMENT_INFORMATION, "Inspection type"),
                "repair_progress": (
                    ASSIGNMENT_INFORMATION,
                    "Repair or Mitigation Progress",
                ),
                "residence_occupied": (
                    ASSIGNMENT_INFORMATION,
                    "Residence Occupied During Loss",
                ),
                "someone_home": (
                    ASSIGNMENT_INFORMATION,
                    "Was Someone home at time of damage",
                ),
                "type": (ASSIGNMENT_INFORMATION, "Type"),
                "additional_instructions": (
                    "Additional details/Special Instructions",
                    "Details",
                ),
                "attachments": ("Attachment(s)", "Files"),
                "owner_tenant": (
                    INSURED_INFORMATION,
                    "Is the insured an Owner or a Tenant of the loss location?",
                ),
            }
            for item in donut_json.get("form", []):
                field_name = item.get("name")
                field_value = item.get("value")
                if field_name in field_mapping:
                    section, qb_field = field_mapping[field_name]
                    if field_name in ["residence_occupied", "someone_home"]:
                        field_value = field_value.lower() in [
                            "yes",
                            "true",
                            "1",
                            "x",
                            "[x]",
                            "(x)",
                        ]
                    elif field_name == "attachments":
                        # Assuming attachments are URLs, implement validation if necessary
                        pass  # Removed redundant assignment
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
        except ValueError as ve:
            self.logger.error(
                "ValueError during mapping Donut output to schema: %s", ve
            )
            raise ValidationError(f"Donut mapping failed: {ve}") from ve
        except Exception as e:
            self.logger.error(
                "Error during mapping Donut output to schema: %s", e, exc_info=True
            )
            raise ValidationError(f"Donut mapping failed: {e}") from e

    def cleanup_resources(self):
        """
        Cleans up resources by moving models to CPU and clearing CUDA cache.
        """
        self.logger.info("Cleaning up resources.")
        try:
            models_to_cleanup = [
                (self.donut_model, "Donut model"),
                (self.ner_pipeline, "NER pipeline"),
                (self.validation_pipeline, "Validation pipeline"),
                (self.summarization_pipeline, "Summarization pipeline"),
                (
                    self.model_parser,
                    "Model-Based parser",
                ),  # Add model_parser to cleanup
            ]

            for model, name in models_to_cleanup:
                if model is not None:
                    try:
                        if hasattr(model, "model"):
                            model.model.cpu()
                        elif hasattr(model, "to"):
                            model.to("cpu")
                        self.logger.debug("%s moved to CPU.", name)
                    except ValueError as ve:
                        self.logger.error("ValueError moving %s to CPU: %s", name, ve)
                    except OSError as oe:
                        self.logger.error("OSError moving %s to CPU: %s", name, oe)
                    except Exception as e:
                        self.logger.error(
                            "Unexpected error moving %s to CPU: %s",
                            name,
                            e,
                            exc_info=True,
                        )

            torch.cuda.empty_cache()
            self.logger.info("Resources cleaned up successfully.")

            # Close asyncio loop if it exists
            if self.loop is not None and not self.loop.is_closed():
                self.loop.close()
                self.logger.debug("Asyncio event loop closed.")

        except Exception as e:
            self.logger.error("Error during cleanup: %s", e, exc_info=True)

    def recover_from_failure(self, stage: str) -> bool:
        """
        Attempts to recover from a stage failure by reinitializing the corresponding model.

        Args:
            stage (str): The name of the failed stage.

        Returns:
            bool: True if recovery was successful, False otherwise.
        """
        self.logger.warning("Attempting to recover from %s failure", stage)

        recoverable_stages = {
            "ner_parsing": lambda: setattr(
                self, "ner_pipeline", initialize_ner_pipeline(self.logger, self.config)
            ),
            "donut_parsing": lambda: [
                setattr(
                    self,
                    "donut_processor",
                    initialize_donut(self.logger, self.config)[0],
                ),
                setattr(
                    self, "donut_model", initialize_donut(self.logger, self.config)[1]
                ),
            ],
            "model_based_parsing": lambda: setattr(
                self, "model_parser", initialize_model_parser(self.logger, self.config, prompt_template=self._render_prompt('model_based_parsing'))
            ),
            "validation_parsing": lambda: setattr(
                self,
                "validation_pipeline",
                init_validation_model(self.logger, prompt_template=self._render_prompt('validation')),
            ),
            "schema_validation": lambda: setattr(
                self,
                "validation_pipeline",
                init_validation_model(self.logger, prompt_template=self._render_prompt('validation')),
            ),
            "summarization": lambda: setattr(
                self,
                "summarization_pipeline",
                initialize_summarization_pipeline(self.logger, self.config, prompt_template=self._render_prompt('summarization')),
            ),
            "post_processing": None,  # Non-recoverable
            "json_validation": None,  # Non-recoverable
        }

        stage_key = stage.lower().replace(" ", "_")

        if stage_key in recoverable_stages and recoverable_stages[stage_key]:
            try:
                recovery_actions = recoverable_stages[stage_key]
                if isinstance(recovery_actions, list):
                    for action in recovery_actions:
                        action()
                else:
                    recovery_actions()
                # Health check after recovery
                recovery_successful = self.health_check().get(stage_key, False)
                if recovery_successful:
                    self.logger.info("Successfully recovered from %s failure", stage)
                else:
                    self.logger.warning(
                        "Recovery from %s failure was unsuccessful", stage
                    )
                return recovery_successful
            except (ValueError, OSError) as e:
                self.logger.error("Error during recovery from %s: %s", stage, e)
                return False
            except Exception as e:
                self.logger.error(
                    "Unexpected error during recovery from %s: %s",
                    stage,
                    e,
                    exc_info=True,
                )
                return False

        self.logger.debug("No recovery method available for stage: %s", stage)
        return False

    def validate_input(
        self,
        email_content: Optional[str] = None,
        document_image: Optional[Union[str, Image.Image]] = None,
    ) -> bool:
        """
        Validates the input provided to the parser.

        Args:
            email_content (Optional[str]): The content of the email.
            document_image (Optional[Union[str, Image.Image]]): Path to the document image or a PIL Image object.

        Returns:
            bool: True if input is valid, False otherwise.
        """
        if not email_content and not document_image:
            self.logger.error("No input provided.")
            return False
        if document_image and not isinstance(document_image, (str, Image.Image)):
            self.logger.error("Invalid document_image type: %s", type(document_image))
            return False
        if email_content and not isinstance(email_content, str):
            self.logger.error("Invalid email_content type: %s", type(email_content))
            return False
        return True

    def __enter__(self):
        """
        Enables the EnhancedParser to be used as a context manager.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Ensures resources are cleaned up when exiting the context.
        """
        self.cleanup_resources()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Retrieves performance metrics related to memory usage and processing times.

        Returns:
            Dict[str, Any]: Dictionary containing memory usage, CPU usage, model status, and processing times.
        """
        metrics = {
            "memory_usage": self._check_memory_usage(),
            "cpu_usage_percent": psutil.cpu_percent(interval=1),
            "model_status": self.health_check(),
            "active_threads": self.get_max_workers(),
            "processing_times": {
                "ner_parsing": self.timeouts.get("ner_parsing", 30),
                "donut_parsing": self.timeouts.get("donut_parsing", 60),
                "model_based_parsing": self.timeouts.get(
                    "model_based_parsing", 45
                ),  # Include processing time for model-based parsing
                "validation_parsing": self.timeouts.get("validation_parsing", 30),
                "schema_validation": self.timeouts.get("schema_validation", 30),
                "post_processing": self.timeouts.get("post_processing", 30),
                "json_validation": self.timeouts.get("json_validation", 30),
                "summarization": self.timeouts.get("summarization", 45),
            },
        }
        return metrics

    def _check_memory_usage(self) -> Dict[str, float]:
        """
        Checks the current memory usage of CUDA devices.

        Returns:
            Dict[str, float]: Memory usage details in megabytes.
        """
        memory_info = {}
        if torch.cuda.is_available():
            memory_info["cuda"] = {
                "allocated": torch.cuda.memory_allocated() / 1024**2,
                "cached": torch.cuda.memory_reserved() / 1024**2,
                "max_allocated": torch.cuda.max_memory_allocated() / 1024**2,
            }
        return memory_info

    def health_check(self) -> Dict[str, bool]:
        """
        Performs health checks on all parser components.

        Returns:
            Dict[str, bool]: Health status of each component.
        """
        health = {
            "ner_parsing": self.ner_pipeline is not None,
            "donut_parsing": self.donut_model is not None and self.donut_processor is not None,
            "model_based_parsing": self.model_parser is not None,
            "validation_parsing": self.validation_pipeline is not None,
            "summarization": self.summarization_pipeline is not None,
        }
        self.logger.debug("Health check status: %s", health)
        return health
