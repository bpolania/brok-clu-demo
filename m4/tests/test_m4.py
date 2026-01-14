#!/usr/bin/env python3
"""
Phase M-4 Determinism and Observability Tests

Tests verify that:
- All utilities produce deterministic output
- Manifest and trace are deterministic
- No timestamps or absolute paths leak into outputs
- Run ID derivation is content-based
"""

import sys
import os
import json
import tempfile
import unittest

# Add m4/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils import (
    sha256_bytes,
    sha256_file,
    to_rel_path,
    is_absolute_path,
    validate_no_absolute_paths,
    validate_no_timestamps,
    stable_json_dumps,
    stable_json_write,
    derive_run_id,
    PathSafetyError
)
from manifest import ManifestBuilder
from trace import TraceWriter


class TestSha256Determinism(unittest.TestCase):
    """Test SHA-256 hash determinism."""

    def test_sha256_bytes_deterministic(self):
        """Same bytes must produce same hash."""
        data = b"test content for hashing"
        results = [sha256_bytes(data) for _ in range(10)]
        self.assertTrue(all(r == results[0] for r in results))

    def test_sha256_bytes_different_input_different_hash(self):
        """Different bytes must produce different hashes."""
        hash1 = sha256_bytes(b"content A")
        hash2 = sha256_bytes(b"content B")
        self.assertNotEqual(hash1, hash2)

    def test_sha256_file_deterministic(self):
        """Same file content must produce same hash."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b"file content for testing")
            path = f.name

        try:
            results = [sha256_file(path) for _ in range(10)]
            self.assertTrue(all(r == results[0] for r in results))
        finally:
            os.unlink(path)

    def test_sha256_file_matches_bytes(self):
        """File hash must match direct bytes hash."""
        content = b"matching content test"
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(content)
            path = f.name

        try:
            file_hash = sha256_file(path)
            bytes_hash = sha256_bytes(content)
            self.assertEqual(file_hash, bytes_hash)
        finally:
            os.unlink(path)


class TestRelPathDeterminism(unittest.TestCase):
    """Test relative path conversion."""

    def test_to_rel_path_basic(self):
        """Basic path conversion."""
        result = to_rel_path("/repo", "/repo/src/file.py")
        self.assertEqual(result, "src/file.py")

    def test_to_rel_path_posix_separators(self):
        """Result must use POSIX separators."""
        result = to_rel_path("/repo", "/repo/src/subdir/file.py")
        self.assertNotIn("\\", result)
        self.assertEqual(result, "src/subdir/file.py")

    def test_to_rel_path_rejects_escape(self):
        """Paths escaping repo must be rejected."""
        with self.assertRaises(PathSafetyError):
            to_rel_path("/repo", "/other/file.py")

    def test_to_rel_path_allow_external(self):
        """External paths can be marked with allow_external."""
        result = to_rel_path("/repo", "/other/file.py", allow_external=True)
        self.assertTrue(result.startswith("[external]:"))

    def test_is_absolute_path_unix(self):
        """Detect Unix absolute paths."""
        self.assertTrue(is_absolute_path("/usr/bin/python"))
        self.assertFalse(is_absolute_path("src/file.py"))

    def test_is_absolute_path_windows(self):
        """Detect Windows absolute paths."""
        self.assertTrue(is_absolute_path("C:\\Users\\test"))
        self.assertTrue(is_absolute_path("D:/data/file.txt"))


class TestValidationFunctions(unittest.TestCase):
    """Test validation utilities."""

    def test_validate_no_absolute_paths_clean(self):
        """Clean data passes validation."""
        data = {
            "path": "src/file.py",
            "items": ["one", "two"],
            "nested": {"ref": "artifacts/output.json"}
        }
        errors = validate_no_absolute_paths(data)
        self.assertEqual(errors, [])

    def test_validate_no_absolute_paths_detects_unix(self):
        """Detects Unix absolute paths."""
        data = {"path": "/usr/bin/python"}
        errors = validate_no_absolute_paths(data)
        self.assertEqual(len(errors), 1)
        self.assertIn("/usr/bin/python", errors[0])

    def test_validate_no_absolute_paths_detects_windows(self):
        """Detects Windows absolute paths."""
        data = {"path": "C:\\Users\\file.txt"}
        errors = validate_no_absolute_paths(data)
        self.assertEqual(len(errors), 1)

    def test_validate_no_absolute_paths_nested(self):
        """Detects absolute paths in nested structures."""
        data = {
            "level1": {
                "level2": ["/absolute/path", "relative/path"]
            }
        }
        errors = validate_no_absolute_paths(data)
        self.assertEqual(len(errors), 1)

    def test_validate_no_timestamps_clean(self):
        """Clean data passes timestamp validation."""
        data = {
            "input_path_rel": "artifacts/input.txt",
            "status": "OK",
            "artifacts": [{"path": "out.json", "sha256": "abc123"}]
        }
        errors = validate_no_timestamps(data)
        self.assertEqual(errors, [])

    def test_validate_no_timestamps_detects_keys(self):
        """Detects timestamp keys."""
        data = {"timestamp": 123, "other": "value"}
        errors = validate_no_timestamps(data)
        self.assertEqual(len(errors), 1)
        self.assertIn("timestamp", errors[0].lower())

    def test_validate_no_timestamps_detects_iso_datetime(self):
        """Detects ISO 8601 datetime strings."""
        data = {"value": "2024-01-15T10:30:00Z"}
        errors = validate_no_timestamps(data)
        self.assertEqual(len(errors), 1)

    def test_validate_no_timestamps_allows_safe_integers(self):
        """Safe integers pass validation."""
        data = {"count": 42, "seq": 0, "version": 100}
        errors = validate_no_timestamps(data)
        self.assertEqual(errors, [])

    def test_validate_no_timestamps_detects_epoch(self):
        """Detects epoch-like integers."""
        data = {"value": 1700000000}  # Unix epoch
        errors = validate_no_timestamps(data)
        self.assertEqual(len(errors), 1)


class TestStableJson(unittest.TestCase):
    """Test stable JSON serialization."""

    def test_stable_json_sorted_keys(self):
        """Keys must be sorted alphabetically."""
        data = {"z": 1, "a": 2, "m": 3}
        result = stable_json_dumps(data)
        # Keys should appear in order: a, m, z
        a_pos = result.find('"a"')
        m_pos = result.find('"m"')
        z_pos = result.find('"z"')
        self.assertLess(a_pos, m_pos)
        self.assertLess(m_pos, z_pos)

    def test_stable_json_deterministic(self):
        """Same data must produce same output."""
        data = {"items": [3, 1, 2], "name": "test", "value": True}
        results = [stable_json_dumps(data) for _ in range(10)]
        self.assertTrue(all(r == results[0] for r in results))

    def test_stable_json_newline_terminated(self):
        """Output must end with newline."""
        result = stable_json_dumps({"key": "value"})
        self.assertTrue(result.endswith('\n'))

    def test_stable_json_nested_sorting(self):
        """Nested objects must also have sorted keys."""
        data = {"outer": {"z": 1, "a": 2}}
        result = stable_json_dumps(data)
        self.assertIn('"a": 2', result)
        self.assertIn('"z": 1', result)
        # 'a' should come before 'z' in the nested object
        a_pos = result.find('"a"')
        z_pos = result.find('"z"')
        self.assertLess(a_pos, z_pos)

    def test_stable_json_write_file(self):
        """stable_json_write produces same output as stable_json_dumps."""
        data = {"test": True, "values": [1, 2, 3]}

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            path = f.name

        try:
            stable_json_write(path, data)
            with open(path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            string_content = stable_json_dumps(data)
            self.assertEqual(file_content, string_content)
        finally:
            os.unlink(path)


class TestRunIdDerivation(unittest.TestCase):
    """Test run ID derivation."""

    def test_derive_run_id_deterministic(self):
        """Same inputs must produce same run ID."""
        results = [
            derive_run_id("abc123", "def456", "ghi789")
            for _ in range(10)
        ]
        self.assertTrue(all(r == results[0] for r in results))

    def test_derive_run_id_format(self):
        """Run ID must have correct format."""
        run_id = derive_run_id("abc", "def", "ghi")
        self.assertTrue(run_id.startswith("m4_"))
        # Should be m4_ (3 chars) + 16 hex characters = 19 total
        self.assertEqual(len(run_id), 19)

    def test_derive_run_id_different_inputs(self):
        """Different inputs must produce different run IDs."""
        id1 = derive_run_id("abc", "def", "ghi")
        id2 = derive_run_id("xyz", "def", "ghi")
        self.assertNotEqual(id1, id2)

    def test_derive_run_id_optional_params(self):
        """Optional parameters handled correctly."""
        id1 = derive_run_id("abc")
        id2 = derive_run_id("abc", None, None)
        self.assertEqual(id1, id2)


class TestManifestBuilder(unittest.TestCase):
    """Test manifest builder determinism."""

    def setUp(self):
        self.repo_root = tempfile.mkdtemp()
        # Create a test input file
        self.input_path = os.path.join(self.repo_root, "input.txt")
        with open(self.input_path, 'w') as f:
            f.write("test input content")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.repo_root, ignore_errors=True)

    def test_manifest_deterministic(self):
        """Same operations must produce same manifest."""
        manifests = []
        for _ in range(5):
            builder = ManifestBuilder(self.repo_root)
            builder.set_input(self.input_path)
            builder.add_stage("TEST", "OK")
            manifests.append(builder.build())

        first = json.dumps(manifests[0], sort_keys=True)
        for m in manifests[1:]:
            self.assertEqual(first, json.dumps(m, sort_keys=True))

    def test_manifest_no_absolute_paths(self):
        """Manifest must not contain absolute paths."""
        builder = ManifestBuilder(self.repo_root)
        builder.set_input(self.input_path)
        builder.add_stage("TEST", "OK")
        manifest = builder.build()

        errors = validate_no_absolute_paths(manifest)
        self.assertEqual(errors, [], f"Found absolute paths: {errors}")

    def test_manifest_no_timestamps(self):
        """Manifest must not contain timestamps."""
        builder = ManifestBuilder(self.repo_root)
        builder.set_input(self.input_path)
        builder.add_stage("TEST", "OK")
        manifest = builder.build()

        errors = validate_no_timestamps(manifest)
        self.assertEqual(errors, [], f"Found timestamps: {errors}")


class TestTraceWriter(unittest.TestCase):
    """Test trace writer determinism."""

    def setUp(self):
        self.repo_root = tempfile.mkdtemp()
        # Create an input file under the repo root
        self.input_path = os.path.join(self.repo_root, "input.txt")
        with open(self.input_path, 'w') as f:
            f.write("test content")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.repo_root, ignore_errors=True)

    def test_trace_deterministic(self):
        """Same events must produce same trace."""
        traces = []
        for _ in range(5):
            writer = TraceWriter(self.repo_root)
            writer.run_start(self.input_path, "abc123")
            writer.gate_decision("ACCEPT")
            writer.run_complete("test_run")
            traces.append(writer.get_events())

        first = json.dumps(traces[0], sort_keys=True)
        for t in traces[1:]:
            self.assertEqual(first, json.dumps(t, sort_keys=True))

    def test_trace_sequential_numbers(self):
        """Events must have sequential sequence numbers."""
        writer = TraceWriter(self.repo_root)
        writer.run_start(self.input_path, "abc123")
        writer.gate_decision("ACCEPT")
        writer.execution_started()
        writer.run_complete("test_run")

        events = writer.get_events()
        for i, event in enumerate(events):
            self.assertEqual(event["seq"], i)

    def test_trace_no_absolute_paths(self):
        """Trace events must not contain absolute paths."""
        writer = TraceWriter(self.repo_root)
        writer.run_start(self.input_path, "abc123")
        writer.gate_decision("REJECT", "NO_PROPOSALS")
        writer.execution_skipped("decision=REJECT")
        writer.run_complete("test_run")

        events = writer.get_events()
        for event in events:
            errors = validate_no_absolute_paths(event)
            self.assertEqual(errors, [], f"Event has absolute paths: {event}")

    def test_trace_write_jsonl_format(self):
        """Written trace must be valid JSONL."""
        writer = TraceWriter(self.repo_root)
        writer.run_start(self.input_path, "abc123")
        writer.run_complete("test_run")

        output_dir = os.path.join(self.repo_root, "output")
        trace_path = writer.write(output_dir)

        with open(trace_path, 'r') as f:
            lines = f.readlines()

        for line in lines:
            # Each line must be valid JSON
            parsed = json.loads(line.strip())
            self.assertIn("seq", parsed)
            self.assertIn("event", parsed)


class TestEndToEndDeterminism(unittest.TestCase):
    """End-to-end determinism tests."""

    def setUp(self):
        self.repo_root = tempfile.mkdtemp()
        self.input_path = os.path.join(self.repo_root, "input.txt")
        with open(self.input_path, 'w') as f:
            f.write("test input")
        # Create a proposal file for tracing
        self.proposal_path = os.path.join(self.repo_root, "proposal.json")
        with open(self.proposal_path, 'w') as f:
            f.write('{"proposals": []}')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.repo_root, ignore_errors=True)

    def test_full_run_deterministic(self):
        """Full manifest + trace run must be deterministic."""
        outputs = []

        for _ in range(3):
            builder = ManifestBuilder(self.repo_root)
            builder.set_input(self.input_path)
            builder.add_stage("PROPOSAL", "OK")
            builder.add_stage("ARTIFACT", "OK")
            builder.add_stage("EXECUTION", "SKIP")

            writer = TraceWriter(self.repo_root)
            writer.run_start(self.input_path, sha256_file(self.input_path))
            writer.proposal_generated(self.proposal_path, 0)
            writer.gate_decision("REJECT", "NO_PROPOSALS")
            writer.execution_skipped("decision=REJECT")
            run_id = builder.get_run_id()
            writer.run_complete(run_id)

            outputs.append({
                "manifest": builder.build(),
                "trace": writer.get_events(),
                "run_id": run_id
            })

        first = json.dumps(outputs[0], sort_keys=True)
        for o in outputs[1:]:
            self.assertEqual(first, json.dumps(o, sort_keys=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
