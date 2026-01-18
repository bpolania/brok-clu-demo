#!/usr/bin/env python3
"""
Phase M-4: Deterministic Trace Writer

Creates a deterministic trace.jsonl recording stage transitions.
Each line is a JSON object with:
- seq: Monotonic sequence number
- event: Event type token
- stage: Stage name
- detail: Deterministic details (paths, hashes)

No timestamps. No durations. No absolute paths.
All outputs are DERIVED and non-authoritative.
"""

import json
import os
from typing import Any, Dict, List, Optional

from utils import to_rel_path, sha256_file, validate_no_absolute_paths, validate_no_timestamps


# Event type tokens
EVENT_RUN_START = "M4_RUN_START"
EVENT_PROPOSAL_GENERATED = "PROPOSAL_GENERATED"
EVENT_PROPOSAL_EMPTY = "PROPOSAL_EMPTY"
EVENT_ARTIFACT_WRITTEN = "ARTIFACT_WRITTEN"
EVENT_GATE_ACCEPT = "GATE_ACCEPT"
EVENT_GATE_REJECT = "GATE_REJECT"
EVENT_EXECUTION_STARTED = "EXECUTION_STARTED"
EVENT_EXECUTION_SKIPPED = "EXECUTION_SKIPPED"
EVENT_EXECUTION_COMPLETE = "EXECUTION_COMPLETE"
EVENT_RUN_COMPLETE = "M4_RUN_COMPLETE"


class TraceWriter:
    """
    Writes deterministic trace events to trace.jsonl.

    Events are accumulated in memory and written atomically to ensure
    deterministic output even if the pipeline fails partway through.
    """

    def __init__(self, repo_root: str):
        """
        Initialize trace writer.

        Args:
            repo_root: Absolute path to repository root
        """
        self.repo_root = os.path.abspath(repo_root)
        self._events: List[Dict[str, Any]] = []
        self._seq = 0

    def _make_rel_path(self, path: str, allow_external: bool = False) -> str:
        """Convert path to repo-relative form."""
        if not path:
            return ""
        return to_rel_path(self.repo_root, path, allow_external=allow_external)

    def _emit(self, event: str, stage: str, detail: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a trace event.

        Args:
            event: Event type token
            stage: Stage name
            detail: Optional details dict (must be deterministic)

        Raises:
            ValueError: If event contains absolute paths or timestamps
        """
        record = {
            "seq": self._seq,
            "event": event,
            "stage": stage
        }
        if detail:
            record["detail"] = detail

        # Validate event before recording
        path_errors = validate_no_absolute_paths(record)
        if path_errors:
            raise ValueError(f"Trace event contains absolute paths: {path_errors}")

        timestamp_errors = validate_no_timestamps(record)
        if timestamp_errors:
            raise ValueError(f"Trace event contains timestamps: {timestamp_errors}")

        self._events.append(record)
        self._seq += 1

    def run_start(self, input_path: str, input_sha256: str) -> None:
        """Record run start event."""
        self._emit(EVENT_RUN_START, "INIT", {
            "input_path_rel": self._make_rel_path(input_path, allow_external=True),
            "input_sha256": input_sha256
        })

    def proposal_generated(self, proposal_path: str, proposal_count: int) -> None:
        """Record proposal generation event."""
        if proposal_count == 0:
            self._emit(EVENT_PROPOSAL_EMPTY, "PROPOSAL", {
                "path_rel": self._make_rel_path(proposal_path),
                "proposal_count": 0
            })
        else:
            self._emit(EVENT_PROPOSAL_GENERATED, "PROPOSAL", {
                "path_rel": self._make_rel_path(proposal_path),
                "proposal_count": proposal_count,
                "sha256": sha256_file(proposal_path) if os.path.isfile(proposal_path) else None
            })

    def artifact_written(self, artifact_path: str, decision: str) -> None:
        """Record artifact write event."""
        self._emit(EVENT_ARTIFACT_WRITTEN, "ARTIFACT", {
            "path_rel": self._make_rel_path(artifact_path),
            "decision": decision,
            "sha256": sha256_file(artifact_path) if os.path.isfile(artifact_path) else None
        })

    def gate_decision(self, decision: str, reason_code: Optional[str] = None) -> None:
        """Record execution gate decision."""
        if decision == "ACCEPT":
            self._emit(EVENT_GATE_ACCEPT, "GATE", {"decision": "ACCEPT"})
        else:
            detail = {"decision": "REJECT"}
            if reason_code:
                detail["reason_code"] = reason_code
            self._emit(EVENT_GATE_REJECT, "GATE", detail)

    def execution_started(self) -> None:
        """Record execution start event."""
        self._emit(EVENT_EXECUTION_STARTED, "EXECUTION")

    def execution_skipped(self, reason: str) -> None:
        """Record execution skip event."""
        self._emit(EVENT_EXECUTION_SKIPPED, "EXECUTION", {
            "executed": False,
            "reason": reason
        })

    def execution_complete(
        self,
        stdout_raw_kv_path: Optional[str],
        exit_code: int
    ) -> None:
        """
        Record execution completion event.

        Args:
            stdout_raw_kv_path: Path to stdout.raw.kv file (if exists)
            exit_code: Exit code from execution

        Note: We do NOT record the run directory path as it may contain
        timestamps. We only record the hash of stdout.raw.kv.
        """
        detail: Dict[str, Any] = {
            "executed": True,
            "exit_code": exit_code
        }
        # Record stdout.raw.kv hash without recording timestamped path
        if stdout_raw_kv_path and os.path.isfile(stdout_raw_kv_path):
            detail["stdout_raw_kv_sha256"] = sha256_file(stdout_raw_kv_path)
        self._emit(EVENT_EXECUTION_COMPLETE, "EXECUTION", detail)

    def run_complete(self, run_id: str) -> None:
        """Record run completion event."""
        self._emit(EVENT_RUN_COMPLETE, "COMPLETE", {"run_id": run_id})

    def get_events(self) -> List[Dict[str, Any]]:
        """Get accumulated events."""
        return self._events.copy()

    def write(self, output_dir: str) -> str:
        """
        Write trace to file.

        Args:
            output_dir: Directory to write trace.jsonl

        Returns:
            Path to written trace file
        """
        os.makedirs(output_dir, exist_ok=True)
        trace_path = os.path.join(output_dir, "trace.jsonl")

        with open(trace_path, 'w', encoding='utf-8', newline='\n') as f:
            for event in self._events:
                # Use sorted keys for deterministic output
                line = json.dumps(event, sort_keys=True, ensure_ascii=False)
                f.write(line + '\n')

        return trace_path
