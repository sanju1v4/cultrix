"""
state.py — the per-call state the engine owns.

This is attached to the LiveKit AgentSession as `userdata`, so every tool call
reads and mutates the SAME object. The agent (LLM) never holds the score or the
correct answer in its head — it lives here, in code we control.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import time


@dataclass
class HoldState:
    language: str = "en"
    score: int = 0
    rounds_played: int = 0

    # The currently playing vibe (Track.id), so morph/guess know the context.
    current_track_id: str = "opus1"

    # The previous round's track, so a new round won't repeat it back-to-back.
    last_track_id: str | None = None

    # An in-flight guessing round: the correct Track.id is stashed here and
    # NEVER sent to the LLM until the guess is checked.
    pending_answer_id: str | None = None
    pending_options: list[str] = field(default_factory=list)

    # The "productive while you wait" beat — details captured to speed the human.
    captured: dict[str, str] = field(default_factory=dict)

    # Handoff bookkeeping.
    handoff_requested: bool = False
    started_at: float = field(default_factory=time.monotonic)

    def seconds_waiting(self) -> int:
        return int(time.monotonic() - self.started_at)

    def brief_for_human(self) -> str:
        """One-line spoken summary the agent gives when a human picks up."""
        bits = []
        if self.captured:
            bits.append(", ".join(f"{k}: {v}" for k, v in self.captured.items()))
        bits.append(f"kept them company for {self.seconds_waiting()}s")
        if self.rounds_played:
            bits.append(f"scored {self.score}/{self.rounds_played} in the hold game")
        return "; ".join(bits)
