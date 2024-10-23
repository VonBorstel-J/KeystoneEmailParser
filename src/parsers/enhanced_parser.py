# src/parsers/enhanced_parser.py

# Standard library imports
import logging
import os
import asyncio
from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as ConcurrentTimeoutError,
)
from typing import Any, Dict, Optional, Union

# Third-party imports
import torch
from PIL import Image
import psutil

# Local imports
from src.parsers.base_parser import BaseParser
from src.parsers.data_merger import DataMerger
from src.parsers.stages.post_processing import post_process_parsed_data
from src.parsers.stages.validation_parsing import (
    validate_internal,
    validate_schema_internal,
)
from src.parsers.stages.donut_parsing import perform_donut_parsing, initialize_donut
from src.parsers.stages.ner_parsing import perform_ner, initialize_ner_pipeline
from src.parsers.stages.summarization import (
    perform_summarization,
    initialize_summarization_pipeline,
)
from src.utils.config_loader import ConfigLoader
from src.utils.validation import validate_json

# Initialization imports
from src.parsers.parser_init import (
    setup_logging,
    init_validation_model,
)

# Constants for repeated strings
ADJUSTER_INFORMATION = "Adjuster Information"
INSURED_INFORMATION = "Insured Information"
ASSIGNMENT_INFORMATION = "Assignment Information"
REQUESTING_PARTY = "Requesting Party"


# Exceptions
class TimeoutException(Exception):
    pass


class EnhancedParser(BaseParser):
    def __init__(
        self,
        socketio: Optional[Any] = None,
        sid: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initializes the EnhancedParser with optional SocketIO, session ID, and logger.

        Args:
            socketio (Optional[Any]): SocketIO instance for real-time communication.
            sid (Optional[str]): Session ID.
            logger (Optional[logging.Logger]): Logger instance.
        """
        # Setup logging using parser_init.py's setup_logging function
        self.logger = logger or setup_logging("EnhancedParser")

        self.logger.info("Initializing EnhancedParser.")
        try:
            # Load configuration
            self.config = ConfigLoader.load_config()
            self.logger.debug("Loaded configuration: %s", self.config)

            # Check required environment variables
            self._check_environment_variables()

            # Select device
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.logger.info("Using device: %s", self.device)

            # Initialize models using parser_init.py's functions
            self.ner_pipeline = initialize_ner_pipeline(self.logger, self.config)
            self.donut_processor, self.donut_model = initialize_donut(
                self.logger, self.config
            )
            self.validation_pipeline = init_validation_model(self.logger, self.config)
            self.summarization_pipeline = initialize_summarization_pipeline(
                self.logger, self.config
            )

            # Verify that all models are initialized
            if not self.health_check():
                self.logger.error("One or more models failed to initialize.")
                raise RuntimeError("Parser initialization failed due to model errors.")

            self.socketio = socketio
            self.sid = sid
            self.timeouts = self._set_timeouts()

            # Initialize DataMerger with the logger
            self.data_merger = DataMerger(self.logger)

            # Initialize ThreadPoolExecutor for asynchronous processing
            self.executor = ThreadPoolExecutor(
                max_workers=self._determine_thread_count()
            )
            self.loop = asyncio.get_event_loop()

            self.logger.info("EnhancedParser initialized successfully.")
        except (ValueError, OSError, RuntimeError) as e:
            self.logger.error(
                "Error during EnhancedParser initialization: %s", e, exc_info=True
            )
            raise

    def health_check(self) -> bool:
        """
        Checks if all components are initialized and healthy.

        Returns:
            bool: True if all components are healthy, False otherwise.
        """
        components_healthy = all(
            [
                self.ner_pipeline is not None,
                self.donut_model is not None,
                self.validation_pipeline is not None,
                self.summarization_pipeline is not None,
            ]
        )
        if not components_healthy:
            self.logger.error("One or more components failed to initialize.")
            return False
        self.logger.info("All components are initialized and healthy.")
        return True

    def _check_environment_variables(self):
        """
        Checks for required environment variables and raises an error if any are missing.
        """
        required_vars = ["HF_TOKEN"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            self.logger.error(
                "Missing required environment variables: %s", ", ".join(missing_vars)
            )
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

    def _set_timeouts(self) -> Dict[str, int]:
        """
        Sets processing timeouts based on configuration.

        Returns:
            Dict[str, int]: Dictionary of timeout settings.
        """
        timeouts = {
            "ner_parsing": self.config.get("model_timeouts", {}).get("ner_parsing", 30),
            "donut_parsing": self.config.get("model_timeouts", {}).get(
                "donut_parsing", 60
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
            "summarization": self.config.get("model_timeouts", {}).get(
                "summarization", 45
            ),
        }
        self.logger.debug("Set processing timeouts: %s", timeouts)
        return timeouts

    def _determine_thread_count(self) -> int:
        """
        Determines the optimal number of threads based on CPU count.

        Returns:
            int: Number of threads.
        """
        cpu_count = psutil.cpu_count(logical=True)
        thread_count = min(32, cpu_count * 4) if cpu_count else 8
        self.logger.debug("Determined thread count: %d", thread_count)
        return thread_count

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
        except ValueError as ve:
            self.logger.error("ValueError in parse_email: %s", ve)
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
            ("NER Parsing", self._stage_ner_parsing, {"email_content": email_content}),
            (
                "Donut Parsing",
                self._stage_donut_parsing,
                {"document_image": document_image},
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
                if stage_name == "Donut Parsing" and not kwargs.get("document_image"):
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
                    parsed_data = self.data_merger.merge_parsed_data(
                        parsed_data, stage_result
                    )
            except ConcurrentTimeoutError:
                self.logger.error(
                    "Stage '%s' timed out after %d seconds.",
                    stage_name,
                    timeout_seconds,
                )
                recovery_successful = self.recover_from_failure(stage_name)
                if recovery_successful:
                    self.logger.info(
                        f"Recovered from timeout in stage '{stage_name}'. Retrying..."
                    )
                    try:
                        with ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(stage_method, **kwargs)
                            stage_result = future.result(timeout=timeout_seconds)
                        if isinstance(stage_result, dict) and stage_result:
                            parsed_data = self.data_merger.merge_parsed_data(
                                parsed_data, stage_result
                            )
                    except (ConcurrentTimeoutError, ValueError, OSError) as e:
                        self.logger.error(
                            "Failed to recover and execute stage '%s': %s",
                            stage_name,
                            e,
                        )
                else:
                    self.logger.warning(
                        f"Could not recover from timeout in stage '{stage_name}'."
                    )
            except Exception as e:
                self.logger.error(
                    "Error in stage '%s': %s", stage_name, e, exc_info=True
                )
        self.logger.info("Parsing process completed.")
        return parsed_data

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
            self.logger.error("ValueError during NER Parsing stage: %s", e)
            return {}
        except Exception as e:
            self.logger.error("Error during NER Parsing stage: %s", e, exc_info=True)
            return {}

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
            self.logger.error("ValueError during Donut Parsing stage: %s", e)
            return {}
        except Exception as e:
            self.logger.error("Error during Donut Parsing stage: %s", e, exc_info=True)
            return {}

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
            self.logger.error("ValueError during Comprehensive Validation stage: %s", e)
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(e)]
            return parsed_data
        except Exception as e:
            self.logger.error(
                "Error during Comprehensive Validation stage: %s", e, exc_info=True
            )
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(e)]
            return parsed_data

    def _stage_text_summarization(
        self,
        email_content: Optional[str] = None,
        parsed_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Executes the Text Summarization stage.

        Args:
            email_content (Optional[str]): The content of the email.
            parsed_data (Optional[Dict[str, Any]]): Parsed data from previous stages.
        """
        if not email_content or not parsed_data:
            self.logger.warning(
                "Insufficient data for Text Summarization. Skipping this stage."
            )
            return
        self.logger.debug("Executing Text Summarization stage.")
        try:
            if self.summarization_pipeline is None:
                self.logger.warning(
                    "Summarization pipeline is not available. Skipping Text Summarization."
                )
                return
            summary = perform_summarization(
                email_content=email_content,
                summarization_pipeline=self.summarization_pipeline,
                logger=self.logger,
            )
            if summary:
                parsed_data["summary"] = summary
                self.logger.debug("Summarization Result: %s", parsed_data["summary"])
        except (ValueError, OSError) as e:
            self.logger.error("ValueError during Text Summarization stage: %s", e)
        except Exception as e:
            self.logger.error(
                "Error during Text Summarization stage: %s", e, exc_info=True
            )

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
            self.logger.error("ValueError during Post Processing stage: %s", e)
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(e)]
            return parsed_data
        except Exception as e:
            self.logger.error(
                "Error during Post Processing stage: %s", e, exc_info=True
            )
            return parsed_data

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
        except ValueError as ve:
            self.logger.error("ValueError during JSON validation: %s", ve)
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(ve)]
        except Exception as e:
            self.logger.error(
                "Unexpected error during JSON validation: %s", e, exc_info=True
            )
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(e)]

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
            return {}
        except Exception as e:
            self.logger.error(
                "Error during mapping Donut output to schema: %s", e, exc_info=True
            )
            return {}

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
            "validation_parsing": lambda: setattr(
                self,
                "validation_pipeline",
                init_validation_model(self.logger, self.config),
            ),
            "schema_validation": lambda: setattr(
                self,
                "validation_pipeline",
                init_validation_model(self.logger, self.config),
            ),
            "summarization": lambda: setattr(
                self,
                "summarization_pipeline",
                initialize_summarization_pipeline(self.logger, self.config),
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
                recovery_successful = self.health_check()
                if recovery_successful:
                    self.logger.info("Successfully recovered from %s failure", stage)
                else:
                    self.logger.warning(
                        "Recovery from %s failure was unsuccessful", stage
                    )
                return recovery_successful
            except (ValueError, OSError) as e:
                self.logger.error("ValueError during recovery from %s: %s", stage, e)
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
            self.logger.error("No input provided")
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
