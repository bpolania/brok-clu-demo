"""
Run Context - Per-Run State for Seam S Enforcement

This module provides a minimal run context that enforces the
exactly-one-seam-call invariant at runtime.

Frozen Contract:
- Each run creates exactly one RunContext
- Seam S may be called at most once per RunContext
- Second call raises SeamSViolation deterministically
- No retries, no fallbacks, no config
"""


class SeamSViolation(Exception):
    """
    Raised when Seam S invariants are violated.

    This is a deterministic, non-recoverable error indicating
    a structural violation of the seam contract.
    """
    pass


class RunContext:
    """
    Per-run context that enforces Seam S invariants.

    This context must be created once per pipeline run and passed
    to the seam provider. It enforces:
    - Exactly one Seam S call per run
    - Deterministic failure on violation

    Usage:
        ctx = RunContext()
        # ... pass ctx to seam call ...
        # Second call with same ctx raises SeamSViolation
    """

    __slots__ = ('_seam_s_called',)

    def __init__(self):
        self._seam_s_called = False

    def mark_seam_s_called(self) -> None:
        """
        Mark that Seam S has been called.

        Raises:
            SeamSViolation: If Seam S was already called in this run.
        """
        if self._seam_s_called:
            raise SeamSViolation(
                "Seam S may be called exactly once per run. "
                "Second invocation detected."
            )
        self._seam_s_called = True

    @property
    def seam_s_was_called(self) -> bool:
        """Return whether Seam S has been called in this run."""
        return self._seam_s_called
