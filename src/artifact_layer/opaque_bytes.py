"""
Opaque Proposal Bytes - Mechanical Non-Inspection Boundary

This module provides a wrapper type that makes proposal bytes
opaque by construction. The wrapper:
- Stores bytes internally
- Exposes only to_bytes() for pass-through
- Does NOT implement inspection affordances

This is a freeze-grade mechanical boundary that prevents
accidental inspection of proposal bytes.
"""


class OpaqueProposalBytes:
    """
    Opaque wrapper for proposal bytes.

    This wrapper enforces opacity by construction:
    - No __str__ (prevents accidental string conversion)
    - No decode() (prevents accidental UTF-8 interpretation)
    - No __iter__ (prevents accidental iteration)
    - No __getitem__ (prevents accidental indexing)
    - No __len__ (prevents length-based logic)
    - No __bool__ (prevents truthiness-based logic)
    - No JSON helpers (prevents accidental parsing)

    The ONLY way to access the bytes is via to_bytes(), which
    returns the raw bytes for pass-through to the artifact layer.

    Usage:
        opaque = OpaqueProposalBytes(raw_bytes)
        # ... pass opaque around ...
        raw = opaque.to_bytes()  # Only at artifact layer boundary
    """

    __slots__ = ('_bytes',)

    def __init__(self, data: bytes):
        """
        Initialize with raw bytes.

        Args:
            data: Raw proposal bytes (opaque, not inspected)
        """
        if not isinstance(data, bytes):
            raise TypeError("OpaqueProposalBytes requires bytes")
        object.__setattr__(self, '_bytes', data)

    def to_bytes(self) -> bytes:
        """
        Return the raw bytes for pass-through.

        This is the ONLY method that exposes the internal bytes.
        Use only at the artifact layer boundary.

        Returns:
            The raw proposal bytes.
        """
        return self._bytes

    # === Explicitly disabled affordances ===

    def __str__(self):
        """Disabled: prevents accidental string conversion."""
        raise TypeError(
            "OpaqueProposalBytes does not support str(). "
            "Use to_bytes() at the artifact layer boundary."
        )

    def __repr__(self):
        """Safe repr that does not expose content."""
        return f"OpaqueProposalBytes(<{len(self._bytes)} bytes>)"

    def __iter__(self):
        """Disabled: prevents accidental iteration."""
        raise TypeError(
            "OpaqueProposalBytes does not support iteration. "
            "Use to_bytes() at the artifact layer boundary."
        )

    def __getitem__(self, key):
        """Disabled: prevents accidental indexing."""
        raise TypeError(
            "OpaqueProposalBytes does not support indexing. "
            "Use to_bytes() at the artifact layer boundary."
        )

    def __len__(self):
        """Disabled: prevents length-based logic."""
        raise TypeError(
            "OpaqueProposalBytes does not support len(). "
            "Use to_bytes() at the artifact layer boundary."
        )

    def __bool__(self):
        """Disabled: prevents truthiness-based logic."""
        raise TypeError(
            "OpaqueProposalBytes does not support bool(). "
            "Use to_bytes() at the artifact layer boundary."
        )

    def __eq__(self, other):
        """Disabled: prevents equality-based logic."""
        raise TypeError(
            "OpaqueProposalBytes does not support equality comparison. "
            "Use to_bytes() at the artifact layer boundary."
        )

    def __hash__(self):
        """Disabled: prevents hashing."""
        raise TypeError(
            "OpaqueProposalBytes does not support hashing. "
            "Use to_bytes() at the artifact layer boundary."
        )

    def __setattr__(self, name, value):
        """Disabled: immutable after construction."""
        raise AttributeError(
            "OpaqueProposalBytes is immutable."
        )

    def __delattr__(self, name):
        """Disabled: immutable after construction."""
        raise AttributeError(
            "OpaqueProposalBytes is immutable."
        )
