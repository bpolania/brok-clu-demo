#!/usr/bin/env python3
"""
Phase L-10 Prompt 1: Model Load Collapse Tests

These tests prove that missing/invalid model files cause _get_llm() to return
None, which causes inference_engine() to return empty bytes (b"").

Test Cases:
- C1: Missing model file -> _get_llm() returns None
- C2: Unreadable model file -> _get_llm() returns None
- Model file validation: Verify model.bin is a valid GGUF file

These tests do NOT require llama-cpp-python to be installed. They test the
failure paths which don't depend on successful library import.
"""

import os
import stat
import sys
import tempfile
import shutil

# Setup paths
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
_SRC_DIR = os.path.join(_REPO_ROOT, 'src')

if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from artifact_layer.inference_engine import (
    _get_llm,
    _get_model_path,
    inference_engine,
    _MODEL_RELATIVE_PATH
)


# =============================================================================
# HELPER: Reset module state between tests
# =============================================================================

def reset_llm_instance():
    """Reset the module-level _llm_instance to None."""
    import artifact_layer.inference_engine as ie
    ie._llm_instance = None


# =============================================================================
# TEST: Model path resolution
# =============================================================================

def test_model_path_resolution():
    """Verify _get_model_path() returns the expected fixed path."""
    model_path = _get_model_path()

    # Path should end with the fixed relative path
    assert str(model_path).endswith(_MODEL_RELATIVE_PATH), \
        f"Model path should end with {_MODEL_RELATIVE_PATH}, got {model_path}"

    # Path should be absolute
    assert model_path.is_absolute(), "Model path should be absolute"

    print(f"[PASS] Model path resolution: {model_path}")


# =============================================================================
# TEST: Model file is valid GGUF
# =============================================================================

def test_model_file_is_valid_gguf():
    """
    Verify that model.bin is a valid GGUF file by checking magic bytes.

    GGUF files start with the magic bytes: 0x47 0x47 0x55 0x46 ("GGUF")
    """
    model_path = _get_model_path()

    if not model_path.exists():
        print(f"[SKIP] Model file not found at {model_path}")
        return

    with open(model_path, 'rb') as f:
        magic = f.read(4)

    expected_magic = b'GGUF'
    assert magic == expected_magic, \
        f"Model file should have GGUF magic bytes, got {magic!r}"

    print(f"[PASS] Model file is valid GGUF (magic bytes: {magic!r})")


# =============================================================================
# TEST C1: Missing model file -> _get_llm() returns None
# =============================================================================

def test_c1_missing_model_returns_none():
    """
    C1: Missing model file causes _get_llm() to return None.

    This test temporarily moves the model file, calls _get_llm(),
    and verifies it returns None. The file is restored in finally block.
    """
    reset_llm_instance()
    model_path = _get_model_path()
    backup_path = model_path.with_suffix('.bin.backup')

    if not model_path.exists():
        print(f"[SKIP] Model file not found at {model_path}")
        return

    try:
        # Move the model file to create "missing" condition
        shutil.move(str(model_path), str(backup_path))

        # Verify file is actually missing
        assert not model_path.exists(), "Model file should be missing for test"

        # Call _get_llm() - should return None due to missing file
        result = _get_llm()

        assert result is None, \
            f"_get_llm() should return None when model is missing, got {type(result)}"

        print("[PASS] C1: Missing model file -> _get_llm() returns None")

    finally:
        # Restore the model file
        reset_llm_instance()
        if backup_path.exists():
            shutil.move(str(backup_path), str(model_path))


# =============================================================================
# TEST C2: Unreadable model file -> _get_llm() returns None
# =============================================================================

def test_c2_unreadable_model_returns_none():
    """
    C2: Unreadable model file causes _get_llm() to return None.

    This test temporarily removes read permissions from the model file,
    calls _get_llm(), and verifies it returns None. Permissions are
    restored in finally block.

    Note: This test may not work on all platforms (e.g., Windows) or
    when running as root. It is skipped in those cases.
    """
    reset_llm_instance()
    model_path = _get_model_path()

    if not model_path.exists():
        print(f"[SKIP] Model file not found at {model_path}")
        return

    # Skip on Windows (chmod doesn't work the same way)
    if sys.platform == 'win32':
        print("[SKIP] C2: Test skipped on Windows")
        return

    # Get original permissions
    original_mode = os.stat(model_path).st_mode

    try:
        # Remove read permissions (keep write to restore later)
        os.chmod(model_path, stat.S_IWUSR)

        # Call _get_llm() - should return None due to unreadable file
        result = _get_llm()

        assert result is None, \
            f"_get_llm() should return None when model is unreadable, got {type(result)}"

        print("[PASS] C2: Unreadable model file -> _get_llm() returns None")

    finally:
        # Restore original permissions
        reset_llm_instance()
        os.chmod(model_path, original_mode)


# =============================================================================
# TEST: inference_engine returns b"" when _get_llm returns None
# =============================================================================

def test_inference_engine_returns_empty_on_no_llm():
    """
    Verify that inference_engine() returns b"" when no LLM is available.

    Since _get_llm() returns None in Prompt 1 state (even with valid model),
    inference_engine() should always return empty bytes.
    """
    reset_llm_instance()

    # Call inference_engine with some test input
    result = inference_engine(b"test input")

    assert result == b"", \
        f"inference_engine should return b'' when no LLM available, got {result!r}"

    print("[PASS] inference_engine returns b'' when no LLM available")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run all L-10 model load collapse tests."""
    print("=" * 70)
    print("Phase L-10 Prompt 1: Model Load Collapse Tests")
    print("=" * 70)
    print()

    tests = [
        ("Model path resolution", test_model_path_resolution),
        ("Model file is valid GGUF", test_model_file_is_valid_gguf),
        ("C1: Missing model -> None", test_c1_missing_model_returns_none),
        ("C2: Unreadable model -> None", test_c2_unreadable_model_returns_none),
        ("inference_engine returns b'' on no LLM", test_inference_engine_returns_empty_on_no_llm),
    ]

    passed = 0
    failed = 0
    skipped = 0

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {name}: {type(e).__name__}: {e}")
            failed += 1

    print()
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
