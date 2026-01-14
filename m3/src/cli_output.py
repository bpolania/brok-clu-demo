#!/usr/bin/env python3
"""
Phase M-3: CLI Output Formatting

Provides structured, labeled output for the pipeline stages to make
authority boundaries externally visible.

Output sections:
1. PROPOSAL (DERIVED, NON-AUTHORITATIVE) - Shows proposal count and summary
2. ARTIFACT (AUTHORITATIVE WRAPPER DECISION) - Shows decision and ruleset
3. EXECUTION (FROZEN, AUTHORITATIVE OUTPUT) - Shows execution status

Design principles:
- Make it hard to confuse proposal output as a decision
- Make it hard to confuse artifact as execution truth
- Make it hard to confuse derived summaries as guarantees
- Never print or interpret stdout.raw.kv content
"""

import json
import sys
from typing import Dict, Optional, TextIO


# Section headers with authority labels
SECTION_PROPOSAL = """
================================================================================
[1/3] PROPOSAL (DERIVED, NON-AUTHORITATIVE)
================================================================================
"""

SECTION_ARTIFACT = """
================================================================================
[2/3] ARTIFACT (AUTHORITATIVE WRAPPER DECISION)
================================================================================
"""

SECTION_EXECUTION = """
================================================================================
[3/3] EXECUTION (FROZEN, AUTHORITATIVE OUTPUT = stdout.raw.kv)
================================================================================
"""

DISCLAIMER_PROPOSALS = """\
NOTE: Proposals are DERIVED and NON-AUTHORITATIVE. They do not constitute
      decisions. The artifact layer makes the authoritative wrapper decision.
"""

DISCLAIMER_ARTIFACT = """\
NOTE: Artifacts record DECISIONS, not execution outcomes. The artifact decides
      whether execution proceeds. Execution truth is in stdout.raw.kv only.
"""

DISCLAIMER_EXECUTION = """\
NOTE: stdout.raw.kv is the ONLY authoritative execution output. All other
      outputs are derived summaries. Do not treat derived outputs as guarantees.
"""


def format_proposal_section(
    proposal_set: Dict,
    proposal_set_path: str,
    output: TextIO = sys.stderr
) -> None:
    """
    Format and print the PROPOSAL section.

    Args:
        proposal_set: The loaded proposal set dict
        proposal_set_path: Path to proposal_set.json
        output: Output stream (default stderr)
    """
    print(SECTION_PROPOSAL, file=output)

    proposals = proposal_set.get("proposals", [])
    proposal_count = len(proposals)

    print(f"  Proposal count: {proposal_count}", file=output)
    print(f"  Source: {proposal_set_path}", file=output)

    if proposal_count == 0:
        print("  Status: NO PROPOSALS GENERATED", file=output)
        print("  (Input did not yield any actionable proposals)", file=output)
    elif proposal_count == 1:
        print("  Status: SINGLE PROPOSAL", file=output)
        # Show safe summary (kind only, no interpreted content)
        p = proposals[0]
        kind = p.get("kind", "UNKNOWN")
        print(f"  Proposal kind: {kind}", file=output)
    else:
        print(f"  Status: MULTIPLE PROPOSALS ({proposal_count})", file=output)
        print("  (Multiple proposals indicate ambiguity)", file=output)

    print("", file=output)
    print(DISCLAIMER_PROPOSALS, file=output)


def format_artifact_section(
    artifact: Dict,
    artifact_path: str,
    output: TextIO = sys.stderr
) -> None:
    """
    Format and print the ARTIFACT section.

    Args:
        artifact: The loaded artifact dict
        artifact_path: Path to artifact.json
        output: Output stream (default stderr)
    """
    print(SECTION_ARTIFACT, file=output)

    decision = artifact.get("decision", "UNKNOWN")
    construction = artifact.get("construction", {})
    ruleset_id = construction.get("ruleset_id", "UNKNOWN")
    proposal_count = construction.get("proposal_count", "?")

    print(f"  Decision: {decision}", file=output)
    print(f"  Ruleset: {ruleset_id}", file=output)
    print(f"  Proposal count: {proposal_count}", file=output)
    print(f"  Artifact path: {artifact_path}", file=output)

    if decision == "ACCEPT":
        print("  Status: EXECUTION PERMITTED", file=output)
    elif decision == "REJECT":
        reject_payload = artifact.get("reject_payload", {})
        reason_code = reject_payload.get("reason_code", "UNKNOWN")
        print(f"  Status: EXECUTION NOT PERMITTED", file=output)
        print(f"  Reason: {reason_code}", file=output)

    print("", file=output)
    print(DISCLAIMER_ARTIFACT, file=output)


def format_execution_section(
    decision: str,
    executed: bool,
    run_directory: Optional[str] = None,
    exit_code: Optional[int] = None,
    error: Optional[str] = None,
    output: TextIO = sys.stderr
) -> None:
    """
    Format and print the EXECUTION section.

    Args:
        decision: The artifact decision ("ACCEPT" or "REJECT")
        executed: Whether PoC v2 was actually invoked
        run_directory: Path to run directory (if executed)
        exit_code: Exit code from PoC v2 (if executed)
        error: Error message (if execution failed)
        output: Output stream (default stderr)
    """
    print(SECTION_EXECUTION, file=output)

    if decision == "REJECT":
        print("  Status: NOT INVOKED", file=output)
        print("  Reason: Artifact decision is REJECT", file=output)
        print("  (No PoC v2 execution occurred - this is expected behavior)", file=output)
    elif not executed:
        print("  Status: FAILED TO INVOKE", file=output)
        if error:
            print(f"  Error: {error}", file=output)
    else:
        print("  Status: INVOKED", file=output)
        if run_directory:
            print(f"  Run directory: {run_directory}", file=output)
            stdout_path = f"{run_directory}/stdout.raw.kv"
            print(f"  Authoritative output: {stdout_path}", file=output)
        if exit_code is not None:
            print(f"  Exit code: {exit_code}", file=output)

    print("", file=output)
    print(DISCLAIMER_EXECUTION, file=output)


def format_final_result(
    decision: str,
    executed: bool,
    reason_code: Optional[str] = None,
    output: TextIO = sys.stdout
) -> None:
    """
    Format the final machine-readable result line.

    This goes to stdout for parsing by callers.

    Args:
        decision: The artifact decision
        executed: Whether execution occurred
        reason_code: Reason code if REJECT
        output: Output stream (default stdout)
    """
    if decision == "ACCEPT":
        print(f"decision=ACCEPT executed={str(executed).lower()}", file=output)
    else:
        if reason_code:
            print(f"decision=REJECT reason_code={reason_code}", file=output)
        else:
            print(f"decision=REJECT", file=output)


def print_pipeline_header(output: TextIO = sys.stderr) -> None:
    """Print the pipeline header."""
    print("""
################################################################################
#                          BROK-CLU PIPELINE                                   #
#                                                                              #
#  Pipeline: INPUT -> PROPOSAL -> ARTIFACT -> EXECUTION                        #
#                                                                              #
#  Authority model:                                                            #
#    - Proposals are DERIVED and NON-AUTHORITATIVE                             #
#    - Artifacts hold WRAPPER-LEVEL DECISION AUTHORITY                         #
#    - Execution output (stdout.raw.kv) is the ONLY AUTHORITATIVE OUTPUT       #
#                                                                              #
################################################################################
""", file=output)


def print_pipeline_footer(output: TextIO = sys.stderr) -> None:
    """Print the pipeline footer."""
    print("""
################################################################################
#  END OF PIPELINE                                                             #
#                                                                              #
#  Remember: stdout.raw.kv is authoritative. Everything else is derived.       #
################################################################################
""", file=output)


# ASCII diagram for documentation
PIPELINE_DIAGRAM = """
+-------------------+     +-------------------+     +-------------------+
|      INPUT        |     |     PROPOSAL      |     |     ARTIFACT      |
|                   |     |                   |     |                   |
|  User-provided    | --> |  DERIVED          | --> |  AUTHORITATIVE    |
|  text/command     |     |  NON-AUTHORITATIVE|     |  WRAPPER DECISION |
|                   |     |  May be empty     |     |  ACCEPT or REJECT |
+-------------------+     +-------------------+     +-------------------+
                                                            |
                                                            v
                                              +-------------------+
                                              |    EXECUTION      |
                                              |                   |
                                              |  FROZEN PoC v2    |
                                              |  stdout.raw.kv    |
                                              |  = AUTHORITATIVE  |
                                              |    OUTPUT         |
                                              +-------------------+
"""
