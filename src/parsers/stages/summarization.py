import logging
import re
from typing import Dict, Any
from transformers import pipeline
import torch

def initialize_summarization_pipeline(logger: logging.Logger, config: Dict[str, Any]):
    """
    Initializes the summarization pipeline.

    Args:
        logger (logging.Logger): Logger instance.
        config (Dict[str, Any]): Configuration dictionary.

    Returns:
        pipeline: Initialized summarization pipeline.
    """
    try:
        logger.debug("Loading Summarization model and tokenizer.")
        summarizer = pipeline(
            "summarization",
            model=config['models']['summarization']['repo_id'],
            tokenizer=config['models']['summarization']['repo_id'],
            device=0 if config['processing']['device'] == 'cuda' and torch.cuda.is_available() else -1,
            framework='pt'
        )
        logger.info("Summarization pipeline initialized successfully.")
        return summarizer
    except Exception as e:
        logger.error(f"Failed to initialize Summarization pipeline: {e}", exc_info=True)
        return None

def perform_summarization(email_content: str, summarization_pipeline, logger: logging.Logger) -> str:
    """
    Generates a summary of the email content.

    Args:
        email_content (str): The content of the email.
        summarization_pipeline: The initialized summarization pipeline.
        logger (logging.Logger): Logger instance.

    Returns:
        str: Generated summary.
    """
    try:
        logger.debug("Starting summarization process.")
        # Handle large inputs by chunking if necessary
        max_chunk = 1000  # Define based on model's max token limit
        if len(email_content) > max_chunk:
            logger.debug("Email content exceeds max_chunk size. Splitting into chunks.")
            chunks = split_text(email_content, max_chunk)
            summaries = []
            for chunk in chunks:
                summary = summarization_pipeline(
                    chunk,
                    max_length=150,
                    min_length=50,
                    do_sample=False
                )
                summaries.append(summary[0]['summary_text'])
            final_summary = " ".join(summaries)
        else:
            summary = summarization_pipeline(
                email_content,
                max_length=150,
                min_length=50,
                do_sample=False
            )
            final_summary = summary[0]['summary_text']
        logger.debug(f"Generated summary: {final_summary}")
        return final_summary
    except Exception as e:
        logger.error(f"Error during summarization: {e}", exc_info=True)
        return ""

def split_text(text: str, max_length: int) -> list[str]:
    """
    Splits text into chunks of specified maximum length.

    Args:
        text (str): The text to split.
        max_length (int): Maximum length of each chunk.

    Returns:
        List[str]: List of text chunks.
    """
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += " " + sentence
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks
