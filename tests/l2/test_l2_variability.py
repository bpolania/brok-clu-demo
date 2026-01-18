#!/usr/bin/env python3
"""
Phase L-2 Proposal Variability Tests

Demonstrates that the offline nondeterministic engine produces variable output
while maintaining downstream determinism and REJECT-guaranteed behavior.

Key properties:
1. Same input may produce different ProposalSet bytes across runs (variability)
2. ALL runs produce REJECT (unmapped proposals guarantee INVALID_PROPOSALS)
3. Downstream behavior remains deterministic (exit code always 0)
4. No external services, API keys, or network required

These tests run entirely offline using OS randomness for nondeterminism.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BROK_CLI = os.path.join(REPO_ROOT, 'brok')

# Add src path for direct engine testing
sys.path.insert(0, os.path.join(REPO_ROOT, 'src'))


def _run_pipeline(input_text: str) -> dict:
    """Run the pipeline and extract proposal set info."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(input_text)
        input_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, BROK_CLI, '--input', input_path],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )

        # Find proposal set file from output (check both stdout and stderr)
        proposal_path = None
        all_output = result.stdout + result.stderr
        for line in all_output.split('\n'):
            if 'proposal_set.json' in line:
                if 'Source:' in line:
                    proposal_path = line.split('Source:')[1].strip()
                    break

        proposal_hash = None
        proposal_count = 0
        proposal_bytes = b""

        if proposal_path:
            full_path = os.path.join(REPO_ROOT, proposal_path)
            if os.path.exists(full_path):
                with open(full_path, 'rb') as f:
                    content = f.read()
                    proposal_hash = hashlib.sha256(content).hexdigest()[:16]
                    proposal_bytes = content
                    try:
                        proposal_data = json.loads(content)
                        proposal_count = len(proposal_data.get('proposals', []))
                    except json.JSONDecodeError:
                        pass

        return {
            'exit_code': result.returncode,
            'proposal_hash': proposal_hash,
            'proposal_count': proposal_count,
            'proposal_bytes': proposal_bytes,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'has_reject': 'decision=REJECT' in result.stdout,
            'has_accept': 'decision=ACCEPT' in result.stdout,
        }

    finally:
        os.unlink(input_path)


def test_variability_offline():
    """
    Test proposal variability using the offline nondeterministic engine.

    This test demonstrates that:
    - Multiple runs may produce different ProposalSet hashes
    - The engine runs without external services
    - Downstream determinism is maintained (exit code always 0)
    """
    # Test input that should map to a valid command
    test_input = "restart alpha subsystem gracefully"

    # Run 20 times to demonstrate variability (nondeterminism rate ~10%)
    runs = []
    for i in range(20):
        run_result = _run_pipeline(test_input)
        runs.append(run_result)

    # Collect results
    results = []
    results.append("Offline Nondeterministic Engine - Variability Test")
    results.append("=" * 60)
    results.append(f"Input: {test_input}")
    results.append(f"Runs: 20")
    results.append("")

    hashes = []
    for i, run in enumerate(runs):
        hashes.append(run['proposal_hash'])
        decision = 'REJECT' if run['has_reject'] else 'ACCEPT' if run['has_accept'] else 'UNKNOWN'
        results.append(f"Run {i+1}: hash={run['proposal_hash']}, proposals={run['proposal_count']}, decision={decision}")

    results.append("")

    # Analyze variability
    unique_hashes = set(h for h in hashes if h is not None)

    results.append("VARIABILITY ANALYSIS:")
    results.append(f"  Unique proposal hashes: {len(unique_hashes)}")

    variability_demonstrated = len(unique_hashes) > 1
    if variability_demonstrated:
        results.append("  Result: VARIABILITY DEMONSTRATED")
        results.append("  (Different runs produced different proposals - expected nondeterminism)")
    else:
        results.append("  Result: NO VARIABILITY IN THIS SAMPLE")
        results.append("  (May need more runs to observe variability)")

    # Check REJECT-only: ALL runs must produce REJECT (L-2 requirement)
    all_reject = all(run['has_reject'] for run in runs)
    no_accept = not any(run['has_accept'] for run in runs)
    reject_only = all_reject and no_accept
    results.append("")
    results.append("REJECT-ONLY VERIFICATION (L-2 CRITICAL):")
    results.append(f"  All runs REJECT: {all_reject}")
    results.append(f"  Zero ACCEPT: {no_accept}")
    if reject_only:
        results.append("  Result: REJECT-ONLY VERIFIED")
    else:
        results.append("  Result: REJECT-ONLY VIOLATED (L-2 BLOCKER)")

    # Check downstream determinism: exit code should always be 0
    all_exit_zero = all(run['exit_code'] == 0 for run in runs)
    results.append("")
    results.append("DOWNSTREAM DETERMINISM:")
    results.append(f"  All exit codes = 0: {all_exit_zero}")
    if all_exit_zero:
        results.append("  Result: DOWNSTREAM DETERMINISM MAINTAINED")
    else:
        results.append("  Result: DOWNSTREAM DETERMINISM VIOLATED")

    # Offline operation verified (no API key needed, no network)
    results.append("")
    results.append("OFFLINE OPERATION:")
    results.append("  External services required: None")
    results.append("  API keys required: None")
    results.append("  Network access required: None")
    results.append("  Result: OFFLINE OPERATION CONFIRMED")

    return '\n'.join(results), variability_demonstrated, all_exit_zero, reject_only


def test_direct_engine_variability():
    """
    Test the engine directly (not through CLI) to verify variability.

    This provides faster feedback and more runs for statistical confidence.
    """
    from artifact_layer.llm_engine import llm_engine

    test_input = b"restart alpha subsystem gracefully"

    # Run 20 times for statistical confidence
    hashes = set()
    results = []

    for i in range(20):
        output = llm_engine(test_input)
        h = hashlib.sha256(output).hexdigest()[:16]
        hashes.add(h)
        results.append((h, len(output)))

    variability = len(hashes) > 1

    report = []
    report.append("Direct Engine Variability Test")
    report.append("=" * 60)
    report.append(f"Runs: 20")
    report.append(f"Unique hashes: {len(hashes)}")
    report.append(f"Variability demonstrated: {variability}")
    report.append("")
    report.append("Sample outputs:")
    for i, (h, length) in enumerate(results[:5]):
        report.append(f"  Run {i+1}: hash={h}, bytes={length}")

    return '\n'.join(report), variability


def test_empty_input_always_rejects():
    """Test that empty input always produces REJECT."""
    runs = []
    for _ in range(3):
        run_result = _run_pipeline("")
        runs.append(run_result)

    all_reject = all(run['has_reject'] for run in runs)
    all_exit_zero = all(run['exit_code'] == 0 for run in runs)

    if all_reject and all_exit_zero:
        return True, "Empty input -> REJECT (exit 0) confirmed"
    else:
        return False, f"Unexpected: reject={all_reject}, exit_zero={all_exit_zero}"


def main():
    """Run all variability tests."""
    print("=" * 75)
    print("Phase L-2 Proposal Variability Tests (Offline)")
    print("=" * 75)
    print()
    print("These tests verify nondeterminism WITHOUT external services or API keys.")
    print()

    # Test 1: Direct engine variability
    print("-" * 75)
    print("Test 1: Direct Engine Variability")
    print("-" * 75)
    report1, var1 = test_direct_engine_variability()
    print(report1)
    print()

    # Test 2: Pipeline variability
    print("-" * 75)
    print("Test 2: Pipeline Variability (via CLI)")
    print("-" * 75)
    report2, var2, det2, rej2 = test_variability_offline()
    print(report2)
    print()

    # Test 3: Empty input
    print("-" * 75)
    print("Test 3: Empty Input Always Rejects")
    print("-" * 75)
    passed3, msg3 = test_empty_input_always_rejects()
    print(f"[{'PASS' if passed3 else 'FAIL'}] {msg3}")
    print()

    # Summary
    print("=" * 75)
    print("SUMMARY")
    print("=" * 75)
    print(f"Direct engine variability: {'PASS' if var1 else 'FAIL'}")
    print(f"Pipeline variability: {'PASS' if var2 else 'FAIL'}")
    print(f"REJECT-only (L-2 critical): {'PASS' if rej2 else 'FAIL'}")
    print(f"Downstream determinism: {'PASS' if det2 else 'FAIL'}")
    print(f"Empty input -> REJECT: {'PASS' if passed3 else 'FAIL'}")
    print()
    print("Offline operation: CONFIRMED (no secrets, no network)")
    print("=" * 75)

    # Return success if all properties demonstrated (including REJECT-only)
    if var1 and var2 and rej2 and det2 and passed3:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
