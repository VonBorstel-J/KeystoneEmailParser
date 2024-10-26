# src/utils/schema_validator.py

from typing import Any, Dict, List
from jsonschema import Draft7Validator, validators, ValidationError as JSONSchemaValidationError
import logging

from src.utils.exceptions import ValidationError, ConfigurationErrorFactory, DependencyError
from src.utils.exceptions import ErrorAggregator, ErrorReporter


logger = logging.getLogger("SchemaValidator")
logger.setLevel(logging.DEBUG)


def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property_name, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(property_name, subschema["default"])

        for error in validate_properties(
            validator,
            properties,
            instance,
            schema,
        ):
            yield error

    return validators.extend(
        validator_class,
        {"properties": set_defaults},
    )


DefaultValidatingDraft7Validator = extend_with_default(Draft7Validator)


class SchemaValidator:
    """Validates configuration against a predefined schema."""

    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
        self.validator = DefaultValidatingDraft7Validator(self.schema)
        self.custom_validators = {}
        self.setup_custom_validations()

    def setup_custom_validations(self):
        """Setup custom validation rules."""
        # Example: occupancy consistency
        self.custom_validators['occupancy_consistency'] = self.validate_occupancy_consistency
        # Add other custom validators as needed

    def validate(self, config: Dict[str, Any]) -> None:
        """Validates the given configuration against the schema and custom rules."""
        errors = sorted(self.validator.iter_errors(config), key=lambda e: e.path)
        aggregator = ErrorAggregator()

        for error in errors:
            path = ".".join([str(elem) for elem in error.path])
            message = f"{path}: {error.message}" if path else error.message
            category = self.get_error_category(error)
            error_obj = ConfigurationErrorFactory.create_validation_error(message, {"path": path, "schema_rule": error.validator})
            error_obj.category = category
            aggregator.add_error(error_obj)
            logger.warning(f"Schema validation issue: {message}")

        # Execute custom validators
        for validator in self.custom_validators.values():
            try:
                validator(config, aggregator)
            except ConfigurationErrorFactory as e:
                aggregator.add_error(e)

        if aggregator.has_errors():
            raise aggregator

        logger.debug("Schema validation completed successfully.")

    def get_error_category(self, error: JSONSchemaValidationError) -> str:
        """Maps JSON Schema validation errors to predefined categories."""
        mapping = {
            "required": "MISSING_REQUIRED",
            "type": "TYPE_MISMATCH",
            "pattern": "INVALID_FORMAT",
            "format": "INVALID_FORMAT",
            "minimum": "VALUE_RANGE",
            "maximum": "VALUE_RANGE",
            # Add more mappings as needed
        }
        return mapping.get(error.validator, "UNKNOWN_ERROR")

    def validate_occupancy_consistency(self, config: Dict[str, Any], aggregator: 'ErrorAggregator') -> None:
        """Validates consistency between occupancy fields."""
        assignment_info = config.get("Assignment Information", {})
        residence_occupied = assignment_info.get("Residence Occupied During Loss", [])
        someone_home = assignment_info.get("Was Someone home at time of damage", [])

        if isinstance(residence_occupied, list):
            residence_occupied_value = residence_occupied[0] if residence_occupied else None
        else:
            residence_occupied_value = residence_occupied

        if isinstance(someone_home, list):
            someone_home_value = someone_home[0] if someone_home else None
        else:
            someone_home_value = someone_home

        if residence_occupied_value is False and someone_home_value is True:
            message = (
                "Inconsistent occupancy status: 'Residence Occupied During Loss' is False, "
                "'Was Someone home at time of damage' is True."
            )
            error_obj = ConfigurationErrorFactory.create_dependency_error(message, {
                "field1": "Residence Occupied During Loss",
                "value1": residence_occupied_value,
                "field2": "Was Someone home at time of damage",
                "value2": someone_home_value,
            })
            aggregator.add_error(error_obj)
            logger.warning(message)
