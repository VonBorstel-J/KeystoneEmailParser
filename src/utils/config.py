# src/utils/config.py

import os
import logging

class Config:
    """Configuration settings."""

    # ----------------------------
    # Enhanced Parser Configuration
    # ----------------------------
    # Fuzzy Matching Threshold
    FUZZY_THRESHOLD = int(os.getenv('FUZZY_THRESHOLD', '90'))
    
    # Known Values for Fuzzy Matching
    KNOWN_VALUES = {
        "Claim Number": [
            "ABC123",
            "XYZ789",
            "DEF456",
            "GHI101",
            "JKL202",
            # Add more known claim numbers as needed
        ],
        "Insurance Company": [
            "State Farm",
            "Allstate",
            "Geico",
            "Progressive",
            "Nationwide",
            "Liberty Mutual",
            "Farmers",
            "Travelers",
            "American Family",
            "USAA",
            # Add more known insurance companies as needed
        ],
        "Handler": [
            "John Doe",
            "Jane Smith",
            "Emily Davis",
            "Michael Brown",
            "Sarah Johnson",
            "David Wilson",
            # Add more known handlers as needed
        ],
        "Adjuster Name": [
            "Michael Brown",
            "Sarah Johnson",
            "David Wilson",
            "Laura Martinez",
            "James Anderson",
            # Add more known adjuster names as needed
        ],
        # Add other fields and their known values as needed
    }

    # Date Formats for Parsing
    DATE_FORMATS = [
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y-%m-%d',
        '%B %d, %Y',
        '%b %d, %Y',
        '%d %B %Y',
        '%d %b %Y',
        '%Y/%m/%d',
        '%d-%m-%Y',
        '%Y.%m.%d',
        '%d.%m.%Y',
        '%m-%d-%Y',
        '%Y%m%d',
        '%B %-d, %Y',
        '%b %-d, %Y',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%fZ',
    ]

    # Boolean Values
    BOOLEAN_VALUES = {
        "positive": [
            'yes', 'y', 'true', 't', '1', 'x', '[x]', '[X]', '(x)', '(X)',
        ],
        "negative": [
            'no', 'n', 'false', 'f', '0', '[ ]', '()', '[N/A]', '(N/A)',
        ],
    }
    
    # Model Timeouts
    MODEL_TIMEOUTS = {
        'ner': int(os.getenv('NER_TIMEOUT', '30')),
        'donut': int(os.getenv('DONUT_TIMEOUT', '60')),
        'sequence': int(os.getenv('SEQUENCE_TIMEOUT', '45')),
        'validation': int(os.getenv('VALIDATION_TIMEOUT', '30'))
    }
    
    # Model Configurations
    MODEL_CONFIG = {
        'ner': {
            'name': "dslim/bert-base-NER",
            'type': "ner",
            'batch_size': 32
        },
        'donut': {
            'name': "naver-clova-ix/donut-base-finetuned-cord-v2",
            'type': "document",
            'batch_size': 1
        },
        'sequence': {
            'name': "facebook/bart-large-cnn",
            'type': "summarization",
            'batch_size': 8
        },
        'validation': {
            'name': "gpt2",
            'type': "text-generation",
            'batch_size': 4
        }
    }

    # Valid File Extensions for Attachments
    VALID_EXTENSIONS = [
        '.pdf', '.docx', '.xlsx', '.zip', '.png', '.jpg', '.jpeg', '.gif', '.txt', '.csv',
    ]

    # URL Validation Setting
    URL_VALIDATION = {
        "use_external_library": os.getenv('URL_VALIDATION_USE_EXTERNAL_LIBRARY', 'true').lower() in ['true', '1', 'yes']
    }

    # ----------------------------
    # Logging Configuration
    # ----------------------------
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG').upper()  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

    # ----------------------------
    # Load Configuration
    # ----------------------------
    @classmethod
    def load_config(cls) -> dict:
        """
        Load configuration settings.

        Returns:
            dict: Configuration settings.
        """
        logger = logging.getLogger("Config")
        config = {
            "fuzzy_threshold": cls.FUZZY_THRESHOLD,
            "known_values": cls.KNOWN_VALUES,
            "date_formats": cls.DATE_FORMATS,
            "boolean_values": cls.BOOLEAN_VALUES,
            "valid_extensions": cls.VALID_EXTENSIONS,
            "url_validation": cls.URL_VALIDATION,
            "log_level": cls.LOG_LEVEL,
        }
        logger.info("Loaded configuration from Config class variables.")
        return config
