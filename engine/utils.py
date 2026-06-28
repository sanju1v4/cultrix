"""Shared text-processing utilities used across the engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .library import Track


def normalize_text(s: str) -> str:
    """Lowercase, strip, keep only alphanumerics and spaces."""
    return "".join(ch for ch in s.lower().strip() if ch.isalnum() or ch == " ").strip()


def match_region(guess: str, track: "Track") -> bool:
    """True when *guess* matches the track's host country or any alias."""
    g = normalize_text(guess)
    if g == normalize_text(track.region):
        return True
    return any(g == normalize_text(a) for a in track.region_aliases)
