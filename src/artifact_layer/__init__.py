"""
Artifact Layer - LLM Proposal Engine Integration

This package provides the seam for proposal acquisition.
The seam is the only integration point for probabilistic proposal generation.
"""

from .seam_provider import acquire_proposal_set

__all__ = ["acquire_proposal_set"]
