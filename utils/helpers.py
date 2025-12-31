import json
import os
from typing import List, Dict, Any


def load_json(file_path: str) -> List[Dict[str, Any]]:
    """
    Safely load and validate a JSON file.

    Handles:
    - File not found
    - Empty file
    - Corrupted JSON
    - Incorrect top-level structure
    - Non-dictionary records

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        List[Dict[str, Any]]: Validated list of records.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file is empty, corrupted, or invalid format.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    if os.path.getsize(file_path) == 0:
        raise ValueError(f"JSON file is empty: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

    except json.JSONDecodeError as e:
        raise ValueError(
            f"JSON file is corrupted or improperly formatted: {file_path}"
        ) from e

    # Top-level structure check
    if not isinstance(data, list):
        raise ValueError(
            f"Invalid JSON structure in {file_path}. Expected a list of objects."
        )

    # Ensure all records are dictionaries
    for index, record in enumerate(data):
        if not isinstance(record, dict):
            raise ValueError(
                f"Invalid record format at index {index} in {file_path}. "
                f"Expected JSON object, got {type(record).__name__}."
            )

    return data


def validate_fields(
    records: List[Dict[str, Any]],
    required_fields: List[str]
) -> None:
    """
    Validate presence of required fields in each record.

    Args:
        records (List[Dict]): Loaded JSON records.
        required_fields (List[str]): Required field names.

    Raises:
        ValueError: If records are empty or fields are missing.
    """
    if not records:
        raise ValueError("Dataset is empty after loading.")

    for index, record in enumerate(records):
        for field in required_fields:
            if field not in record:
                raise ValueError(
                    f"Missing required field '{field}' in record {index}"
                )


def filter_by_key(
    records: List[Dict[str, Any]],
    key: str,
    value: Any
) -> List[Dict[str, Any]]:
    """
    Filter records by matching a specific key-value pair.

    Handles:
    - Missing keys
    - Empty input list

    Args:
        records (List[Dict]): Input records.
        key (str): Key to filter by.
        value (Any): Value to match.

    Returns:
        List[Dict]: Filtered records (may be empty).
    """
    if not records:
        return []

    return [
        record for record in records
        if key in record and record[key] == value
    ]
