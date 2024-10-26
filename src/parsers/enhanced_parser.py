# src/parsers/enhanced_parser.py

import logging
import os
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as ConcurrentTimeoutError
from typing import Any, Dict, Optional, Union, Callable, List, Tuple

import torch
from PIL import Image
import psutil
from jinja2 import Template

from src.parsers.base_parser import BaseParser
from src.parsers.data_merger import DataMerger
from src.parsers.stages.post_processing import post_process_parsed_data
from src.parsers.stages.validation_parsing import (
    validate_internal,
    validate_schema_internal,
)
from src.parsers.stages.donut_parsing import perform_donut_parsing, initialize_donut
from src.parsers.stages.model_based_parsing import (
    perform_model_based_parsing,
    initialize_model_parser,
)
from src.utils.config import Config
from src.utils.validation import validate_json
from src.utils.email_utils import parse_email
from src.utils.exceptions import ValidationError, ParsingError, InitializationError

ADJUSTER_INFORMATION: str = "Adjuster Information"
REQUESTING_PARTY: str = "Requesting Party"
INSURED_INFORMATION: str = "Insured Information"
ASSIGNMENT_INFORMATION: str = "Assignment Information"

class EnhancedParser(BaseParser):
    REQUIRED_ENV_VARS = ["HF_TOKEN", "HF_HOME"]

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        socketio: Optional[Any] = None,
        sid: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__()
        self.lock = threading.Lock()
        self._init_core_attributes(config, socketio, sid, logger)
        self.device: Optional[str] = None
        self.donut_processor = None
        self.donut_model = None
        self.llama_model = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.executor: Optional[ThreadPoolExecutor] = None
        self.data_merger: DataMerger = DataMerger(self.logger)
        self._initialize_event_loop()

    def _init_core_attributes(
        self,
        config: Optional[Dict[str, Any]],
        socketio: Optional[Any],
        sid: Optional[str],
        logger: Optional[logging.Logger],
    ):
        Config.initialize()
        self.config: Dict[str, Any] = config or Config.get_full_config()
        self.logger: logging.Logger = logger or self._setup_logging()
        self.socketio = socketio
        self.sid = sid

    def _initialize_event_loop(self) -> None:
        """Initialize the asyncio event loop in a thread-safe manner."""
        try:
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                
            if self.loop.is_closed():
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                
            self.logger.debug("Event loop initialized successfully")
        except Exception as e:
            self.logger.error("Failed to initialize asyncio loop", exc_info=True)
            raise InitializationError(f"Asyncio loop initialization failed: {e}") from e

    async def parse_async(
        self,
        email_content: Optional[str] = None,
        document_image: Optional[Union[str, Image.Image]] = None,
    ) -> Dict[str, Any]:
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
        if not self.validate_input(email_content, document_image):
            self.logger.error("Invalid input provided to parse_email.")
            return {}
        parsed_data = self.parse(email_content, document_image)
        try:
            is_valid, errors = validate_json(parsed_data)
            if not is_valid:
                self.logger.warning("JSON validation failed: %s", errors)
                parsed_data["validation_issues"] = parsed_data.get(
                    "validation_issues", []
                )
                parsed_data["validation_issues"].append(errors)
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
        self.logger.info("Starting parsing process.")
        parsed_data: Dict[str, Any] = {}
        input_type = self._detect_input_type(email_content, document_image)

        try:
            with self.lock:
                self._initialize_executor()
                self._initialize_models(input_type)

            stages = self._get_parsing_stages(
                email_content, document_image, parsed_data
            )

            for stage in stages:
                parsed_data = self._process_parsing_stage(stage, parsed_data)

            return parsed_data

        except Exception as e:
            self.logger.error("Error during parsing: %s", e, exc_info=True)
            return self._handle_parsing_error(e, parsed_data)
        finally:
            self.cleanup_resources()

    def _detect_input_type(
        self,
        email_content: Optional[str],
        document_image: Optional[Union[str, Image.Image]],
    ) -> str:
        if email_content and document_image:
            return 'both'
        elif email_content:
            return 'text'
        elif document_image:
            return 'image'
        else:
            return 'none'

    def _initialize_executor(self):
        if not self.executor:
            self.executor = ThreadPoolExecutor(
                max_workers=self._determine_thread_count()
            )
            self.logger.debug("ThreadPoolExecutor initialized.")

    def _initialize_models(self, input_type: str) -> None:
        try:
            if input_type in ['image', 'both'] and not self.donut_model:
                self.donut_processor, self.donut_model = self._initialize_with_retry(
                    initialize_donut, self.logger, Config.get_model_config("donut")
                )

            if input_type in ['text', 'both'] and not self.llama_model:
                self.llama_model = self._initialize_with_retry(
                    initialize_model_parser,
                    self.logger,
                    Config.get_model_config("llama"),
                    prompt_templates=self._render_prompts(),
                )

            self.device = Config.get_device()

        except InitializationError:
            raise
        except Exception as e:
            self.logger.error("Failed to initialize models: %s", e, exc_info=True)
            raise InitializationError(f"Model initialization failed: {e}") from e

    def _check_environment_variables(self) -> None:
        missing_vars = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing_vars:
            self.logger.error(
                "Missing required environment variables: %s",
                ", ".join(missing_vars),
            )
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger("EnhancedParser")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
        return logger

    def _initialize_with_retry(self, init_func: Callable, *args, **kwargs) -> Any:
        max_retries = kwargs.pop("max_retries", 3)
        for attempt in range(max_retries):
            try:
                component = init_func(*args, **kwargs)
                self.logger.debug(
                    "Successfully initialized %s on attempt %d.",
                    init_func.__name__,
                    attempt + 1,
                )
                return component
            except (ValueError, OSError, TypeError) as e:
                if attempt == max_retries - 1:
                    self.logger.error(
                        "Failed to initialize %s after %d attempts: %s",
                        init_func.__name__,
                        max_retries,
                        e,
                        exc_info=True,
                    )
                    raise InitializationError(
                        f"Initialization failed for {init_func.__name__}: {e}"
                    ) from e
                self.logger.warning(
                    "Initialization attempt %d for %s failed: %s. Retrying...",
                    attempt + 1,
                    init_func.__name__,
                    e,
                )
                torch.cuda.empty_cache()

    def _determine_thread_count(self) -> int:
        cpu_count = psutil.cpu_count(logical=True)
        available_memory_gb = psutil.virtual_memory().available / (1024**3)

        thread_count = min(
            16,
            cpu_count * 2,
            int(available_memory_gb * 2),
        )

        self.logger.debug("Determined thread count: %d", thread_count)
        return max(1, thread_count)

    def _set_timeouts(self) -> Dict[str, int]:
        return {
            "donut_parsing": Config.get_model_config("donut").get("timeout", 60),
            "llama_text_extraction": Config.get_model_config("llama").get("timeout_text_extraction", 60),
            "llama_validation": Config.get_model_config("llama").get("timeout_validation", 45),
            "llama_summarization": Config.get_model_config("llama").get("timeout_summarization", 30),
            "post_processing": Config.get_model_config("post_processing").get("timeout", 30),
            "json_validation": Config.get_model_config("json_validation").get("timeout", 30),
        }

    def _render_prompts(self) -> Dict[str, str]:
        prompts = {}
        prompt_config = self.config.get("models", {}).get("llama", {}).get("prompt_templates", {})
        for task, template in prompt_config.items():
            if template:
                data_points = Config.get_data_points()
                template_obj = Template(template)
                prompts[task] = template_obj.render(data_points=data_points)
            else:
                prompts[task] = ""
        return prompts

    def _get_parsing_stages(
        self,
        email_content: Optional[str],
        document_image: Optional[Union[str, Image.Image]],
        parsed_data: Dict[str, Any],
    ) -> List[Tuple[str, Callable, Dict[str, Any]]]:
        enabled_stages = Config.get_enabled_stages()
        stages = []

        if "Email Parsing" in enabled_stages and email_content:
            stages.append(
                (
                    "Email Parsing",
                    self._stage_email_parsing,
                    {"email_content": email_content},
                )
            )
        if "Donut Parsing" in enabled_stages and document_image:
            stages.append(
                (
                    "Donut Parsing",
                    self._stage_donut_parsing,
                    {"document_image": document_image},
                )
            )
        if "Text Extraction" in enabled_stages and email_content:
            stages.append(
                (
                    "Text Extraction",
                    self._stage_text_extraction,
                    {"email_content": email_content},
                )
            )
        if "Validation" in enabled_stages and email_content:
            stages.append(
                (
                    "Validation",
                    self._stage_validation,
                    {"email_content": email_content, "parsed_data": parsed_data},
                )
            )
        if "Summarization" in enabled_stages and email_content:
            stages.append(
                (
                    "Summarization",
                    self._stage_summarization,
                    {"email_content": email_content, "parsed_data": parsed_data},
                )
            )
        if "Post Processing" in enabled_stages and parsed_data:
            stages.append(
                (
                    "Post Processing",
                    self._stage_post_processing,
                    {"parsed_data": parsed_data},
                )
            )
        if "JSON Validation" in enabled_stages and parsed_data:
            stages.append(
                (
                    "JSON Validation",
                    self._stage_json_validation,
                    {"parsed_data": parsed_data},
                )
            )

        return stages

    def _process_parsing_stage(
        self,
        stage: Tuple[str, Callable, Dict[str, Any]],
        parsed_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        stage_name, stage_method, kwargs = stage
        self.logger.info("Starting stage: %s", stage_name)

        try:
            future = self.executor.submit(stage_method, **kwargs)
            stage_result = future.result(
                timeout=self._get_stage_timeout(stage_name)
            )

            if isinstance(stage_result, dict) and stage_result:
                parsed_data = self.data_merger.merge_parsed_data(
                    parsed_data, stage_result
                )

            self.logger.info("Completed stage: %s", stage_name)
            return parsed_data

        except ConcurrentTimeoutError:
            self.logger.error(
                "Timeout in stage '%s': exceeded %d seconds.",
                stage_name,
                self._get_stage_timeout(stage_name),
            )
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [f"Stage '{stage_name}' timed out."]
            if not self.recover_from_failure(stage_name.lower().replace(" ", "_")):
                self.logger.warning(
                    "Failed to recover from timeout in stage '%s'. Continuing with next stage.",
                    stage_name,
                )
        except ParsingError as pe:
            self.logger.error(
                "ParsingError in stage '%s': %s", stage_name, pe, exc_info=True
            )
            if not self.recover_from_failure(stage_name.lower().replace(" ", "_")):
                self.logger.warning(
                    "Failed to recover from error in stage '%s'. Continuing with next stage.",
                    stage_name,
                )
        except ValidationError as ve:
            self.logger.error(
                "ValidationError in stage '%s': %s", stage_name, ve, exc_info=True
            )
            if not self.recover_from_failure(stage_name.lower().replace(" ", "_")):
                self.logger.warning(
                    "Failed to recover from validation error in stage '%s'. Continuing with next stage.",
                    stage_name,
                )
        except Exception as e:
            self.logger.error(
                "Unexpected error in stage '%s': %s", stage_name, e, exc_info=True
            )
            if not self.recover_from_failure(stage_name.lower().replace(" ", "_")):
                self.logger.warning(
                    "Failed to recover from error in stage '%s'. Continuing with next stage.",
                    stage_name,
                )
        return parsed_data

    def _get_stage_timeout(self, stage_name: str) -> int:
        stage_key = stage_name.lower().replace(" ", "_")
        return self.timeouts.get(stage_key, 60)

    def _handle_parsing_error(
        self, error: Exception, parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        self.logger.error("Parsing process failed: %s", error, exc_info=True)
        parsed_data["validation_issues"] = parsed_data.get("validation_issues", []) + [
            str(error)
        ]
        return parsed_data

    def _handle_stage_error(
        self, stage_name: str, error: Exception, parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        if isinstance(error, (ConcurrentTimeoutError, ParsingError, ValidationError)):
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(error)]
        else:
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [f"Unexpected error in stage '{stage_name}': {error}"]
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
            self.logger.error("ParsingError during Email Parsing stage: %s", pe)
            raise
        except Exception as e:
            self.logger.error("Error during Email Parsing stage: %s", e, exc_info=True)
            raise ParsingError(f"Email Parsing failed: {e}") from e

    def _stage_donut_parsing(
        self, document_image: Optional[Union[str, Image.Image]] = None
    ) -> Dict[str, Any]:
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

            donut_output = perform_donut_parsing(
                document_image=document_image,
                processor=self.donut_processor,
                model=self.donut_model,
                device=self.device,
                logger=self.logger,
                config=self.config,
            )

            if not donut_output:
                self.logger.warning("Donut Parsing returned empty output.")
                return {}

            mapped_data = self.map_donut_output_to_schema(donut_output)
            return mapped_data
        except (ValueError, OSError) as e:
            self.logger.error("Error during Donut Parsing stage: %s", e)
            raise ParsingError(f"Donut Parsing failed: {e}") from e
        except Exception as e:
            self.logger.error(
                "Unexpected error during Donut Parsing stage: %s", e, exc_info=True
            )
            raise ParsingError(f"Donut Parsing failed: {e}") from e

    def _stage_text_extraction(
        self, email_content: Optional[str] = None
    ) -> Dict[str, Any]:
        if not email_content:
            self.logger.warning("No email content provided for Text Extraction.")
            return {}
        try:
            if self.llama_model is None:
                self.logger.warning(
                    "LLaMA model is not available. Skipping Text Extraction."
                )
                return {}

            prompt = self.llama_model['prompt_templates'].get("text_extraction", "")
            if not prompt:
                self.logger.warning("No prompt template for Text Extraction.")
                return {}

            extracted_text = perform_model_based_parsing(
                prompt, self.llama_model['model'], self.logger
            )
            return {"extracted_text": extracted_text}
        except ParsingError as pe:
            self.logger.error("ParsingError during Text Extraction stage: %s", pe)
            raise
        except Exception as e:
            self.logger.error(
                "Unexpected error during Text Extraction stage: %s",
                e,
                exc_info=True,
            )
            raise ParsingError(f"Text Extraction failed: {e}") from e

    def _stage_validation(
        self,
        email_content: Optional[str] = None,
        parsed_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not email_content or not parsed_data:
            self.logger.warning(
                "Insufficient data for Validation. Skipping this stage."
            )
            return parsed_data
        self.logger.debug("Executing Validation stage.")
        try:
            prompt = self.llama_model['prompt_templates'].get("validation", "")
            if not prompt:
                self.logger.warning("No prompt template for Validation.")
                return parsed_data

            validated_data = perform_model_based_parsing(
                prompt, self.llama_model['model'], self.logger
            )
            parsed_data.update(validated_data)
            return parsed_data
        except (ValueError, OSError) as e:
            self.logger.error(
                "ValidationError during Validation stage: %s", e
            )
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(e)]
            raise ValidationError(f"Validation failed: {e}") from e
        except Exception as e:
            self.logger.error(
                "Unexpected error during Validation stage: %s",
                e,
                exc_info=True,
            )
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(e)]
            raise ValidationError(f"Validation failed: {e}") from e

    def _stage_summarization(
        self,
        email_content: Optional[str] = None,
        parsed_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not email_content or not parsed_data:
            self.logger.warning(
                "Insufficient data for Summarization. Skipping this stage."
            )
            return
        try:
            if self.llama_model is None:
                self.logger.warning(
                    "LLaMA model is not available. Skipping Summarization."
                )
                return

            prompt = self.llama_model['prompt_templates'].get("summarization", "")
            if not prompt:
                self.logger.warning("No prompt template for Summarization.")
                return

            summary = perform_model_based_parsing(
                prompt, self.llama_model['model'], self.logger
            )
            if summary:
                parsed_data["summary"] = summary
                self.logger.debug("Summarization Result: %s", parsed_data["summary"])
        except ParsingError as pe:
            self.logger.error("ParsingError during Summarization stage: %s", pe)
            raise
        except Exception as e:
            self.logger.error(
                "Unexpected error during Summarization stage: %s", e, exc_info=True
            )
            raise ParsingError(f"Summarization failed: {e}") from e

    def _stage_post_processing(
        self, parsed_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not parsed_data:
            self.logger.warning(
                "No parsed data available for Post Processing. Skipping this stage."
            )
            return {}
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
            parsed_data["validation_issues"] = parsed_data.get(
                "validation_issues", []
            ) + [str(e)]
            raise ParsingError(f"Post Processing failed: {e}") from e

    def _stage_json_validation(
        self, parsed_data: Optional[Dict[str, Any]] = None
    ) -> None:
        if not parsed_data:
            self.logger.warning(
                "No parsed data available for JSON Validation. Skipping this stage."
            )
            return
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
                        field_value = field_value.lower() in ["yes", "true", "1"]
                    mapped_data.setdefault(section, {}).setdefault(qb_field, []).append(
                        field_value
                    )
            return mapped_data
        except ValueError as ve:
            self.logger.error(f"ValueError during Donut mapping: {ve}")
            raise ValidationError(f"Donut mapping failed: {ve}") from ve
        except Exception as e:
            self.logger.error(f"Error during Donut mapping: {e}", exc_info=True)
            raise ValidationError(f"Donut mapping failed: {e}") from e

    def cleanup_resources(self):
        """Clean up resources including the event loop."""
        self.logger.info("Starting resource cleanup.")
        cleanup_errors = []

        try:
            with self.lock:
                self._cleanup_models(cleanup_errors)
                self._cleanup_executor(cleanup_errors)

            if cleanup_errors:
                self.logger.warning("Cleanup completed with errors: %s", cleanup_errors)
            else:
                self.logger.info("Cleanup completed successfully")

        except Exception as e:
            self.logger.error("Fatal error during cleanup: %s", e, exc_info=True)
            raise

    def _cleanup_models(self, cleanup_errors: List[str]):
        models_to_cleanup = [
            (self.donut_model, "Donut model"),
            (self.donut_processor, "Donut processor"),
            (self.llama_model, "LLaMA model"),
        ]

        for model, name in models_to_cleanup:
            if model is not None:
                try:
                    if hasattr(model, "model"):
                        model.model.cpu()
                    elif hasattr(model, "to"):
                        model.to("cpu")
                except ValueError as ve:
                    error_msg = f"ValueError moving {name} to CPU: {ve}"
                    self.logger.error(error_msg)
                    cleanup_errors.append(error_msg)
                except OSError as oe:
                    error_msg = f"OSError moving {name} to CPU: {oe}"
                    self.logger.error(error_msg)
                    cleanup_errors.append(error_msg)
                except Exception as e:
                    error_msg = f"Unexpected error moving {name} to CPU: {e}"
                    self.logger.error(
                        "Unexpected error moving %s to CPU: %s",
                        name,
                        e,
                        exc_info=True,
                    )
                    cleanup_errors.append(error_msg)

    def _cleanup_executor(self, cleanup_errors: List[str]):
        if self.executor:
            try:
                self.executor.shutdown(wait=True)
                self.logger.debug("Executor shutdown successfully.")
            except Exception as e:
                error_msg = f"Error during executor shutdown: {e}"
                self.logger.error(error_msg)
                cleanup_errors.append(error_msg)

    def _unload_models(self):
        models_to_unload = [
            "donut_model",
            "donut_processor",
            "llama_model",
        ]

        for model_attr in models_to_unload:
            model = getattr(self, model_attr, None)
            if model is not None:
                delattr(self, model_attr)
                self.logger.debug(f"Unloaded {model_attr} from memory.")
        torch.cuda.empty_cache()
        self.logger.debug("Cleared CUDA cache.")

    def recover_from_failure(self, stage: str) -> bool:
        self.logger.warning("Attempting to recover from %s failure", stage)

        recoverable_stages = {
            "donut_parsing": lambda: self._recover_donut_parsing(),
            "text_extraction": lambda: self._recover_llama(),
            "validation": lambda: self._recover_llama(),
            "summarization": lambda: self._recover_llama(),
            "post_processing": None,
            "json_validation": None,
        }

        stage_key = stage.lower().replace(" ", "_")

        recovery_action = recoverable_stages.get(stage_key)
        if recovery_action:
            try:
                recovery_action()
                self._initialize_executor()
                self._initialize_models(self.input_type)
                health = self.health_check()
                recovery_successful = health.get(stage_key, False)
                if recovery_successful:
                    self.logger.info("Successfully recovered from %s failure", stage)
                else:
                    self.logger.warning(
                        "Recovery from %s failure was unsuccessful", stage
                    )
                return recovery_successful
            except (ValueError, OSError, TypeError) as e:
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

    def _recover_donut_parsing(self):
        self.donut_processor, self.donut_model = initialize_donut(
            self.logger, self.config
        )

    def _recover_llama(self):
        self.llama_model = initialize_model_parser(
            self.logger,
            self.config,
            prompt_templates=self._render_prompts(),
        )

    def validate_input(
        self,
        email_content: Optional[str] = None,
        document_image: Optional[Union[str, Image.Image]] = None,
    ) -> bool:
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
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_resources()

    def get_performance_metrics(self) -> Dict[str, Any]:
        metrics = {
            "memory_usage": self._check_memory_usage(),
            "cpu_usage_percent": psutil.cpu_percent(interval=1),
            "model_status": self.health_check(),
            "active_threads": self.max_workers,
            "processing_times": {
                "donut_parsing": self.timeouts.get("donut_parsing", 60),
                "llama_text_extraction": self.timeouts.get("llama_text_extraction", 60),
                "llama_validation": self.timeouts.get("llama_validation", 45),
                "llama_summarization": self.timeouts.get("llama_summarization", 30),
                "post_processing": self.timeouts.get("post_processing", 30),
                "json_validation": self.timeouts.get("json_validation", 30),
            },
        }
        return metrics

    def _check_memory_usage(self) -> Dict[str, float]:
        memory_info = {}
        if torch.cuda.is_available():
            memory_info["cuda"] = {
                "allocated": torch.cuda.memory_allocated() / 1024**2,
                "cached": torch.cuda.memory_reserved() / 1024**2,
                "max_allocated": torch.cuda.max_memory_allocated() / 1024**2,
            }
        return memory_info

    def health_check(self) -> Dict[str, bool]:
        health = {
            "donut_parsing": self.donut_model is not None
            and self.donut_processor is not None,
            "llama_text_extraction": self.llama_model is not None,
            "llama_validation": self.llama_model is not None,
            "llama_summarization": self.llama_model is not None,
        }
        self.logger.debug("Health check status: %s", health)
        return health

    @property
    def max_workers(self) -> int:
        if not self.executor:
            return 0
        try:
            return getattr(self.executor, "_max_workers", 0)
        except AttributeError:
            self.logger.warning("Unable to get max workers count")
            return 0
