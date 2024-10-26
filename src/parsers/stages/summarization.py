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
    max_chunk_size: int = 1000
    min_summary_length: int = 50
    max_summary_length: int = 150
    stride: int = 100
    temperature: float = 0.7
    top_p: float = 0.9
    max_retries: int = 3
    recursive_summarization: bool = True
    logging_level: str = "DEBUG"

class SummarizationError(Exception):
    pass

def initialize_summarization_pipeline(logger: logging.Logger, config: Dict[str, Any], prompt_template: Optional[str] = None) -> Optional[Any]:
    try:
        logger.info("Initializing Summarization pipeline.")
        summarization_config = config.get("models", {}).get("summarization", {})
        if not summarization_config:
            raise KeyError("'summarization' configuration not found under 'models'")
        model_id = summarization_config.get('repo_id')
        if not isinstance(model_id, str):
            raise ValueError(f"Invalid 'repo_id' for Summarization model: {model_id}")
        device_config = summarization_config.get('device', 'cuda')
        device = 0 if device_config == "cuda" and torch.cuda.is_available() else -1
        summarization_pipeline = pipeline(
            task=summarization_config.get('task', 'text2text-generation'),
            model=model_id,
            tokenizer=model_id,
            device=device
        )
        if prompt_template:
            logger.debug("Using prompt template for summarization: %s", prompt_template)
        logger.info("Summarization pipeline initialized successfully.")
        return summarization_pipeline
    except KeyError as e:
        logger.error("Configuration key error during pipeline initialization: %s", e, exc_info=True)
    except ValueError as e:
        logger.error("Value error during pipeline initialization: %s", e, exc_info=True)
    except ImportError as e:
        logger.error("Import error during pipeline initialization: %s", e, exc_info=True)
    except Exception as e:
        logger.error("Unexpected error during Summarization pipeline initialization: %s", e, exc_info=True)
    return None

def preprocess_text(text: str, config: Dict[str, Any]) -> str:
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
                    overlap_sentences = current_chunk[-stride:] if len(current_chunk) >= stride else current_chunk
                    current_chunk = overlap_sentences + [sentence]
                    current_length = sum(len(s) for s in current_chunk)
                else:
                    split_point = max_length
                    chunks.append(sentence[:split_point])
                    remaining_sentence = sentence[split_point:]
                    current_chunk = [remaining_sentence] if remaining_sentence else []
                    current_length = len(remaining_sentence)
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        logger.debug(f"Split text into {len(chunks)} chunks")
        return chunks
    except Exception as e:
        logger.error(f"Error splitting text: {str(e)}")
        return [text]

def perform_summarization(email_content: str, summarization_pipeline: pipeline, logger: logging.Logger, config: Dict[str, Any]) -> str:
    try:
        logger.setLevel(getattr(logging, config.get('models', {}).get('summarization', {}).get('logging_level', 'DEBUG').upper(), logging.DEBUG))
        logger.debug("Starting summarization process.")
        if not email_content.strip():
            raise ValueError("Empty email content provided")
        summarization_params = config.get('models', {}).get('summarization', {}).get('parameters', {})
        summarization_config = SummarizationConfig(
            max_chunk_size=summarization_params.get('max_chunk_size', 1000),
            min_summary_length=summarization_params.get('min_summary_length', 50),
            max_summary_length=summarization_params.get('max_summary_length', 150),
            stride=summarization_params.get('stride', 100),
            temperature=summarization_params.get('temperature', 0.7),
            top_p=summarization_params.get('top_p', 0.9),
            max_retries=summarization_params.get('max_retries', 3),
            recursive_summarization=summarization_params.get('recursive_summarization', True),
            logging_level=config.get('models', {}).get('summarization', {}).get('logging_level', 'DEBUG')
        )
        preprocessed_text = preprocess_text(email_content, config)
        if len(preprocessed_text) > summarization_config.max_chunk_size:
            logger.debug(f"Email content exceeds max_chunk_size ({summarization_config.max_chunk_size}). Splitting into chunks.")
            chunks = split_text(preprocessed_text, summarization_config.max_chunk_size, summarization_config.stride, logger)
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
                except (KeyError, ImportError) as e:
                    raise SummarizationError(f"Critical error during summarization of chunk {i}: {e}") from e
                except Exception as e:
                    if attempt == summarization_config.max_retries - 1:
                        raise SummarizationError(f"Failed to summarize chunk {i} after {summarization_config.max_retries} attempts") from e
                    logger.warning(f"Attempt {attempt + 1} failed for chunk {i} due to {e}. Retrying...")
        if len(summaries) > 1 and summarization_config.recursive_summarization:
            logger.debug("Performing recursive summarization on combined chunk summaries.")
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
            final_summary = " ".join(summaries)
        logger.debug(f"Generated summary: {final_summary}")
        return final_summary
    except SummarizationError as se:
        log_error(logger, f"Summarization error: {str(se)}", se)
        raise
    except Exception as e:
        log_error(logger, f"Unexpected error during summarization: {str(e)}", e)
        raise SummarizationError(f"Failed to perform summarization: {str(e)}") from e
