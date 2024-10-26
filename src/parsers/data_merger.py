from typing import Any, Dict, List, Optional, Set
import logging
from dataclasses import dataclass
from copy import deepcopy

from src.utils.quickbase_schema import QUICKBASE_SCHEMA


@dataclass
class MergeChange:
    """
    Represents a change made during the data merging process.
    """
    section: str
    field: Optional[str]
    old_value: Any
    new_value: Any
    change_type: str

    def __str__(self) -> str:
        if self.field:
            return f"{self.change_type.title()}: {self.section}.{self.field}: {self.old_value} -> {self.new_value}"
        return f"{self.change_type.title()}: {self.section}: {self.old_value} -> {self.new_value}"

class DataMerger:
    """
    Handles merging of parsed data into the original data structure.
    Keeps track of all changes made during the merge.
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.changes: List[MergeChange] = []
        self._seen_values: Set[str] = set()

    @staticmethod
    def ensure_list(value: Any) -> List[Any]:
        """
        Ensures that the input value is a list.

        Args:
            value (Any): The value to ensure as a list.

        Returns:
            List[Any]: The value as a list.
        """
        if value is None:
            return ["N/A"]
        if isinstance(value, list):
            return value
        if isinstance(value, (dict, set)):
            return [value]
        return [value]

    def merge_field_values(
        self, existing: Any, new: Any, field_config: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Merges existing and new values based on field configuration.

        Args:
            existing (Any): The existing value(s).
            new (Any): The new value(s) to merge.
            field_config (Optional[Dict[str, Any]]): Configuration dict for the field.

        Returns:
            List[Any]: The merged list of values.
        """
        existing_list = self.ensure_list(existing)
        new_list = self.ensure_list(new)
        if field_config:
            field_type = field_config.get("type")
            if field_type == "boolean":
                return [bool(new_list[-1])]
            elif field_type == "date":
                return self._format_dates(new_list)
            elif field_type == "email":
                return [email.lower().strip() for email in new_list if email != "N/A"]
        if any(v != "N/A" for v in new_list):
            existing_list = [v for v in existing_list if v != "N/A"]
        self._seen_values.clear()
        merged = []
        for item in existing_list + new_list:
            if item != "N/A":
                item_str = str(item)
                if item_str not in self._seen_values:
                    self._seen_values.add(item_str)
                    merged.append(item)
        return merged if merged else ["N/A"]

    def _format_dates(self, dates: List[str]) -> List[str]:
        """
        Formats a list of date strings to 'YYYY-MM-DD'.

        Args:
            dates (List[str]): List of date strings.

        Returns:
            List[str]: List of formatted date strings.
        """
        from datetime import datetime

        formatted = []
        for date in dates:
            try:
                if date != "N/A":
                    dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
                    formatted.append(dt.strftime("%Y-%m-%d"))
            except ValueError:
                self.logger.warning(f"Invalid date format: {date}")
        return formatted if formatted else ["N/A"]

    def merge_parsed_data(
        self, original_data: Dict[str, Any], new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merges new parsed data into the original data structure.

        Args:
            original_data (Dict[str, Any]): The original data.
            new_data (Dict[str, Any]): The new parsed data to merge.

        Returns:
            Dict[str, Any]: The merged data.
        """
        try:
            if not isinstance(original_data, dict):
                raise ValueError(
                    f"original_data must be dict, got {type(original_data)}"
                )
            if not isinstance(new_data, dict):
                raise ValueError(f"new_data must be dict, got {type(new_data)}")
            result = deepcopy(original_data)
            for section, fields in new_data.items():
                try:
                    schema_config = QUICKBASE_SCHEMA.get(section, {})
                    if section in QUICKBASE_SCHEMA:
                        if section not in result:
                            result[section] = {}
                            self.changes.append(
                                MergeChange(
                                    section=section,
                                    field=None,
                                    old_value=None,
                                    new_value={},
                                    change_type="create",
                                )
                            )
                        if isinstance(fields, dict):
                            for field, value in fields.items():
                                field_config = schema_config.get(field, {})
                                old_value = result[section].get(field, ["N/A"])
                                new_value = self.merge_field_values(
                                    old_value, value, field_config
                                )
                                if old_value != new_value:
                                    result[section][field] = new_value
                                    self.changes.append(
                                        MergeChange(
                                            section=section,
                                            field=field,
                                            old_value=old_value,
                                            new_value=new_value,
                                            change_type="update",
                                        )
                                    )
                        elif isinstance(fields, list):
                            old_value = result.get(section, [])
                            new_value = self.merge_field_values(old_value, fields)
                            if old_value != new_value:
                                result[section] = new_value
                                self.changes.append(
                                    MergeChange(
                                        section=section,
                                        field=None,
                                        old_value=old_value,
                                        new_value=new_value,
                                        change_type="update",
                                    )
                                )
                        else:
                            old_value = result.get(section)
                            result[section] = fields
                            self.changes.append(
                                MergeChange(
                                    section=section,
                                    field=None,
                                    old_value=old_value,
                                    new_value=fields,
                                    change_type="update",
                                )
                            )
                    else:
                        self.logger.debug(f"Handling non-schema section: {section}")
                        if isinstance(fields, list):
                            if section not in result:
                                result[section] = []
                                self.changes.append(
                                    MergeChange(
                                        section=section,
                                        field=None,
                                        old_value=None,
                                        new_value=[],
                                        change_type="create",
                                    )
                                )
                            old_value = result[section]
                            new_items = [x for x in fields if x not in result[section]]
                            result[section].extend(new_items)
                            if new_items:
                                self.changes.append(
                                    MergeChange(
                                        section=section,
                                        field=None,
                                        old_value=old_value,
                                        new_value=result[section],
                                        change_type="update",
                                    )
                                )
                        else:
                            old_value = result.get(section)
                            result[section] = fields
                            self.changes.append(
                                MergeChange(
                                    section=section,
                                    field=None,
                                    old_value=old_value,
                                    new_value=fields,
                                    change_type="update",
                                )
                            )
                except Exception as section_error:
                    self.logger.error(
                        f"Error processing section '{section}': {str(section_error)}",
                        exc_info=True,
                    )
                    continue
            if self.changes:
                self.logger.debug(
                    "Merge changes:\n" + "\n".join(f"- {change}" for change in self.changes)
                )
            self._validate_merged_data(result)
            return result
        except ValueError as ve:
            self.logger.error(f"Invalid input data: {str(ve)}")
            raise
        except Exception as e:
            self.logger.error(f"Error in merge_parsed_data: {str(e)}", exc_info=True)
            return original_data

    def _validate_merged_data(self, data: Dict[str, Any]) -> None:
        """
        Validates the merged data against the required schema.

        Args:
            data (Dict[str, Any]): The merged data to validate.

        Raises:
            ValueError: If validation fails.
        """
        required_sections = {
            "Requesting Party": {
                "Insurance Company": list,
                "Handler": list,
                "Carrier Claim Number": list,
            },
            "Insured Information": {
                "Name": list,
                "Contact #": list,
                "Loss Address": list,
                "Public Adjuster": list,
                "Is the insured an Owner or a Tenant of the loss location?": list,
            },
            "Adjuster Information": {
                "Adjuster Name": list,
                "Adjuster Phone Number": list,
                "Adjuster Email": list,
                "Job Title": list,
                "Address": list,
                "Policy #": list,
            },
            "Assignment Information": {
                "Date of Loss/Occurrence": list,
                "Cause of loss": list,
                "Facts of Loss": list,
                "Loss Description": list,
                "Residence Occupied During Loss": list,
                "Was Someone home at time of damage": list,
                "Repair or Mitigation Progress": list,
                "Type": list,
                "Inspection type": list,
            },
            "Assignment Type": {
                "Wind": list,
                "Structural": list,
                "Hail": list,
                "Foundation": list,
                "Other": list,
            },
        }
        try:
            for section, fields in required_sections.items():
                if section not in data:
                    self.logger.warning(f"Missing required section: {section}")
                    data[section] = {}
                for field, field_type in fields.items():
                    if field not in data[section]:
                        if field_type == list:
                            data[section][field] = ["N/A"]
                        else:
                            data[section][field] = "N/A"
                    if field_type == list and not isinstance(
                        data[section][field], list
                    ):
                        data[section][field] = [data[section][field]]
            if "Assignment Type" in data and "Other" in data["Assignment Type"]:
                other_data = data["Assignment Type"]["Other"]
                if isinstance(other_data, list) and other_data:
                    if isinstance(other_data[0], dict):
                        if not all(
                            key in other_data[0] for key in ["Checked", "Details"]
                        ):
                            self.logger.warning(
                                "Invalid Other field format in Assignment Type"
                            )
                            data["Assignment Type"]["Other"] = [
                                {"Checked": False, "Details": "N/A"}
                            ]
                    else:
                        data["Assignment Type"]["Other"] = [
                            {"Checked": False, "Details": "N/A"}
                        ]
            for section in [
                "Entities",
                "TransformerEntities",
                "Additional details/Special Instructions",
                "Attachment(s)",
            ]:
                if section not in data:
                    data[section] = {} if section != "Attachment(s)" else []
            self.logger.debug("Data validation completed successfully")
        except Exception as e:
            self.logger.error(f"Error during data validation: {str(e)}", exc_info=True)
            raise ValueError(f"Data validation failed: {str(e)}")
