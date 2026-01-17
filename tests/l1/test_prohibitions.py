#!/usr/bin/env python3
"""
Phase L-1 Prohibition Checks (Repo-Wide)

Verifies that prohibited patterns do not exist in the repository.
Scans entire repo excluding: .git/, artifacts/, docs/migration/evidence/,
__pycache__/, .venv/, .idea/, and other build caches.

Prohibitions checked:
1. No ACCEPT fixtures or acceptance semantics
2. No retry loops around proposal acquisition
3. No scoring/ranking/confidence keywords in runtime paths
4. No new CLI flags beyond --input
5. No environment variables controlling seam behavior
6. No runtime configurability

These are grep-based checks that verify absence of patterns.
"""

import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Directories to exclude from repo-wide scans
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
    'docs/migration/evidence',  # Evidence files may contain prohibited words in context
    'tests/l1',  # Test files contain pattern strings for checking
    'tests/l2',  # L-2 test files contain pattern strings for checking
}

# Seam-specific paths (for env var check which is scoped to seam only)
SEAM_PATHS = [
    os.path.join(REPO_ROOT, 'src', 'artifact_layer'),
]

BROK_CLI_PATH = os.path.join(REPO_ROOT, 'brok')


def _should_skip_path(path: str) -> bool:
    """Check if path should be skipped based on exclusion rules."""
    rel_path = os.path.relpath(path, REPO_ROOT)
    rel_path_normalized = rel_path.replace(os.sep, '/')
    parts = rel_path.split(os.sep)
    for part in parts:
        if part in EXCLUDED_DIRS:
            return True
    # Also skip specific paths
    if 'docs/migration/evidence' in rel_path_normalized:
        return True
    if 'tests/l1' in rel_path_normalized:
        return True
    if 'tests/l2' in rel_path_normalized:
        return True
    return False


def _scan_repo_for_patterns(patterns: list, file_ext: str = '.py') -> tuple:
    """
    Scan repo for prohibited patterns.

    Returns:
        (passed, message) tuple
    """
    for root, dirs, files in os.walk(REPO_ROOT):
        # Modify dirs in-place to skip excluded directories
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


def check_no_retry_loops():
    """Check that no retry loops exist in runtime paths."""
    # These patterns are checked in Python files that are part of runtime
    prohibited_patterns = [
        r'\bretry\s*\(',        # retry function calls
        r'\bmax_attempts\b',
        r'\bbackoff\b',
        r'\btry_again\b',
        r'\battempt\s*\+=\s*1',
        r'while.*attempt.*<',
        r'for.*attempt.*in.*range',
    ]
    return _scan_repo_for_patterns(prohibited_patterns)


def check_no_scoring_ranking():
    """Check that no scoring/ranking/confidence keywords exist in runtime paths."""
    prohibited_patterns = [
        r'\bscore\s*=',         # score assignment
        r'\bscoring\s*\(',      # scoring function
        r'\brank\s*=',          # rank assignment
        r'\branking\s*\(',      # ranking function
        r'\bconfidence\s*[=<>]', # confidence comparison/assignment
        r'\bthreshold\s*=',     # threshold assignment
        r'\.score\b',           # .score attribute
        r'\.rank\b',            # .rank attribute
        r'\.confidence\b',      # .confidence attribute
    ]
    return _scan_repo_for_patterns(prohibited_patterns)


def check_no_new_cli_flags():
    """Check that no new CLI flags exist beyond --input."""
    allowed_flags = {'--input', '-h', '--help'}

    result = subprocess.run(
        [sys.executable, BROK_CLI_PATH, '--help'],
        capture_output=True,
        text=True
    )

    # Parse help output for flags
    found_flags = set(re.findall(r'(--[a-z-]+|-[a-z])', result.stdout + result.stderr))

    new_flags = found_flags - allowed_flags
    if new_flags:
        return False, f"Found new CLI flags: {new_flags}"

    return True, "No new CLI flags found"


def check_no_env_vars_in_seam():
    """Check that no environment variables control seam behavior."""
    prohibited_patterns = [
        r'os\.environ\[',
        r'os\.getenv\(',
        r'getenv\(',
    ]

    for path in SEAM_PATHS:
        if not os.path.isdir(path):
            continue
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for fname in files:
                if not fname.endswith('.py'):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                for pattern in prohibited_patterns:
                    for line_num, line in enumerate(lines, 1):
                        if re.search(pattern, line):
                            rel_path = os.path.relpath(fpath, REPO_ROOT)
                            return False, f"Found env var pattern '{pattern}' at {rel_path}:{line_num}"
    return True, "No environment variables in seam code"


def check_no_runtime_config():
    """Check that no runtime configurability exists repo-wide."""
    prohibited_patterns = [
        r'config_file\s*=',
        r'load_config\(',
        r'configparser',
        r'runtime_mode\s*=',
        r'debug_mode\s*=',
        r'if\s+debug\s*:',
        r'if\s+DEBUG\s*:',
    ]
    return _scan_repo_for_patterns(prohibited_patterns)


def check_no_os_import_in_seam_provider():
    """Check that seam_provider.py does not import os (env access risk)."""
    seam_provider = os.path.join(REPO_ROOT, 'src', 'artifact_layer', 'seam_provider.py')
    if not os.path.isfile(seam_provider):
        return False, "seam_provider.py not found"

    with open(seam_provider, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for os import (but not os.path which is OK in other files)
    if re.search(r'^import os\b', content, re.MULTILINE):
        return False, "seam_provider.py imports os module"
    if re.search(r'^from os import', content, re.MULTILINE):
        return False, "seam_provider.py imports from os module"

    return True, "seam_provider.py does not import os"


def main():
    """Run all prohibition checks."""
    checks = [
        ("No ACCEPT fixtures (repo-wide)", check_no_accept_fixtures),
        ("No retry loops (repo-wide)", check_no_retry_loops),
        ("No scoring/ranking (repo-wide)", check_no_scoring_ranking),
        ("No new CLI flags", check_no_new_cli_flags),
        ("No env vars in seam", check_no_env_vars_in_seam),
        ("No runtime config (repo-wide)", check_no_runtime_config),
        ("No os import in seam_provider", check_no_os_import_in_seam_provider),
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
    print("Phase L-1 Prohibition Checks (Repo-Wide)")
    print("=" * 70)

    for name, status, message in results:
        print(f"[{status}] {name}")
        print(f"       {message}")

    print("=" * 70)
    if all_passed:
        print("All prohibition checks PASSED")
        return 0
    else:
        print("Some prohibition checks FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
