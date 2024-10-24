# src/parsers/stages/summarization.py

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import re
import torch
from transformers import pipeline
from src.utils.error_handling import log_error
from src.utils.config import Config

@dataclass
class SummarizationConfig:
    """Configuration for summarization parameters."""
    max_chunk_size: int = 1000
    min_summary_length: int = 50
    max_summary_length: int = 150
    stride: int = 100
    temperature: float = 0.7
    top_p: float = 0.9
    max_retries: int = 3

class SummarizationError(Exception):
    """Custom exception for summarization-related errors."""
    pass

def initialize_summarization_pipeline(logger: logging.Logger, config: Dict[str, Any]) -> Optional[pipeline]:
    """
    Initializes the summarization pipeline with error handling and configuration validation.

    Args:
        logger (logging.Logger): Logger instance.
        config (Dict[str, Any]): Configuration dictionary.

    Returns:
        Optional[pipeline]: Initialized summarization pipeline or None if initialization fails.
    """
    try:
        logger.debug("Loading Summarization model and tokenizer.")
        model_config = config.get('models', {}).get('summarization', {})
        
        if not model_config:
            raise ValueError("Missing summarization model configuration")

        device = 0 if (
            config.get('processing', {}).get('device') == 'cuda' 
            and torch.cuda.is_available()
        ) else -1

        summarizer = pipeline(
            task="summarization",
            model=model_config['repo_id'],
            tokenizer=model_config['repo_id'],
            device=device,
            framework='pt'
        )
        
        logger.info(f"Summarization pipeline initialized successfully using model: {model_config['repo_id']}")
        return summarizer
    except Exception as e:
        log_error(logger, f"Failed to initialize Summarization pipeline: {str(e)}", e)
        return None

def preprocess_text(text: str, config: Dict[str, Any]) -> str:
    """
    Preprocesses text before summarization.
    
    Args:
        text (str): Text to preprocess.
        config (Dict[str, Any]): Configuration dictionary.
        
    Returns:
        str: Preprocessed text.
    """
    preprocessing_config = config.get('models', {}).get('summarization', {}).get('parameters', {}).get('preprocessing', {})
    
    if preprocessing_config.get('normalize_whitespace', True):
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r'\s+', ' ', text)
    
    if preprocessing_config.get('clean_headers', True):
        text = re.sub(r'^.*?Subject:', 'Subject:', text, flags=re.DOTALL)
    
    if preprocessing_config.get('remove_signatures', True):
        text = re.sub(r'(--)?\s*Best regards,?.*$', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'(--)?\s*Regards,?.*$', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'(--)?\s*Sincerely,?.*$', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    return text.strip()

def split_text(text: str, max_length: int, stride: int, logger: logging.Logger) -> List[str]:
    """
    Splits text into overlapping chunks for better context preservation.

    Args:
        text (str): Text to split.
        max_length (int): Maximum length of each chunk.
        stride (int): Overlap between chunks.
        logger (logging.Logger): Logger instance.

    Returns:
        List[str]: List of text chunks.
    """
    try:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length <= max_length:
                current_chunk.append(sentence)
                current_length += sentence_length
            else:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    # Keep last few sentences for context
                    overlap_sentences = current_chunk[-stride:]
                    current_chunk = overlap_sentences + [sentence]
                    current_length = sum(len(s) for s in current_chunk)
                else:
                    chunks.append(sentence[:max_length])
                    current_chunk = []
                    current_length = 0

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        logger.debug(f"Split text into {len(chunks)} chunks")
        return chunks
    except Exception as e:
        logger.error(f"Error splitting text: {str(e)}")
        return [text]  # Return original text as single chunk on error

def perform_summarization(
    email_content: str, 
    summarization_pipeline: pipeline, 
    logger: logging.Logger,
    config: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generates a summary of the email content with improved error handling and chunking.

    Args:
        email_content (str): The content of the email.
        summarization_pipeline: The initialized summarization pipeline.
        logger (logging.Logger): Logger instance.
        config (Optional[Dict[str, Any]]): Configuration dictionary. If None, will use default config.

    Returns:
        str: Generated summary.

    Raises:
        SummarizationError: If summarization fails.
    """
    try:
        logger.debug("Starting summarization process.")
        
        if not email_content.strip():
            raise ValueError("Empty email content provided")

        # Load configuration
        config = config or Config.get_model_config('summarization')
        summarization_params = config.get('parameters', {})
        
        # Create config with defaults
        summarization_config = SummarizationConfig(
            max_chunk_size=summarization_params.get('max_chunk_size', 1000),
            min_summary_length=summarization_params.get('min_summary_length', 50),
            max_summary_length=summarization_params.get('max_summary_length', 150),
            stride=summarization_params.get('stride', 100),
            temperature=summarization_params.get('temperature', 0.7),
            top_p=summarization_params.get('top_p', 0.9),
            max_retries=summarization_params.get('max_retries', 3)
        )

        # Preprocess the text
        preprocessed_text = preprocess_text(email_content, config)
        
        # Split into chunks if necessary
        if len(preprocessed_text) > summarization_config.max_chunk_size:
            logger.debug(
                f"Email content exceeds max_chunk_size ({summarization_config.max_chunk_size}). "
                "Splitting into chunks."
            )
            chunks = split_text(
                preprocessed_text,
                summarization_config.max_chunk_size,
                summarization_config.stride,
                logger
            )
        else:
            chunks = [preprocessed_text]

        summaries = []
        for i, chunk in enumerate(chunks, 1):
            logger.debug(f"Processing chunk {i}/{len(chunks)}")
            
            for attempt in range(summarization_config.max_retries):
                try:
                    summary = summarization_pipeline(
                        chunk,
                        max_length=summarization_config.max_summary_length,
                        min_length=summarization_config.min_summary_length,
                        do_sample=True,
                        temperature=summarization_config.temperature,
                        top_p=summarization_config.top_p,
                    )
                    summaries.append(summary[0]['summary_text'])
                    break
                except Exception as e:
                    if attempt == summarization_config.max_retries - 1:
                        raise SummarizationError(
                            f"Failed to summarize chunk {i} after {summarization_config.max_retries} attempts"
                        ) from e
                    logger.warning(f"Attempt {attempt + 1} failed for chunk {i}. Retrying...")
                    continue

        # Combine chunk summaries
        if len(summaries) > 1:
            # Recursive summarization for multiple chunks
            combined_summary = " ".join(summaries)
            final_summary = summarization_pipeline(
                combined_summary,
                max_length=summarization_config.max_summary_length,
                min_length=summarization_config.min_summary_length,
                do_sample=True,
                temperature=summarization_config.temperature,
                top_p=summarization_config.top_p,
            )[0]['summary_text']
        else:
            final_summary = summaries[0]

        logger.debug(f"Generated summary: {final_summary}")
        return final_summary

    except SummarizationError as se:
        log_error(logger, f"Summarization error: {str(se)}", se)
        raise
    except Exception as e:
        log_error(logger, f"Unexpected error during summarization: {str(e)}", e)
        raise SummarizationError(f"Failed to perform summarization: {str(e)}") from e