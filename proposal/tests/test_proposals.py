#!/usr/bin/env python3
"""
Phase M-1 Unit Tests for Proposal Generation and Validation

Tests cover:
- Determinism: same input yields byte-for-byte identical output
- Boundedness: overlong input produces zero proposals
- Whitespace semantics: empty and whitespace-only inputs
- Validation: generator output validates; malformed output fails
- Unknown field rejection (additionalProperties enforcement)
- Bounded error output

These tests are isolated from PoC v2 tests.
"""

import sys
import os
import unittest
import json

# Add proposal/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from generator import (
    generate_proposal_set,
    proposal_set_to_json,
    SCHEMA_VERSION,
    MAX_INPUT_LENGTH,
    MAX_PROPOSALS
)
from validator import (
    validate_proposal_set,
    validate_and_normalize,
    MAX_ERRORS
)


class TestDeterminism(unittest.TestCase):
    """Test that proposal generation is deterministic."""

    def test_identical_output_for_identical_input(self):
        """Same input must produce byte-for-byte identical JSON output."""
        test_input = "restart alpha subsystem gracefully"

        # Generate multiple times
        outputs = []
        for _ in range(10):
            result = generate_proposal_set(test_input)
            json_output = proposal_set_to_json(result)
            outputs.append(json_output)

        # All outputs must be identical
        first = outputs[0]
        for i, output in enumerate(outputs[1:], 2):
            self.assertEqual(first, output,
                f"Run {i} produced different output than run 1")

    def test_determinism_across_various_inputs(self):
        """Determinism must hold for various input types."""
        test_cases = [
            "",
            "   ",
            "hello world",
            "restart alpha subsystem gracefully",
            "status of beta",
            "RESTART ALPHA SUBSYSTEM GRACEFULLY",  # case variation
            "unknown command xyz",
            "a" * 100,
        ]

        for test_input in test_cases:
            with self.subTest(input=repr(test_input)):
                result1 = proposal_set_to_json(generate_proposal_set(test_input))
                result2 = proposal_set_to_json(generate_proposal_set(test_input))
                self.assertEqual(result1, result2)


class TestBoundedness(unittest.TestCase):
    """Test input and output bounds."""

    def test_overlong_input_produces_zero_proposals(self):
        """Input exceeding MAX_INPUT_LENGTH must produce zero proposals."""
        overlong = "a" * (MAX_INPUT_LENGTH + 1)
        result = generate_proposal_set(overlong)

        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["proposals"], [])
        self.assertIn("INPUT_TOO_LONG", result.get("errors", []))

    def test_max_length_input_accepted(self):
        """Input at exactly MAX_INPUT_LENGTH must be processed normally."""
        exact_max = "a" * MAX_INPUT_LENGTH
        result = generate_proposal_set(exact_max)

        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["input"]["raw"], exact_max)
        # May or may not produce proposals depending on content
        self.assertLessEqual(len(result["proposals"]), MAX_PROPOSALS)

    def test_proposals_bounded_by_max(self):
        """Number of proposals must not exceed MAX_PROPOSALS."""
        # Test with valid input
        result = generate_proposal_set("restart alpha subsystem gracefully")
        self.assertLessEqual(len(result["proposals"]), MAX_PROPOSALS)

    def test_json_output_bounded(self):
        """JSON output should be reasonably bounded."""
        result = generate_proposal_set("restart alpha subsystem gracefully")
        json_output = proposal_set_to_json(result)
        # Should be well under 10KB for any valid output
        self.assertLess(len(json_output), 10000)


class TestWhitespaceSemantics(unittest.TestCase):
    """Test whitespace handling semantics."""

    def test_empty_string_preserved(self):
        """Empty string input must produce input.raw == '' and proposals == []."""
        result = generate_proposal_set("")

        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["input"]["raw"], "")
        self.assertEqual(result["proposals"], [])

    def test_whitespace_only_preserved(self):
        """Whitespace-only input must be preserved exactly in input.raw."""
        whitespace_inputs = ["   ", "\t", "\n", "  \t\n  "]

        for ws in whitespace_inputs:
            with self.subTest(input=repr(ws)):
                result = generate_proposal_set(ws)

                self.assertEqual(result["input"]["raw"], ws)
                self.assertEqual(result["proposals"], [])

    def test_input_not_trimmed_in_output(self):
        """Input with leading/trailing whitespace must preserve exact content."""
        test_input = "  restart alpha subsystem gracefully  "
        result = generate_proposal_set(test_input)

        self.assertEqual(result["input"]["raw"], test_input)


class TestValidation(unittest.TestCase):
    """Test schema validation."""

    def test_generator_output_always_validates(self):
        """Output from generate_proposal_set must always pass validation."""
        test_cases = [
            "",
            "   ",
            "restart alpha subsystem gracefully",
            "status of beta",
            "unknown command",
            "a" * 5000,  # overlong
        ]

        for test_input in test_cases:
            with self.subTest(input=repr(test_input[:50])):
                result = generate_proposal_set(test_input)
                is_valid, errors = validate_proposal_set(result)
                self.assertTrue(is_valid, f"Validation failed: {errors}")

    def test_malformed_output_fails_validation(self):
        """Intentionally malformed ProposalSet must fail validation."""
        malformed_cases = [
            # Missing schema_version
            {"input": {"raw": ""}, "proposals": []},
            # Wrong schema_version
            {"schema_version": "wrong", "input": {"raw": ""}, "proposals": []},
            # Missing input
            {"schema_version": SCHEMA_VERSION, "proposals": []},
            # Missing proposals
            {"schema_version": SCHEMA_VERSION, "input": {"raw": ""}},
            # Extra fields
            {"schema_version": SCHEMA_VERSION, "input": {"raw": ""}, "proposals": [], "extra": 1},
            # Invalid proposal kind
            {"schema_version": SCHEMA_VERSION, "input": {"raw": ""}, "proposals": [
                {"kind": "INVALID", "payload": {"intent": "RESTART_SUBSYSTEM", "slots": {}}}
            ]},
            # Invalid intent
            {"schema_version": SCHEMA_VERSION, "input": {"raw": ""}, "proposals": [
                {"kind": "ROUTE_CANDIDATE", "payload": {"intent": "INVALID", "slots": {}}}
            ]},
        ]

        for malformed in malformed_cases:
            with self.subTest(data=str(malformed)[:80]):
                is_valid, errors = validate_proposal_set(malformed)
                self.assertFalse(is_valid, f"Expected validation failure for: {malformed}")

    def test_validate_and_normalize_handles_invalid(self):
        """validate_and_normalize must return empty ProposalSet for invalid input."""
        malformed = {"garbage": True}
        result = validate_and_normalize(malformed)

        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["proposals"], [])
        self.assertIn("errors", result)
        self.assertGreater(len(result["errors"]), 0)


class TestProposalGeneration(unittest.TestCase):
    """Test proposal generation for known command patterns."""

    def test_restart_graceful_produces_proposal(self):
        """Valid restart command must produce one ROUTE_CANDIDATE proposal."""
        result = generate_proposal_set("restart alpha subsystem gracefully")

        self.assertEqual(len(result["proposals"]), 1)
        proposal = result["proposals"][0]
        self.assertEqual(proposal["kind"], "ROUTE_CANDIDATE")
        self.assertEqual(proposal["payload"]["intent"], "RESTART_SUBSYSTEM")
        self.assertEqual(proposal["payload"]["slots"]["target"], "alpha")
        self.assertEqual(proposal["payload"]["slots"]["mode"], "graceful")

    def test_status_query_produces_proposal(self):
        """Valid status query must produce one ROUTE_CANDIDATE proposal."""
        result = generate_proposal_set("status of beta")

        self.assertEqual(len(result["proposals"]), 1)
        proposal = result["proposals"][0]
        self.assertEqual(proposal["kind"], "ROUTE_CANDIDATE")
        self.assertEqual(proposal["payload"]["intent"], "STATUS_QUERY")
        self.assertEqual(proposal["payload"]["slots"]["target"], "beta")

    def test_unknown_input_produces_zero_proposals(self):
        """Unmapped input must produce zero proposals (not fallback)."""
        unknown_inputs = [
            "hello world",
            "delete database",
            "restart unknown subsystem",
            "12345",
            "SELECT * FROM users",
        ]

        for test_input in unknown_inputs:
            with self.subTest(input=test_input):
                result = generate_proposal_set(test_input)
                self.assertEqual(result["proposals"], [],
                    f"Expected zero proposals for unknown input: {test_input}")

    def test_case_insensitive_matching(self):
        """Pattern matching must be case-insensitive."""
        variations = [
            "RESTART ALPHA SUBSYSTEM GRACEFULLY",
            "Restart Alpha Subsystem Gracefully",
            "restart alpha subsystem gracefully",
        ]

        results = [generate_proposal_set(v) for v in variations]

        # All should produce proposals
        for v, r in zip(variations, results):
            self.assertEqual(len(r["proposals"]), 1, f"No proposal for: {v}")

        # All should have same proposal content (after normalization)
        first_payload = results[0]["proposals"][0]["payload"]
        for r in results[1:]:
            self.assertEqual(r["proposals"][0]["payload"], first_payload)


class TestNonAuthority(unittest.TestCase):
    """Test that proposals have no authority indicators."""

    def test_no_confidence_scores(self):
        """Proposals must not contain confidence, score, or ranking fields."""
        result = generate_proposal_set("restart alpha subsystem gracefully")

        json_str = proposal_set_to_json(result)
        forbidden_terms = ["confidence", "score", "ranking", "best", "selected", "winner"]

        for term in forbidden_terms:
            self.assertNotIn(term.lower(), json_str.lower(),
                f"Found forbidden authority term '{term}' in output")

    def test_no_accept_reject_in_proposals(self):
        """Proposals must not contain ACCEPT/REJECT status."""
        result = generate_proposal_set("restart alpha subsystem gracefully")

        json_str = proposal_set_to_json(result)
        # Should not have status=ACCEPT or status=REJECT
        self.assertNotIn('"status"', json_str)


class TestAdditionalPropertiesRejection(unittest.TestCase):
    """Test that unknown fields are rejected at all levels (additionalProperties: false)."""

    def test_reject_unknown_root_fields(self):
        """Unknown fields at root level must be rejected."""
        data = {
            "schema_version": SCHEMA_VERSION,
            "input": {"raw": "test"},
            "proposals": [],
            "unknown_field": "should_fail"
        }
        is_valid, errors = validate_proposal_set(data)
        self.assertFalse(is_valid)
        self.assertTrue(any("UNEXPECTED_ROOT_FIELDS" in e for e in errors))

    def test_reject_unknown_input_fields(self):
        """Unknown fields in input object must be rejected."""
        data = {
            "schema_version": SCHEMA_VERSION,
            "input": {"raw": "test", "extra": "bad"},
            "proposals": []
        }
        is_valid, errors = validate_proposal_set(data)
        self.assertFalse(is_valid)
        self.assertTrue(any("UNEXPECTED_INPUT_FIELDS" in e for e in errors))

    def test_reject_unknown_proposal_fields(self):
        """Unknown fields in proposal object must be rejected."""
        data = {
            "schema_version": SCHEMA_VERSION,
            "input": {"raw": "test"},
            "proposals": [{
                "kind": "ROUTE_CANDIDATE",
                "payload": {"intent": "RESTART_SUBSYSTEM", "slots": {"target": "alpha"}},
                "extra_field": "bad"
            }]
        }
        is_valid, errors = validate_proposal_set(data)
        self.assertFalse(is_valid)
        self.assertTrue(any("UNEXPECTED_FIELDS" in e for e in errors))

    def test_reject_unknown_payload_fields(self):
        """Unknown fields in payload object must be rejected."""
        data = {
            "schema_version": SCHEMA_VERSION,
            "input": {"raw": "test"},
            "proposals": [{
                "kind": "ROUTE_CANDIDATE",
                "payload": {
                    "intent": "RESTART_SUBSYSTEM",
                    "slots": {"target": "alpha"},
                    "unknown": "bad"
                }
            }]
        }
        is_valid, errors = validate_proposal_set(data)
        self.assertFalse(is_valid)
        self.assertTrue(any("PAYLOAD_UNEXPECTED_FIELDS" in e for e in errors))

    def test_reject_unknown_slots_fields(self):
        """Unknown fields in slots object must be rejected."""
        data = {
            "schema_version": SCHEMA_VERSION,
            "input": {"raw": "test"},
            "proposals": [{
                "kind": "ROUTE_CANDIDATE",
                "payload": {
                    "intent": "RESTART_SUBSYSTEM",
                    "slots": {"target": "alpha", "unknown_slot": "bad"}
                }
            }]
        }
        is_valid, errors = validate_proposal_set(data)
        self.assertFalse(is_valid)
        self.assertTrue(any("SLOTS_UNEXPECTED_FIELDS" in e for e in errors))


class TestBoundedErrors(unittest.TestCase):
    """Test that error output is bounded."""

    def test_errors_bounded_by_max(self):
        """Error array in normalized output must not exceed MAX_ERRORS."""
        # Create something that will generate many errors
        malformed = {
            "schema_version": "wrong",
            "input": "not_an_object",
            "proposals": "not_an_array",
            "extra1": 1, "extra2": 2, "extra3": 3,
        }
        result = validate_and_normalize(malformed)

        if "errors" in result:
            self.assertLessEqual(len(result["errors"]), MAX_ERRORS)

    def test_validate_and_normalize_bounds_errors(self):
        """validate_and_normalize must truncate errors to MAX_ERRORS."""
        # Construct a case with many validation errors
        many_proposals = [
            {"kind": "INVALID_KIND_" + str(i), "payload": {"intent": "INVALID", "slots": {}}}
            for i in range(20)
        ]
        data = {
            "schema_version": SCHEMA_VERSION,
            "input": {"raw": "test"},
            "proposals": many_proposals
        }
        result = validate_and_normalize(data)

        self.assertEqual(result["proposals"], [])
        self.assertIn("errors", result)
        self.assertLessEqual(len(result["errors"]), MAX_ERRORS)

    def test_error_codes_are_deterministic(self):
        """Error codes must be deterministic (same input = same errors)."""
        malformed = {"garbage": True, "more_garbage": False}

        result1 = validate_and_normalize(malformed)
        result2 = validate_and_normalize(malformed)

        self.assertEqual(result1["errors"], result2["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
