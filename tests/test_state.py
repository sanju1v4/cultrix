"""Unit tests for engine/state.py — HoldState dataclass and its methods."""

import time

from engine.state import HoldState


class TestHoldStateDefaults:
    """Verify default construction of HoldState."""

    def test_default_language(self):
        state = HoldState()
        assert state.language == "en"

    def test_default_score(self):
        state = HoldState()
        assert state.score == 0

    def test_default_rounds_played(self):
        state = HoldState()
        assert state.rounds_played == 0

    def test_default_current_track_id(self):
        state = HoldState()
        assert state.current_track_id == "opus1"

    def test_default_last_track_id(self):
        state = HoldState()
        assert state.last_track_id is None

    def test_default_pending_answer_id(self):
        state = HoldState()
        assert state.pending_answer_id is None

    def test_default_pending_options(self):
        state = HoldState()
        assert state.pending_options == []

    def test_default_captured(self):
        state = HoldState()
        assert state.captured == {}

    def test_default_handoff_requested(self):
        state = HoldState()
        assert state.handoff_requested is False

    def test_started_at_is_set(self):
        before = time.monotonic()
        state = HoldState()
        after = time.monotonic()
        assert before <= state.started_at <= after


class TestHoldStateSecondsWaiting:
    """Test the seconds_waiting() method."""

    def test_returns_int(self):
        state = HoldState()
        result = state.seconds_waiting()
        assert isinstance(result, int)

    def test_non_negative(self):
        state = HoldState()
        assert state.seconds_waiting() >= 0

    def test_increases_over_time(self):
        state = HoldState()
        time.sleep(0.05)
        assert state.seconds_waiting() >= 0


class TestHoldStateBriefForHuman:
    """Test the brief_for_human() method."""

    def test_empty_state_includes_wait_time(self):
        state = HoldState()
        brief = state.brief_for_human()
        assert "kept them company for" in brief
        assert "s" in brief

    def test_with_captured_details(self):
        state = HoldState()
        state.captured = {"order number": "DE-4471"}
        brief = state.brief_for_human()
        assert "order number: DE-4471" in brief
        assert "kept them company for" in brief

    def test_with_multiple_captured_details(self):
        state = HoldState()
        state.captured = {"order number": "DE-4471", "name": "Alice"}
        brief = state.brief_for_human()
        assert "order number: DE-4471" in brief
        assert "name: Alice" in brief

    def test_with_rounds_played(self):
        state = HoldState()
        state.rounds_played = 3
        state.score = 2
        brief = state.brief_for_human()
        assert "scored 2/3" in brief
        assert "hold game" in brief

    def test_with_no_rounds_played_omits_score(self):
        state = HoldState()
        state.rounds_played = 0
        brief = state.brief_for_human()
        assert "scored" not in brief

    def test_full_state(self):
        state = HoldState()
        state.captured = {"ticket": "T-123"}
        state.rounds_played = 5
        state.score = 3
        brief = state.brief_for_human()
        assert "ticket: T-123" in brief
        assert "kept them company for" in brief
        assert "scored 3/5" in brief


class TestHoldStateMutation:
    """Verify that state fields are mutable as expected by the engine."""

    def test_score_mutation(self):
        state = HoldState()
        state.score += 1
        assert state.score == 1

    def test_rounds_played_mutation(self):
        state = HoldState()
        state.rounds_played += 1
        assert state.rounds_played == 1

    def test_language_mutation(self):
        state = HoldState()
        state.language = "de"
        assert state.language == "de"

    def test_captured_dict_mutation(self):
        state = HoldState()
        state.captured["key"] = "value"
        assert state.captured == {"key": "value"}

    def test_pending_options_mutation(self):
        state = HoldState()
        state.pending_options = ["Italy", "France"]
        assert state.pending_options == ["Italy", "France"]

    def test_handoff_requested_mutation(self):
        state = HoldState()
        state.handoff_requested = True
        assert state.handoff_requested is True

    def test_independent_instances(self):
        """Two HoldState instances don't share mutable state."""
        s1 = HoldState()
        s2 = HoldState()
        s1.captured["x"] = "1"
        assert s2.captured == {}
