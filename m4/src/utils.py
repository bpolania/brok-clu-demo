#!/usr/bin/env python3
"""
Phase M-4: Deterministic Utilities

Provides helpers for deterministic observability:
- SHA-256 hashing (bytes only, no interpretation)
- Stable JSON serialization (sorted keys, stable arrays)
- Relative path enforcement (no absolute paths)

All utilities are designed to produce identical outputs for identical inputs.
No timestamps, no machine identifiers, no randomness.
"""

import hashlib
import json
import os
import re
from typing import Any, List, Optional


# Patterns for timestamp detection in strings
# M-3 run directory pattern: run_YYYYMMDDTHHMMSSZ
RUN_DIR_TIMESTAMP_PATTERN = re.compile(r'run_\d{8}T\d{6}Z')
# ISO 8601 datetime pattern embedded in strings
ISO_DATETIME_IN_STRING_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
# Date-like patterns that indicate non-determinism
DATE_PATTERN = re.compile(r'\d{4}[-/]\d{2}[-/]\d{2}')


class PathSafetyError(Exception):
    """Raised when a path violates safety constraints."""
    pass


def sha256_bytes(data: bytes) -> str:
    """
    Compute SHA-256 hash of raw bytes.

    Args:
        data: Raw bytes to hash

    Returns:
        Lowercase hex digest string (64 characters)

    This function ONLY hashes bytes. It does not interpret content.
    """
    return hashlib.sha256(data).hexdigest()


def sha256_file(file_path: str) -> str:
    """
    Compute SHA-256 hash of a file's raw bytes.

    Args:
        file_path: Path to file to hash

    Returns:
        Lowercase hex digest string (64 characters)

    This function ONLY hashes raw file bytes. It does not interpret content.
    """
    with open(file_path, 'rb') as f:
        return sha256_bytes(f.read())


def to_rel_path(repo_root: str, path: str, allow_external: bool = False) -> str:
    """
    Convert a path to repo-relative form with POSIX separators.

    Args:
        repo_root: Repository root directory (absolute path)
        path: Path to convert (may be absolute or relative)
        allow_external: If True, return a marker for external paths instead of raising

    Returns:
        Repo-relative path with forward slashes, or "[external]:<basename>" if
        allow_external is True and path is outside repo

    Raises:
        PathSafetyError: If path is absolute and not under repo_root,
                         or if the result would escape repo_root
                         (only if allow_external is False)
    """
    # Normalize both paths
    repo_root = os.path.abspath(repo_root)
    abs_path = os.path.abspath(path)

    # Check if path is under repo_root
    try:
        rel = os.path.relpath(abs_path, repo_root)
    except ValueError:
        # Different drives on Windows
        if allow_external:
            return f"[external]:{os.path.basename(path)}"
        raise PathSafetyError(f"Path not under repo root: {path}")

    # Reject paths that escape repo root
    if rel.startswith('..'):
        if allow_external:
            return f"[external]:{os.path.basename(path)}"
        raise PathSafetyError(f"Path escapes repo root: {path}")

    # Normalize to POSIX separators
    return rel.replace(os.sep, '/')


def is_absolute_path(path: str) -> bool:
    """Check if a path is absolute (any platform)."""
    if os.path.isabs(path):
        return True
    # Also check for Windows-style paths
    if len(path) >= 2 and path[1] == ':':
        return True
    if path.startswith('\\\\'):
        return True
    return False


def validate_no_absolute_paths(data: Any, path: str = "root") -> List[str]:
    """
    Recursively validate that a data structure contains no absolute paths.

    Args:
        data: Data structure to validate (dict, list, or scalar)
        path: Current path for error reporting

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if isinstance(data, dict):
        for key, value in data.items():
            errors.extend(validate_no_absolute_paths(value, f"{path}.{key}"))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            errors.extend(validate_no_absolute_paths(item, f"{path}[{i}]"))
    elif isinstance(data, str):
        if is_absolute_path(data):
            errors.append(f"Absolute path at {path}: {data}")

    return errors


def validate_no_timestamps(data: Any, path: str = "root") -> List[str]:
    """
    Recursively validate that a data structure contains no timestamp-like values.

    Checks for:
    - Keys that are exactly timestamp indicators (timestamp, created_at, etc.)
    - ISO 8601 date strings (YYYY-MM-DDTHH:MM:SS) anywhere in string values
    - Unix epoch integers (> 1000000000)
    - M-3 run directory patterns (run_YYYYMMDDTHHMMSSZ) embedded in paths

    Args:
        data: Data structure to validate
        path: Current path for error reporting

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    # Only exact matches for timestamp-like keys (not substrings)
    timestamp_keys = {
        'timestamp', 'created_at', 'modified_at', 'updated_at',
        'created_time', 'modified_time', 'start_time', 'end_time',
        'datetime', 'date_time', 'wall_clock', 'epoch'
    }

    if isinstance(data, dict):
        for key, value in data.items():
            key_lower = key.lower()
            # Check for exact timestamp key matches
            if key_lower in timestamp_keys:
                errors.append(f"Timestamp key at {path}: {key}")
            errors.extend(validate_no_timestamps(value, f"{path}.{key}"))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            errors.extend(validate_no_timestamps(item, f"{path}[{i}]"))
    elif isinstance(data, int):
        # Check for epoch-like integers (after year 2001, before 2100)
        if data > 1000000000 and data < 4000000000:
            errors.append(f"Epoch-like integer at {path}: {data}")
    elif isinstance(data, str):
        # Check for M-3 run directory timestamp pattern (run_YYYYMMDDTHHMMSSZ)
        if RUN_DIR_TIMESTAMP_PATTERN.search(data):
            errors.append(f"Run directory timestamp pattern at {path}: {data}")
        # Check for ISO 8601 datetime patterns embedded in strings
        elif ISO_DATETIME_IN_STRING_PATTERN.search(data):
            errors.append(f"ISO datetime pattern in string at {path}: {data}")

    return errors


def stable_json_dumps(data: Any) -> str:
    """
    Serialize data to JSON with stable, deterministic output.

    Properties:
    - Keys are sorted alphabetically at all levels
    - Consistent indentation (2 spaces)
    - Newline at end of file
    - No trailing whitespace
    - UTF-8 encoding assumed

    Args:
        data: Data structure to serialize

    Returns:
        JSON string with stable ordering
    """
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + '\n'


def stable_json_write(file_path: str, data: Any) -> None:
    """
    Write data to a JSON file with stable, deterministic output.

    Args:
        file_path: Path to write to
        data: Data structure to serialize
    """
    content = stable_json_dumps(data)
    with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)


def derive_run_id(
    input_sha: str,
    proposal_sha: Optional[str] = None,
    artifact_sha: Optional[str] = None
) -> str:
    """
    Derive a deterministic M-4 run ID from artifact hashes.

    The run ID is computed as:
        sha256(input_sha + proposal_sha + artifact_sha + "m4")[:16]

    Args:
        input_sha: SHA-256 of input file
        proposal_sha: SHA-256 of proposal_set.json (or empty string)
        artifact_sha: SHA-256 of artifact.json (or empty string)

    Returns:
        Run ID string like "m4_a1b2c3d4e5f67890"
    """
    hasher = hashlib.sha256()
    hasher.update(input_sha.encode('utf-8'))
    hasher.update((proposal_sha or '').encode('utf-8'))
    hasher.update((artifact_sha or '').encode('utf-8'))
    hasher.update(b'm4')
    return f"m4_{hasher.hexdigest()[:16]}"
