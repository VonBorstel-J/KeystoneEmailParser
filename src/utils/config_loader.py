import os
import yaml
import logging

class ConfigLoader:
    @staticmethod
    def load_config():
        logger = logging.getLogger("ConfigLoader")
        try:
            # Construct the path to the parser_config.yaml file
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(
                project_root,
                "config",
                "parser_config.yaml"
            )
            logger.debug(f"Loading configuration from {config_path}")
            with open(config_path, "r") as file:
                config = yaml.safe_load(file)
            logger.info("Configuration loaded successfully.")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}", exc_info=True)
            raise
