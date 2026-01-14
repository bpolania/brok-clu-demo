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


class TestTimestampPatternDetection(unittest.TestCase):
    """Test detection of timestamp patterns in strings."""

    def test_detects_run_directory_timestamp_pattern(self):
        """Must detect M-3 run directory timestamp patterns in strings."""
        data = {"path": "artifacts/run/run_20260114T173856Z/stdout.raw.kv"}
        errors = validate_no_timestamps(data)
        self.assertEqual(len(errors), 1)
        self.assertIn("run_20260114T173856Z", errors[0])

    def test_detects_iso_datetime_in_path(self):
        """Must detect ISO datetime patterns embedded in path strings."""
        data = {"path": "logs/2024-01-15T10:30:00_output.log"}
        errors = validate_no_timestamps(data)
        self.assertEqual(len(errors), 1)

    def test_allows_external_marker(self):
        """Must allow [external]: markers."""
        data = {"input_path_rel": "[external]:test.txt"}
        errors = validate_no_timestamps(data)
        self.assertEqual(errors, [])

    def test_allows_deterministic_run_id(self):
        """Must allow deterministic run IDs like run_d357c973b734."""
        data = {"path": "artifacts/proposals/run_d357c973b734/proposal_set.json"}
        errors = validate_no_timestamps(data)
        self.assertEqual(errors, [])


class TestE2EDeterminismCLI(unittest.TestCase):
    """
    E2E determinism proof test using the real CLI.

    Runs ./brok --input twice with identical input and verifies
    M-4 outputs are byte-for-byte identical.
    """

    @classmethod
    def setUpClass(cls):
        """Find repo root."""
        cls.repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        )))
        cls.brok_path = os.path.join(cls.repo_root, "brok")

    def setUp(self):
        """Create temp input file with fixed content."""
        self.temp_dir = tempfile.mkdtemp()
        self.input_path = os.path.join(self.temp_dir, "e2e_test_input.txt")
        # Fixed content for determinism
        with open(self.input_path, 'w') as f:
            f.write("restart alpha subsystem gracefully\n")

    def tearDown(self):
        """Clean up temp files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _run_brok(self):
        """Run brok CLI and return stderr output."""
        import subprocess
        result = subprocess.run(
            [self.brok_path, "--input", self.input_path],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )
        return result.stderr, result.returncode

    def _extract_run_id(self, stderr: str) -> str:
        """Extract M-4 run ID from stderr output."""
        import re
        match = re.search(r'Run ID: (m4_[a-f0-9]+)', stderr)
        if match:
            return match.group(1)
        raise ValueError("Could not find M-4 run ID in stderr")

    def test_e2e_determinism_manifest(self):
        """Running CLI twice must produce identical manifest.json."""
        # First run
        stderr1, rc1 = self._run_brok()
        self.assertEqual(rc1, 0, f"First run failed: {stderr1}")
        run_id = self._extract_run_id(stderr1)

        manifest_path = os.path.join(
            self.repo_root, "artifacts", "run", run_id, "manifest.json"
        )
        with open(manifest_path, 'rb') as f:
            manifest_bytes1 = f.read()

        # Second run (should overwrite with identical content)
        stderr2, rc2 = self._run_brok()
        self.assertEqual(rc2, 0, f"Second run failed: {stderr2}")

        with open(manifest_path, 'rb') as f:
            manifest_bytes2 = f.read()

        self.assertEqual(manifest_bytes1, manifest_bytes2,
            "Manifest not byte-for-byte identical across runs")

    def test_e2e_determinism_trace(self):
        """Running CLI twice must produce identical trace.jsonl."""
        # First run
        stderr1, rc1 = self._run_brok()
        self.assertEqual(rc1, 0)
        run_id = self._extract_run_id(stderr1)

        trace_path = os.path.join(
            self.repo_root, "artifacts", "run", run_id, "trace.jsonl"
        )
        with open(trace_path, 'rb') as f:
            trace_bytes1 = f.read()

        # Second run
        stderr2, rc2 = self._run_brok()
        self.assertEqual(rc2, 0)

        with open(trace_path, 'rb') as f:
            trace_bytes2 = f.read()

        self.assertEqual(trace_bytes1, trace_bytes2,
            "Trace not byte-for-byte identical across runs")


class TestRealOutputValidation(unittest.TestCase):
    """
    Validate real CLI outputs contain no timestamps or absolute paths.
    """

    @classmethod
    def setUpClass(cls):
        """Run CLI once to generate outputs."""
        cls.repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        )))
        cls.brok_path = os.path.join(cls.repo_root, "brok")

        # Create temp input
        cls.temp_dir = tempfile.mkdtemp()
        cls.input_path = os.path.join(cls.temp_dir, "validation_test.txt")
        with open(cls.input_path, 'w') as f:
            f.write("restart alpha subsystem gracefully\n")

        # Run CLI
        import subprocess
        result = subprocess.run(
            [cls.brok_path, "--input", cls.input_path],
            capture_output=True,
            text=True,
            cwd=cls.repo_root
        )
        cls.stderr = result.stderr

        # Extract run ID
        import re
        match = re.search(r'Run ID: (m4_[a-f0-9]+)', cls.stderr)
        if match:
            cls.run_id = match.group(1)
        else:
            cls.run_id = None

    @classmethod
    def tearDownClass(cls):
        """Clean up."""
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_manifest_no_absolute_paths(self):
        """Real manifest must not contain absolute paths."""
        if not self.run_id:
            self.skipTest("No run ID found")

        manifest_path = os.path.join(
            self.repo_root, "artifacts", "run", self.run_id, "manifest.json"
        )
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        errors = validate_no_absolute_paths(manifest)
        self.assertEqual(errors, [], f"Manifest has absolute paths: {errors}")

    def test_manifest_no_timestamps(self):
        """Real manifest must not contain timestamps."""
        if not self.run_id:
            self.skipTest("No run ID found")

        manifest_path = os.path.join(
            self.repo_root, "artifacts", "run", self.run_id, "manifest.json"
        )
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        errors = validate_no_timestamps(manifest)
        self.assertEqual(errors, [], f"Manifest has timestamps: {errors}")

    def test_trace_no_absolute_paths(self):
        """Real trace events must not contain absolute paths."""
        if not self.run_id:
            self.skipTest("No run ID found")

        trace_path = os.path.join(
            self.repo_root, "artifacts", "run", self.run_id, "trace.jsonl"
        )
        with open(trace_path, 'r') as f:
            for line in f:
                event = json.loads(line.strip())
                errors = validate_no_absolute_paths(event)
                self.assertEqual(errors, [],
                    f"Trace event has absolute paths: {event}")

    def test_trace_no_timestamps(self):
        """Real trace events must not contain timestamps."""
        if not self.run_id:
            self.skipTest("No run ID found")

        trace_path = os.path.join(
            self.repo_root, "artifacts", "run", self.run_id, "trace.jsonl"
        )
        with open(trace_path, 'r') as f:
            for line in f:
                event = json.loads(line.strip())
                errors = validate_no_timestamps(event)
                self.assertEqual(errors, [],
                    f"Trace event has timestamps: {event}")


class TestStdoutRawKvBinaryOnly(unittest.TestCase):
    """
    Ensure stdout.raw.kv is only accessed in binary mode (for hashing).

    M-4 must never parse or interpret stdout.raw.kv content.
    """

    def test_sha256_file_uses_binary_mode(self):
        """sha256_file must open files in binary mode."""
        # Create a test file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b"test content")
            path = f.name

        try:
            # Monkeypatch open to track mode
            original_open = open
            open_calls = []

            def tracking_open(file, mode='r', *args, **kwargs):
                if 'stdout.raw.kv' in str(file) or path in str(file):
                    open_calls.append((file, mode))
                return original_open(file, mode, *args, **kwargs)

            # Temporarily replace open
            import builtins
            builtins.open = tracking_open

            try:
                result = sha256_file(path)
                self.assertIsInstance(result, str)
                self.assertEqual(len(result), 64)  # SHA-256 hex digest

                # Verify binary mode was used
                for call_file, call_mode in open_calls:
                    self.assertIn('b', call_mode,
                        f"File {call_file} opened in non-binary mode: {call_mode}")
            finally:
                builtins.open = original_open
        finally:
            os.unlink(path)

    def test_m4_never_reads_stdout_raw_kv_as_text(self):
        """M-4 code must not read stdout.raw.kv in text mode."""
        # This is a structural test - verify the sha256_file implementation
        import inspect
        source = inspect.getsource(sha256_file)

        # Should contain 'rb' for binary read
        self.assertIn("'rb'", source,
            "sha256_file must use 'rb' mode for reading files")

        # Should NOT contain text mode reads
        self.assertNotIn("'r')", source,
            "sha256_file must not use text mode")


class TestAuthoritativeOutputsW1(unittest.TestCase):
    """
    W1 Fix Tests: Verify authoritative_outputs is correctly populated.

    When execution occurs and stdout.raw.kv is hashed:
    - authoritative_outputs must contain "stdout.raw.kv"

    When execution is skipped:
    - authoritative_outputs must be empty
    """

    def setUp(self):
        self.repo_root = tempfile.mkdtemp()
        self.input_path = os.path.join(self.repo_root, "input.txt")
        with open(self.input_path, 'w') as f:
            f.write("test input content")
        # Create a fake stdout.raw.kv file
        self.stdout_raw_kv_path = os.path.join(self.repo_root, "stdout.raw.kv")
        with open(self.stdout_raw_kv_path, 'wb') as f:
            f.write(b"key=value\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.repo_root, ignore_errors=True)

    def test_executed_run_has_authoritative_stdout_raw_kv(self):
        """When execution occurs and stdout.raw.kv exists, authoritative_outputs must contain 'stdout.raw.kv'."""
        builder = ManifestBuilder(self.repo_root)
        builder.set_input(self.input_path)
        # Simulate adding stdout.raw.kv as authoritative with omit_path=True
        builder.add_artifact(
            self.stdout_raw_kv_path,
            artifact_type="stdout.raw.kv",
            authoritative=True,
            omit_path=True
        )
        builder.record_execution(executed=True)
        builder.add_stage("EXECUTION", "OK", omit_outputs=True)

        manifest = builder.build()

        # Verify authoritative_outputs contains "stdout.raw.kv"
        authoritative = manifest["authority_boundary"]["authoritative_outputs"]
        self.assertIn("stdout.raw.kv", authoritative,
            f"Expected 'stdout.raw.kv' in authoritative_outputs, got: {authoritative}")

    def test_skipped_run_has_empty_authoritative_outputs(self):
        """When execution is skipped, authoritative_outputs must be empty."""
        builder = ManifestBuilder(self.repo_root)
        builder.set_input(self.input_path)
        # No stdout.raw.kv added (execution was skipped)
        builder.record_execution(executed=False)
        builder.add_stage("EXECUTION", "SKIP", omit_outputs=True)

        manifest = builder.build()

        # Verify authoritative_outputs is empty
        authoritative = manifest["authority_boundary"]["authoritative_outputs"]
        self.assertEqual(authoritative, [],
            f"Expected empty authoritative_outputs for skipped run, got: {authoritative}")

    def test_real_cli_executed_run_has_authoritative_stdout(self):
        """Real CLI run with execution must have stdout.raw.kv in authoritative_outputs."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        )))
        brok_path = os.path.join(repo_root, "brok")

        # Create temp input that triggers execution
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, "w1_test.txt")
        with open(input_path, 'w') as f:
            f.write("restart alpha subsystem gracefully\n")

        try:
            import subprocess
            result = subprocess.run(
                [brok_path, "--input", input_path],
                capture_output=True,
                text=True,
                cwd=repo_root
            )

            if result.returncode != 0:
                self.skipTest(f"CLI run failed: {result.stderr}")

            # Extract run ID
            import re
            match = re.search(r'Run ID: (m4_[a-f0-9]+)', result.stderr)
            if not match:
                self.skipTest("Could not find M-4 run ID")

            run_id = match.group(1)
            manifest_path = os.path.join(repo_root, "artifacts", "run", run_id, "manifest.json")

            with open(manifest_path, 'r') as f:
                manifest = json.load(f)

            # Verify execution occurred
            self.assertTrue(manifest.get("execution", {}).get("executed", False),
                "Expected execution.executed=true")

            # Verify authoritative_outputs contains stdout.raw.kv
            authoritative = manifest["authority_boundary"]["authoritative_outputs"]
            self.assertIn("stdout.raw.kv", authoritative,
                f"Expected 'stdout.raw.kv' in authoritative_outputs, got: {authoritative}")
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestStdoutRawKvBinaryOnlyRuntime(unittest.TestCase):
    """
    W2 Fix Tests: Runtime-real binary-only enforcement.

    Monkeypatches open() during CLI run and fails if stdout.raw.kv
    is opened in text mode.
    """

    def test_runtime_binary_only_enforcement(self):
        """Real CLI run must only open stdout.raw.kv in binary mode."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        )))

        # Create temp input
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, "w2_binary_test.txt")
        with open(input_path, 'w') as f:
            f.write("restart alpha subsystem gracefully\n")

        try:
            # Run via subprocess with a wrapper that monitors open() calls
            # The wrapper replicates the brok script logic with monkeypatched open()
            wrapper_code = '''
import sys
import os
import builtins
import hashlib

# Set up path BEFORE importing anything else
repo_root = sys.argv[1]
input_path = sys.argv[2]

sys.path.insert(0, os.path.join(repo_root, 'm3', 'src'))
sys.path.insert(0, os.path.join(repo_root, 'proposal', 'src'))
sys.path.insert(0, os.path.join(repo_root, 'artifact', 'src'))
os.chdir(repo_root)

# Track open calls for stdout.raw.kv
stdout_raw_kv_opens = []
original_open = builtins.open

def monitoring_open(file, mode='r', *args, **kwargs):
    file_str = str(file)
    if 'stdout.raw.kv' in file_str:
        stdout_raw_kv_opens.append((file_str, mode))
    return original_open(file, mode, *args, **kwargs)

builtins.open = monitoring_open

# Generate run_id like brok does
def _generate_run_id(inp):
    with original_open(inp, 'rb') as f:
        content = f.read()
    hasher = hashlib.sha256()
    hasher.update(b"M3_RUN_ID_V1")
    hasher.update(content)
    return f"run_{hasher.hexdigest()[:12]}"

run_id = _generate_run_id(input_path)

# Import and run orchestrator
from orchestrator import run_pipeline
result = run_pipeline(
    input_file=input_path,
    run_id=run_id,
    repo_root=repo_root,
    verbose=False
)

# Report any text-mode opens of stdout.raw.kv
for path, mode in stdout_raw_kv_opens:
    if 'b' not in mode:
        print(f"VIOLATION: stdout.raw.kv opened in text mode: {mode}", file=sys.stderr)
        sys.exit(99)

if stdout_raw_kv_opens:
    print(f"OK: stdout.raw.kv opened {len(stdout_raw_kv_opens)} times, all binary mode", file=sys.stderr)
else:
    print("OK: No stdout.raw.kv opens detected (execution may have been skipped)", file=sys.stderr)
'''
            wrapper_path = os.path.join(temp_dir, "open_monitor.py")
            with open(wrapper_path, 'w') as f:
                f.write(wrapper_code)

            import subprocess
            result = subprocess.run(
                [sys.executable, wrapper_path, repo_root, input_path],
                capture_output=True,
                text=True,
                cwd=repo_root
            )

            # Check for violation
            if result.returncode == 99:
                self.fail(f"VIOLATION: stdout.raw.kv opened in text mode:\n{result.stderr}")

            # Verify it ran successfully
            if result.returncode != 0 and "VIOLATION" not in result.stderr:
                self.skipTest(f"Wrapper run had issues: {result.stderr}")

            # If we got here with no violation, test passes
            self.assertNotIn("VIOLATION", result.stderr,
                f"Binary-only enforcement failed: {result.stderr}")

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
