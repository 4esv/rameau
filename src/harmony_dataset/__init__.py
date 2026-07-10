"""Synthetic functional-harmony dataset generator.

Grammar-generated chord progressions with constructive DCML Roman-numeral
labels, verified by a dual-derivation gold gate (music21), framed as multiple
text-to-text tasks. See export.main() for the entry point.
"""
from .vocabulary import Analysis
from .cadence import classify_cadence
from .grammar import generate_phrases
from .generator import build_pool, generate
from .verify import verify_chord

__all__ = ["Analysis", "classify_cadence", "generate_phrases", "build_pool",
           "generate", "verify_chord"]
