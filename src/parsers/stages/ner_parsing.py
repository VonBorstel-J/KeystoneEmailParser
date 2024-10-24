# src\parsers\stages\ner_parsing.py

import logging
from typing import Dict, Any, List
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
import torch

def initialize_ner_pipeline(logger: logging.Logger, config: Dict[str, Any]):
    """
    Initializes the NER pipeline with domain-specific fine-tuning.

    Args:
        logger (logging.Logger): Logger instance.
        config (Dict[str, Any]): Configuration dictionary.

    Returns:
        pipeline: Initialized NER pipeline.
    """
    try:
        logger.debug("Loading NER model and tokenizer.")
        tokenizer = AutoTokenizer.from_pretrained(config['models']['ner']['repo_id'])
        model = AutoModelForTokenClassification.from_pretrained(config['models']['ner']['repo_id'])
        ner_pipeline = pipeline(
            "ner",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy=config['models']['ner'].get('aggregation_strategy', 'simple'),
            device=0 if config['processing']['device'] == 'cuda' and torch.cuda.is_available() else -1
        )
        logger.info("NER pipeline initialized successfully.")
        return ner_pipeline
    except Exception as e:
        logger.error(f"Failed to initialize NER pipeline: {e}", exc_info=True)
        return None

def perform_ner(email_content: str, ner_pipeline) -> Dict[str, Any]:
    """
    Perform Named Entity Recognition on the given email content.

    Args:
        email_content (str): The content of the email.
        ner_pipeline: The initialized NER pipeline.

    Returns:
        Dict[str, Any]: Extracted entities organized by section and field.
    """
    try:
        logging.debug("Starting NER process.")
        entities = ner_pipeline(email_content)
        extracted_entities: Dict[str, Any] = {}
        for entity in entities:
            label = entity.get("entity_group")
            word = entity.get("word").strip()
            score = entity.get("score", 0)
            if label and word and score > 0.85:  # Confidence threshold
                section, field = map_entity_to_field(label, email_content)
                if section and field:
                    extracted_entities.setdefault(section, {}).setdefault(field, []).append(word)
                    logging.debug(f"Extracted {label}: {word} with confidence {score:.2f}")
        return extracted_entities
    except Exception as e:
        logging.error(f"Error during NER processing: {e}", exc_info=True)
        return {}

def map_entity_to_field(label: str, email_content: str) -> (Any, Any):
    """
    Maps a detected entity to a specific section and field in the schema.

    Args:
        label (str): The entity label.
        email_content (str): The content of the email.

    Returns:
        Tuple[Optional[str], Optional[str]]: The section and field names.
    """
    if label == "PER":
        if "insured" in email_content.lower():
            return "Insured Information", "Name"
        elif "adjuster" in email_content.lower():
            return "Adjuster Information", "Adjuster Name"
        elif "handler" in email_content.lower():
            return "Requesting Party", "Handler"
        elif "public adjuster" in email_content.lower():
            return "Insured Information", "Public Adjuster"
    elif label == "ORG":
        if "insurance company" in email_content.lower():
            return "Requesting Party", "Insurance Company"
        elif "claims adjuster" in email_content.lower():
            return "Adjuster Information", "Job Title"
    elif label in ["LOC", "GPE"]:
        if "loss location" in email_content.lower():
            return "Insured Information", "Loss Address"
        elif "address" in email_content.lower():
            return "Adjuster Information", "Address"
    elif label in ["DATE", "EVENT"]:
        if "loss" in email_content.lower():
            return "Assignment Information", "Date of Loss/Occurrence"
        elif "incident" in email_content.lower():
            return "Assignment Information", "Date of Loss/Occurrence"
        elif "damage" in email_content.lower():
            return "Assignment Information", "Cause of loss"
    elif label == "PHONE":
        if "contact number" in email_content.lower():
            return "Insured Information", "Contact #"
        elif "adjuster phone" in email_content.lower():
            return "Adjuster Information", "Adjuster Phone Number"
    elif label == "EMAIL":
        return "Adjuster Information", "Adjuster Email"
    return None, None
