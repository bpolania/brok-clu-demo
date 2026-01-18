#!/usr/bin/env python3
"""
Guardrail Script: Verify ./brok Unchanged

This script verifies that ./brok has not been modified from its known-good state.
It is used as a guardrail to ensure L-5 and future phases do not accidentally
modify the canonical CLI entrypoint.

Verification checks:
  1. SHA-256 hash matches expected value (from proofs/brok_hash.txt or embedded)
  2. git diff shows no changes to ./brok
  3. git status shows ./brok is not modified

Usage:
    python3 scripts/verify_brok_unchanged.py

Exit codes:
    0 - All checks pass (./brok is unchanged)
    1 - One or more checks failed (./brok has been modified)
    2 - ./brok file not found
"""

import hashlib
import os
import subprocess
import sys

# Resolve paths
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
_BROK_PATH = os.path.join(_REPO_ROOT, "brok")
_HASH_FILE = os.path.join(_REPO_ROOT, "proofs", "brok_hash.txt")

# Known-good SHA-256 hash of ./brok at L-4 closure (fallback if hash file missing)
BROK_EXPECTED_SHA256 = "1dc5ddfd2cd95f2b7c9836bd17014f2713e4aae1fead556144fd74ec4b996944"


def sha256_file(path: str) -> str:
    """Compute SHA-256 hex digest of a file."""
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_expected_hash() -> tuple[str, str]:
    """Load expected hash from hash file or use embedded constant.

    Returns (hash, source) tuple.
    """
    if os.path.isfile(_HASH_FILE):
        with open(_HASH_FILE, 'r') as f:
            content = f.read().strip()
            # Extract hash (first 64 hex chars)
            for line in content.split('\n'):
                line = line.strip()
                if len(line) >= 64 and all(c in '0123456789abcdef' for c in line[:64]):
                    return line[:64], f"proofs/brok_hash.txt"
    return BROK_EXPECTED_SHA256, "embedded constant"


def check_git_diff() -> tuple[bool, str]:
    """Check if git diff shows changes to ./brok.

    Returns (passed, message) tuple.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--quiet", "brok"],
            cwd=_REPO_ROOT,
            capture_output=True
        )
        if result.returncode == 0:
            return True, "git diff clean"
        else:
            return False, "git diff shows modifications"
    except FileNotFoundError:
        return True, "git not available (skipped)"


def check_git_status() -> tuple[bool, str]:
    """Check if git status shows ./brok as modified.

    Returns (passed, message) tuple.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "brok"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True
        )
        output = result.stdout.strip()
        if not output:
            return True, "git status clean"
        elif output.startswith("M ") or output.startswith(" M"):
            return False, f"git status shows modified: {output}"
        else:
            return True, f"git status: {output}"
    except FileNotFoundError:
        return True, "git not available (skipped)"


def main():
    print("=" * 60)
    print("Guardrail: Verify ./brok Unchanged")
    print("=" * 60)
    print()

    # Check file exists
    if not os.path.isfile(_BROK_PATH):
        print(f"ERROR: ./brok not found at {_BROK_PATH}")
        return 2

    all_passed = True

    # Check 1: SHA-256 hash
    print("--- Check 1: SHA-256 Hash ---")
    expected_hash, hash_source = load_expected_hash()
    actual_hash = sha256_file(_BROK_PATH)

    print(f"Expected: {expected_hash}")
    print(f"Source:   {hash_source}")
    print(f"Actual:   {actual_hash}")

    if actual_hash == expected_hash:
        print("[PASS] Hash matches")
    else:
        print("[FAIL] Hash mismatch")
        all_passed = False
    print()

    # Check 2: git diff
    print("--- Check 2: git diff ---")
    diff_passed, diff_msg = check_git_diff()
    print(f"Result: {diff_msg}")
    if diff_passed:
        print("[PASS] No uncommitted changes")
    else:
        print("[FAIL] Uncommitted changes detected")
        all_passed = False
    print()

    # Check 3: git status
    print("--- Check 3: git status ---")
    status_passed, status_msg = check_git_status()
    print(f"Result: {status_msg}")
    if status_passed:
        print("[PASS] Not marked as modified")
    else:
        print("[FAIL] Marked as modified")
        all_passed = False
    print()

    # Summary
    print("=" * 60)
    if all_passed:
        print("[PASS] ./brok is UNCHANGED")
        print()
        print("All guardrail checks passed.")
        print("The canonical CLI entrypoint has not been modified.")
        print("Authority invariants are preserved.")
        return 0
    else:
        print("[FAIL] ./brok has been MODIFIED!")
        print()
        print("One or more guardrail checks failed.")
        print("This violates L-5 constraints:")
        print("  - Do NOT modify ./brok in any way")
        print("  - Canonical invocation must remain: ./brok --input <file>")
        print()
        print("Please revert changes to ./brok before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
