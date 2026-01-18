#!/usr/bin/env python3
"""
Phase L-2 Prohibition Checks

Verifies that prohibited patterns do not exist in the L-2 implementation.
Extends L-1 prohibition checks with L-2 specific requirements.

Prohibitions checked:
1. No new CLI flags beyond --input
2. No environment variable configuration hooks for engine selection
3. acquire_proposal_set is called exactly once (no retries)
4. No retry loops in LLM engine
5. No scoring/ranking/confidence keywords
6. No ACCEPT fixtures
"""

import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BROK_CLI_PATH = os.path.join(REPO_ROOT, 'brok')

# Directories to exclude from scans
EXCLUDED_DIRS = {
    '.git',
    'artifacts',
    '__pycache__',
    '.venv',
    'venv',
    '.idea',
    'node_modules',
    '.mypy_cache',
    '.pytest_cache',
    'docs/migration/evidence',
    'tests/l1',
    'tests/l2',
}


def _should_skip_path(path: str) -> bool:
    """Check if path should be skipped based on exclusion rules."""
    rel_path = os.path.relpath(path, REPO_ROOT)
    rel_path_normalized = rel_path.replace(os.sep, '/')
    parts = rel_path.split(os.sep)
    for part in parts:
        if part in EXCLUDED_DIRS:
            return True
    for excluded in ['docs/migration/evidence', 'tests/l1', 'tests/l2']:
        if excluded in rel_path_normalized:
            return True
    return False


def _scan_repo_for_patterns(patterns: list, file_ext: str = '.py') -> tuple:
    """Scan repo for prohibited patterns."""
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        if _should_skip_path(root):
            continue

        for fname in files:
            if not fname.endswith(file_ext):
                continue
            fpath = os.path.join(root, fname)

            if _should_skip_path(fpath):
                continue

            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
            except Exception:
                continue

            for pattern in patterns:
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        rel_path = os.path.relpath(fpath, REPO_ROOT)
                        snippet = line.strip()[:60]
                        return False, f"Found '{pattern}' at {rel_path}:{line_num}: {snippet}"

    return True, "No prohibited patterns found"


def check_no_new_cli_flags():
    """Check that no new CLI flags exist beyond --input."""
    allowed_flags = {'--input', '-h', '--help'}

    result = subprocess.run(
        [sys.executable, BROK_CLI_PATH, '--help'],
        capture_output=True,
        text=True
    )

    found_flags = set(re.findall(r'(--[a-z-]+|-[a-z])', result.stdout + result.stderr))
    new_flags = found_flags - allowed_flags

    if new_flags:
        return False, f"Found new CLI flags: {new_flags}"

    return True, "No new CLI flags found"


def check_no_env_config_in_engine_selection():
    """
    Check that engine selection does not use environment variables
    for configuration (API keys for auth are allowed).
    """
    # Check engine_binding.py for env-based selection
    engine_binding = os.path.join(REPO_ROOT, 'src', 'artifact_layer', 'engine_binding.py')

    if not os.path.isfile(engine_binding):
        return False, "engine_binding.py not found"

    with open(engine_binding, 'r', encoding='utf-8') as f:
        content = f.read()

    # Prohibited: using env vars to SELECT which engine to use
    if re.search(r'os\.environ\.get\(["\'].*ENGINE', content, re.IGNORECASE):
        return False, "Found environment variable controlling engine selection"

    if re.search(r'os\.getenv\(["\'].*ENGINE', content, re.IGNORECASE):
        return False, "Found environment variable controlling engine selection"

    # Check for conditional engine selection based on env
    if re.search(r'if.*os\.environ', content):
        # Allow API key checks for auth, but not engine selection
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'if' in line and 'os.environ' in line:
                # Check if this is in context of engine selection
                context = '\n'.join(lines[max(0, i-5):i+5])
                if 'BOUND_ENGINE_NAME' in context or 'engine' in context.lower():
                    if 'API_KEY' not in line:
                        return False, f"Env-based engine selection at line {i+1}"

    return True, "No environment-based engine selection"


def check_single_seam_call():
    """
    Check that acquire_proposal_set is called exactly once per run.
    This verifies no retry loops exist around the seam call.
    """
    orchestrator = os.path.join(REPO_ROOT, 'm3', 'src', 'orchestrator.py')

    if not os.path.isfile(orchestrator):
        return False, "orchestrator.py not found"

    with open(orchestrator, 'r', encoding='utf-8') as f:
        content = f.read()

    # Count calls to acquire_proposal_set
    calls = re.findall(r'acquire_proposal_set\s*\(', content)

    if len(calls) == 0:
        return False, "acquire_proposal_set not called in orchestrator"

    if len(calls) > 1:
        return False, f"acquire_proposal_set called {len(calls)} times (expected 1)"

    # Check for retry patterns around the call
    retry_patterns = [
        r'while.*acquire_proposal_set',
        r'for.*in.*range.*acquire_proposal_set',
        r'retry.*acquire_proposal_set',
    ]

    for pattern in retry_patterns:
        if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
            return False, f"Found retry pattern: {pattern}"

    return True, "acquire_proposal_set called exactly once, no retries"


def check_no_retries_in_llm_engine():
    """Check that LLM engine has no retry/backoff logic."""
    llm_engine = os.path.join(REPO_ROOT, 'src', 'artifact_layer', 'llm_engine.py')

    if not os.path.isfile(llm_engine):
        return False, "llm_engine.py not found"

    with open(llm_engine, 'r', encoding='utf-8') as f:
        content = f.read()

    retry_patterns = [
        r'\bretry\s*\(',
        r'\bmax_attempts\b',
        r'\bbackoff\b',
        r'\btry_again\b',
        r'\battempt\s*\+=\s*1',
        r'while.*attempt.*<',
        r'for.*attempt.*in.*range',
        r'tenacity',
        r'retrying',
    ]

    for pattern in retry_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False, f"Found retry pattern in LLM engine: {pattern}"

    return True, "No retry/backoff patterns in LLM engine"


def check_no_env_vars_in_llm_engine():
    """Check that LLM engine does not use environment variables."""
    llm_engine = os.path.join(REPO_ROOT, 'src', 'artifact_layer', 'llm_engine.py')

    if not os.path.isfile(llm_engine):
        return False, "llm_engine.py not found"

    with open(llm_engine, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for any env var access
    env_patterns = [
        r'os\.environ',
        r'os\.getenv',
        r'getenv\s*\(',
    ]

    for pattern in env_patterns:
        if re.search(pattern, content):
            return False, f"Found env var access in LLM engine: {pattern}"

    return True, "No environment variables in LLM engine"


def check_no_network_in_llm_engine():
    """Check that LLM engine does not make network calls."""
    llm_engine = os.path.join(REPO_ROOT, 'src', 'artifact_layer', 'llm_engine.py')

    if not os.path.isfile(llm_engine):
        return False, "llm_engine.py not found"

    with open(llm_engine, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for network-related imports/calls
    network_patterns = [
        r'import requests',
        r'import httpx',
        r'import urllib',
        r'import http\.client',
        r'import anthropic',
        r'import openai',
        r'\.get\s*\(\s*["\']http',
        r'\.post\s*\(\s*["\']http',
    ]

    for pattern in network_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False, f"Found network pattern in LLM engine: {pattern}"

    return True, "No network calls in LLM engine"


def check_no_scoring_ranking():
    """Check that no scoring/ranking keywords exist in runtime paths."""
    prohibited_patterns = [
        r'\bscore\s*=',
        r'\bscoring\s*\(',
        r'\brank\s*=',
        r'\branking\s*\(',
        r'\bconfidence\s*[=<>]',
        r'\bthreshold\s*=',
        r'\.score\b',
        r'\.rank\b',
        r'\.confidence\b',
    ]
    return _scan_repo_for_patterns(prohibited_patterns)


def check_no_accept_fixtures():
    """Check that no ACCEPT fixtures exist repo-wide."""
    prohibited_patterns = [
        r'accept_fixture',
        r'ACCEPT_FIXTURE',
        r'mock.*accept.*proposal',
        r'fake.*accept.*proposal',
        r'stub.*accept.*proposal',
    ]
    return _scan_repo_for_patterns(prohibited_patterns)


def main():
    """Run all L-2 prohibition checks."""
    checks = [
        ("No new CLI flags", check_no_new_cli_flags),
        ("No env-based engine selection", check_no_env_config_in_engine_selection),
        ("Single seam call (no retries)", check_single_seam_call),
        ("No retries in LLM engine", check_no_retries_in_llm_engine),
        ("No env vars in LLM engine", check_no_env_vars_in_llm_engine),
        ("No network in LLM engine", check_no_network_in_llm_engine),
        ("No scoring/ranking", check_no_scoring_ranking),
        ("No ACCEPT fixtures", check_no_accept_fixtures),
    ]

    all_passed = True
    results = []

    for name, check_fn in checks:
        passed, message = check_fn()
        status = "PASS" if passed else "FAIL"
        results.append((name, status, message))
        if not passed:
            all_passed = False

    print("=" * 70)
    print("Phase L-2 Prohibition Checks")
    print("=" * 70)

    for name, status, message in results:
        print(f"[{status}] {name}")
        print(f"       {message}")

    print("=" * 70)
    if all_passed:
        print("All L-2 prohibition checks PASSED")
        return 0
    else:
        print("Some L-2 prohibition checks FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
