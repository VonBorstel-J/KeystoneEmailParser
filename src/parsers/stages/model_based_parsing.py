from transformers import pipeline
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

class ParsingError(Exception):
    pass

def initialize_model_parser(logger: logging.Logger, config: Dict[str, Any], prompt_template: Optional[str] = None) -> Any:
    """
    Initializes the model-based parser using a pre-trained transformer model.

    Args:
        logger (logging.Logger): Logger instance for logging information.
        config (Dict[str, Any]): Configuration dictionary.
        prompt_template (Optional[str]): Prompt template for the model.

    Returns:
        Any: Initialized model parser.
    """
    try:
        model_name = config.get("model_based_parsing", {}).get("repo_id", "dslim/bert-base-NER")
        logger.info(f"Initializing Model-Based Parser with model: {model_name}")

        model_parser = pipeline("text-generation", model=model_name, tokenizer=model_name)

        # Log and use the prompt template if available
        if prompt_template:
            logger.debug(f"Using prompt template: {prompt_template}")
        
        logger.info("Model-Based Parser initialized successfully.")
        return model_parser
    except Exception as e:
        logger.error(f"Failed to initialize Model-Based Parser: {e}")
        raise ParsingError(f"Failed to initialize Model-Based Parser: {e}")
    
def perform_model_based_parsing(prompt: str, model_parser: Any, logger: logging.Logger) -> Dict[str, Any]:
    """
    Executes model-based parsing using the configured prompt template.

    Args:
        prompt (str): The rendered prompt template with data points
        model_parser: The initialized model parser
        logger: Logger instance

    Returns:
        Dict[str, Any]: Parsed data structure
    """
    try:
        logger.debug("Executing model-based parsing with prompt")
        
        # Use the prompt with the model_parser
        result = model_parser(prompt, max_length=1024, do_sample=True)

        structured_data = extract_structured_data(result)

        # Add metadata for tracking
        parsed_data = {
            "raw_result": result,
            "structured_data": structured_data,
            "metadata": {
                "model_name": model_parser.model.config.name_or_path,
                "parsing_timestamp": datetime.now().isoformat(),
                "confidence_scores": {
                    section: calculate_section_confidence(entities)
                    for section, entities in structured_data.items()
                }
            }
        }
        
        logger.debug(f"Model parsing complete: {len(structured_data)} sections extracted")
        return parsed_data
    except Exception as e:
        logger.error(f"Model parsing failed: {e}", exc_info=True)
        raise ParsingError(f"Model parsing failed: {e}")

def calculate_section_confidence(entities: List[Dict[str, Any]]) -> float:
    """Calculate average confidence score for a section's entities."""
    if not entities:
        return 0.0
    scores = [e.get('confidence', 0.0) for e in entities]
    return sum(scores) / len(scores)

def extract_structured_data(result: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convert model output to structured data format."""
    structured_data = {}
    
    for entity in result:
        label = entity['entity_group']
        value = entity['word']
        confidence = entity['score']
        section = map_label_to_section(label)
        
        if section:
            if section not in structured_data:
                structured_data[section] = []
            
            structured_data[section].append({
                'value': value,
                'confidence': confidence,
                'original_label': label
            })
    
    return structured_data

def map_label_to_section(label: str) -> Optional[str]:
    """Map NER labels to config sections."""
    mapping = {
        'ORG': 'Requesting_Party.Insurance_Company',
        'PER': 'Adjuster_Information.Adjuster_Name',
        'DATE': 'Assignment_Information.Date_of_Loss',
        'LOC': 'Insured_Information.Loss_Address',
        'PHONE': 'Adjuster_Information.Adjuster_Phone_Number',
        'EMAIL': 'Adjuster_Information.Adjuster_Email',
        'MISC': 'Additional_Details',
        'LAW': 'Legal_Information.Case_Details',
        'EVENT': 'Assignment_Information.Event_Type',
        'HANDLER': 'Requesting_Party.Handler',
        'CLAIM_NUMBER': 'Requesting_Party.Carrier_Claim_Number',
        'INSURED_NAME': 'Insured_Information.Name',
        'CONTACT_NUMBER': 'Insured_Information.Contact_Number',
        'PUBLIC_ADJUSTER': 'Insured_Information.Public_Adjuster',
        'OWNERSHIP_STATUS': 'Insured_Information.Is_the_insured_an_Owner_or_a_Tenant_of_the_loss_location',
        'JOB_TITLE': 'Adjuster_Information.Job_Title',
        'ADDRESS': 'Adjuster_Information.Address',
        'POLICY_NUMBER': 'Adjuster_Information.Policy_Number',
        'CAUSE_OF_LOSS': 'Assignment_Information.Cause_of_Loss',
        'FACTS_OF_LOSS': 'Assignment_Information.Facts_of_Loss',
        'LOSS_DESCRIPTION': 'Assignment_Information.Loss_Description',
        'RESIDENCE_OCCUPIED': 'Assignment_Information.Residence_Occupied_During_Loss',
        'SOMEONE_HOME': 'Assignment_Information.Was_Someone_home_at_time_of_damage',
        'REPAIR_PROGRESS': 'Assignment_Information.Repair_or_Mitigation_Progress',
        'TYPE': 'Assignment_Information.Type',
        'INSPECTION_TYPE': 'Assignment_Information.Inspection_type',
        'WIND': 'Assignment_Type.Wind',
        'STRUCTURAL': 'Assignment_Type.Structural',
        'HAIL': 'Assignment_Type.Hail',
        'FOUNDATION': 'Assignment_Type.Foundation',
        'OTHER_DETAILS': 'Assignment_Type.Other.Details'
    }
    return mapping.get(label)
