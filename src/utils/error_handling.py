# src/utils/error_handling.py

import logging
from typing import Dict, Any

def log_error(logger: logging.Logger, error_message: str, error: Exception = None):
    """
    Log an error message and optionally the exception details.
    """
    if error:
        logger.error(f"{error_message}: {str(error)}", exc_info=True)
    else:
        logger.error(error_message)

def handle_parsing_error(logger: logging.Logger, error: Exception, stage: str) -> Dict[str, Any]:
    """
    Handle parsing errors by logging them and returning a structured error response.
    """
    error_message = f"Error during {stage}: {str(error)}"
    log_error(logger, error_message, error)
    return {
        "error": True,
        "stage": stage,
        "message": str(error)
    }

