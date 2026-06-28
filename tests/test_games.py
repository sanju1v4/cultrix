"""Unit tests for engine/games.py — deterministic game logic."""

import random
from unittest.mock import patch

from engine.games import (
    _norm,
    has_audio,
    resolve_track,
    set_language,
    start_guess_round,
    check_guess,
    morph_options,
    apply_morph,
    anthem_spec,
    lore_card,
    capture_detail,
    request_handoff,
    AUDIO_DESTINATIONS,
)
from engine.library import (
    MUSIC_LIBRARY,
    DESTINATIONS,
    DEFAULT_BORING,
    BY_ID,
    LANGUAGE_SKINS,
)
from engine.state import HoldState


# =============================================================================
# _norm helper
# =============================================================================
class TestNorm:
    """Test the string normalization helper."""

    def test_lowercases(self):
        assert _norm("ITALY") == "italy"

    def test_strips_whitespace(self):
        assert _norm("  France  ") == "france"

    def test_removes_punctuation(self):
        assert _norm("South-Africa!") == "southafrica"

    def test_preserves_internal_spaces(self):
        assert _norm("South Africa") == "south africa"

    def test_removes_special_chars(self):
        assert _norm("K'naan's") == "knaans"

    def test_empty_string(self):
        assert _norm("") == ""

    def test_only_spaces(self):
        assert _norm("   ") == ""

    def test_mixed_case_with_numbers(self):
        assert _norm("World Cup 2010") == "world cup 2010"


# =============================================================================
# has_audio
# =============================================================================
class TestHasAudio:
    """Test audio file detection (files won't exist in test env)."""

    def test_returns_bool(self):
        result = has_audio(DEFAULT_BORING)
        assert isinstance(result, bool)

    def test_no_audio_in_test_env(self):
        """Without actual .ogg files, has_audio should be False."""
        for t in MUSIC_LIBRARY:
            assert has_audio(t) is False


# =============================================================================
# resolve_track
# =============================================================================
class TestResolveTrack:
    """Test track ID resolution."""

    def test_known_id(self):
        t = resolve_track("wc2010_southafrica")
        assert t.region == "South Africa"

    def test_unknown_id_returns_default_boring(self):
        t = resolve_track("nonexistent_track")
        assert t is DEFAULT_BORING

    def test_empty_string_returns_default_boring(self):
        t = resolve_track("")
        assert t is DEFAULT_BORING

    def test_all_library_ids_resolve(self):
        for track in MUSIC_LIBRARY:
            assert resolve_track(track.id) is track


# =============================================================================
# set_language
# =============================================================================
class TestSetLanguage:
    """Test language switching."""

    def test_sets_language_code(self):
        state = HoldState()
        set_language(state, "de")
        assert state.language == "de"

    def test_returns_greeting(self):
        state = HoldState()
        result = set_language(state, "fr")
        assert "greeting" in result
        assert len(result["greeting"]) > 0

    def test_returns_language_label(self):
        state = HoldState()
        result = set_language(state, "it")
        assert result["language"] == "Italiano"

    def test_unknown_language_falls_back_to_english(self):
        state = HoldState()
        result = set_language(state, "zz")
        assert state.language == "en"
        assert result["language"] == "English"

    def test_sets_current_track(self):
        state = HoldState()
        set_language(state, "en")
        assert state.current_track_id != "opus1"  # changed from default

    def test_german_biases_toward_germany(self):
        """German should prefer Germany-related tracks."""
        random.seed(42)
        state = HoldState()
        result = set_language(state, "de")
        # The track should be Germany-related since German has preferred_regions
        track = BY_ID[result["now_playing_id"]]
        assert track.region == "Germany"

    def test_portuguese_biases_toward_brazil(self):
        random.seed(42)
        state = HoldState()
        result = set_language(state, "pt")
        track = BY_ID[result["now_playing_id"]]
        assert track.region == "Brazil"

    def test_result_has_expected_keys(self):
        state = HoldState()
        result = set_language(state, "en")
        expected_keys = {"language", "greeting", "now_playing_id",
                         "now_playing_title", "play_file"}
        assert set(result.keys()) == expected_keys

    def test_truncates_to_two_chars(self):
        state = HoldState()
        set_language(state, "deutsch")  # should use first 2 chars "de"
        assert state.language == "de"


# =============================================================================
# start_guess_round
# =============================================================================
class TestStartGuessRound:
    """Test the guessing round initialization."""

    def test_returns_options(self):
        random.seed(1)
        state = HoldState()
        result = start_guess_round(state)
        assert "options" in result
        assert len(result["options"]) > 0

    def test_default_four_options(self):
        random.seed(1)
        state = HoldState()
        result = start_guess_round(state)
        assert len(result["options"]) == 4

    def test_custom_n_options(self):
        random.seed(1)
        state = HoldState()
        result = start_guess_round(state, n_options=3)
        assert len(result["options"]) == 3

    def test_sets_pending_answer(self):
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        assert state.pending_answer_id is not None
        assert state.pending_answer_id in BY_ID

    def test_answer_region_in_options(self):
        """The correct answer must appear in the options list."""
        random.seed(1)
        state = HoldState()
        result = start_guess_round(state)
        answer = BY_ID[state.pending_answer_id]
        assert answer.region in result["options"]

    def test_options_are_distinct(self):
        """All options should be unique country names."""
        random.seed(1)
        state = HoldState()
        result = start_guess_round(state)
        assert len(result["options"]) == len(set(result["options"]))

    def test_updates_current_track_id(self):
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        assert state.current_track_id == state.pending_answer_id

    def test_updates_last_track_id(self):
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        assert state.last_track_id == state.pending_answer_id

    def test_no_repeat_next_round(self):
        """Consecutive rounds should not pick the same track."""
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        first_track = state.pending_answer_id
        # Clear pending for next round
        state.pending_answer_id = None
        start_guess_round(state)
        second_track = state.pending_answer_id
        # With enough tracks in the pool, should differ
        assert first_track != second_track

    def test_returns_play_file(self):
        random.seed(1)
        state = HoldState()
        result = start_guess_round(state)
        assert "play_file" in result
        assert result["play_file"].endswith(".ogg")

    def test_returns_prompt(self):
        random.seed(1)
        state = HoldState()
        result = start_guess_round(state)
        assert "prompt" in result
        assert len(result["prompt"]) > 0

    def test_no_audio_gives_text_clue(self):
        """Without audio files, the result should include a text clue."""
        random.seed(1)
        state = HoldState()
        result = start_guess_round(state)
        # Since no .ogg files exist in test env, has_audio is False
        assert result["has_audio"] is False
        assert result["clue"] != ""

    def test_has_audio_key(self):
        random.seed(1)
        state = HoldState()
        result = start_guess_round(state)
        assert "has_audio" in result

    def test_result_has_expected_keys(self):
        random.seed(1)
        state = HoldState()
        result = start_guess_round(state)
        expected = {"prompt", "clue", "has_audio", "options", "play_file", "play_title"}
        assert set(result.keys()) == expected


# =============================================================================
# check_guess
# =============================================================================
class TestCheckGuess:
    """Test guess validation and scoring."""

    def test_correct_guess_exact_region(self):
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        answer = BY_ID[state.pending_answer_id]
        result = check_guess(state, answer.region)
        assert result["correct"] is True

    def test_correct_guess_via_alias(self):
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        answer = BY_ID[state.pending_answer_id]
        if answer.region_aliases:
            result = check_guess(state, answer.region_aliases[0])
            assert result["correct"] is True

    def test_correct_guess_case_insensitive(self):
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        answer = BY_ID[state.pending_answer_id]
        result = check_guess(state, answer.region.upper())
        assert result["correct"] is True

    def test_wrong_guess(self):
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        result = check_guess(state, "Atlantis")
        assert result["correct"] is False

    def test_increments_score_on_correct(self):
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        answer = BY_ID[state.pending_answer_id]
        check_guess(state, answer.region)
        assert state.score == 1

    def test_no_score_on_wrong(self):
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        check_guess(state, "Atlantis")
        assert state.score == 0

    def test_increments_rounds_played(self):
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        check_guess(state, "anything")
        assert state.rounds_played == 1

    def test_clears_pending_answer(self):
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        check_guess(state, "anything")
        assert state.pending_answer_id is None

    def test_clears_pending_options(self):
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        check_guess(state, "anything")
        assert state.pending_options == []

    def test_no_round_active_error(self):
        state = HoldState()
        result = check_guess(state, "Italy")
        assert result == {"error": "no_round_active"}

    def test_returns_fact(self):
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        result = check_guess(state, "anything")
        assert "fact" in result
        assert len(result["fact"]) > 0

    def test_returns_answer_region(self):
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        answer = BY_ID[state.pending_answer_id]
        result = check_guess(state, "anything")
        assert result["answer_region"] == answer.region

    def test_returns_score_and_rounds(self):
        random.seed(1)
        state = HoldState()
        start_guess_round(state)
        result = check_guess(state, "anything")
        assert "score" in result
        assert "rounds" in result
        assert result["rounds"] == 1

    def test_multiple_rounds_scoring(self):
        random.seed(1)
        state = HoldState()

        # Round 1: correct
        start_guess_round(state)
        answer1 = BY_ID[state.pending_answer_id]
        check_guess(state, answer1.region)

        # Round 2: wrong
        start_guess_round(state)
        check_guess(state, "Neverland")

        # Round 3: correct
        start_guess_round(state)
        answer3 = BY_ID[state.pending_answer_id]
        result = check_guess(state, answer3.region)

        assert state.score == 2
        assert state.rounds_played == 3
        assert result["score"] == 2
        assert result["rounds"] == 3


# =============================================================================
# morph_options
# =============================================================================
class TestMorphOptions:
    """Test morph options listing."""

    def test_returns_current_id(self):
        state = HoldState()
        state.current_track_id = "wc2010_southafrica"
        result = morph_options(state)
        assert result["current_id"] == "wc2010_southafrica"

    def test_returns_options_list(self):
        state = HoldState()
        result = morph_options(state)
        assert "options" in result
        assert len(result["options"]) == len(DESTINATIONS)

    def test_options_have_expected_keys(self):
        state = HoldState()
        result = morph_options(state)
        for opt in result["options"]:
            assert "id" in opt
            assert "title" in opt
            assert "genre" in opt


# =============================================================================
# apply_morph
# =============================================================================
class TestApplyMorph:
    """Test free-text morph resolution."""

    def test_match_brazil(self):
        state = HoldState()
        result = apply_morph(state, "brazil")
        assert result["matched"] == "wc2014_brazil"

    def test_match_italy(self):
        state = HoldState()
        result = apply_morph(state, "italy")
        assert result["matched"] == "wc1990_italy"

    def test_match_france(self):
        state = HoldState()
        result = apply_morph(state, "france")
        assert result["matched"] == "wc1998_france"

    def test_match_germany(self):
        state = HoldState()
        result = apply_morph(state, "germany")
        assert result["matched"] == "wc2006_germany"

    def test_updates_current_track(self):
        state = HoldState()
        apply_morph(state, "brazil")
        assert state.current_track_id == "wc2014_brazil"

    def test_no_match_picks_random(self):
        """Unresolvable style still returns a valid track."""
        random.seed(1)
        state = HoldState()
        result = apply_morph(state, "xyzzy nonsense")
        assert result["matched"] in BY_ID

    def test_returns_expected_keys(self):
        state = HoldState()
        result = apply_morph(state, "brazil")
        expected = {"matched", "title", "genre", "fact", "play_file"}
        assert set(result.keys()) == expected

    def test_case_insensitive(self):
        state = HoldState()
        result = apply_morph(state, "BRAZIL")
        assert result["matched"] == "wc2014_brazil"

    def test_match_via_alias(self):
        state = HoldState()
        result = apply_morph(state, "korea")
        assert result["matched"] == "wc2002_koreajapan"

    def test_empty_style_picks_random(self):
        random.seed(1)
        state = HoldState()
        result = apply_morph(state, "")
        assert result["matched"] in BY_ID


# =============================================================================
# anthem_spec
# =============================================================================
class TestAnthemSpec:
    """Test anthem specification generation."""

    def test_returns_language(self):
        state = HoldState()
        state.language = "en"
        result = anthem_spec(state, "waiting on hold")
        assert result["language"] == "English"

    def test_returns_four_lines(self):
        state = HoldState()
        result = anthem_spec(state, "topic")
        assert result["lines"] == 4

    def test_returns_aabb_rhyme(self):
        state = HoldState()
        result = anthem_spec(state, "topic")
        assert result["rhyme"] == "AABB"

    def test_must_mention_topic(self):
        state = HoldState()
        result = anthem_spec(state, "a broken heat pump")
        assert result["must_mention"] == "a broken heat pump"

    def test_max_words_per_line(self):
        state = HoldState()
        result = anthem_spec(state, "topic")
        assert result["max_words_per_line"] == 8

    def test_tone(self):
        state = HoldState()
        result = anthem_spec(state, "topic")
        assert "cheeky" in result["tone"]

    def test_respects_state_language(self):
        state = HoldState()
        state.language = "de"
        result = anthem_spec(state, "topic")
        assert result["language"] == "Deutsch"

    def test_unknown_language_falls_back(self):
        state = HoldState()
        state.language = "xx"
        result = anthem_spec(state, "topic")
        assert result["language"] == "English"


# =============================================================================
# lore_card
# =============================================================================
class TestLoreCard:
    """Test hold lore factoid generation."""

    def test_returns_fact(self):
        state = HoldState()
        result = lore_card(state)
        assert "fact" in result
        assert len(result["fact"]) > 0

    def test_fact_is_default_boring_fact(self):
        state = HoldState()
        result = lore_card(state)
        assert result["fact"] == DEFAULT_BORING.fact


# =============================================================================
# capture_detail
# =============================================================================
class TestCaptureDetail:
    """Test detail capture for the productive-beat mechanic."""

    def test_captures_key_value(self):
        state = HoldState()
        capture_detail(state, "order number", "DE-4471")
        assert state.captured["order number"] == "DE-4471"

    def test_returns_captured_dict(self):
        state = HoldState()
        result = capture_detail(state, "name", "Alice")
        assert result["captured"] == {"name": "Alice"}

    def test_strips_value_whitespace(self):
        state = HoldState()
        capture_detail(state, "email", "  test@x.com  ")
        assert state.captured["email"] == "test@x.com"

    def test_normalizes_kind(self):
        state = HoldState()
        capture_detail(state, "Order Number", "X-1")
        assert "order number" in state.captured

    def test_empty_kind_becomes_note(self):
        state = HoldState()
        capture_detail(state, "", "random info")
        assert "note" in state.captured

    def test_multiple_captures(self):
        state = HoldState()
        capture_detail(state, "name", "Bob")
        capture_detail(state, "ticket", "T-99")
        assert len(state.captured) == 2


# =============================================================================
# request_handoff
# =============================================================================
class TestRequestHandoff:
    """Test human handoff request."""

    def test_sets_handoff_flag(self):
        state = HoldState()
        request_handoff(state)
        assert state.handoff_requested is True

    def test_returns_brief(self):
        state = HoldState()
        result = request_handoff(state)
        assert "brief" in result
        assert len(result["brief"]) > 0

    def test_returns_score(self):
        state = HoldState()
        state.score = 3
        result = request_handoff(state)
        assert result["score"] == 3

    def test_returns_rounds(self):
        state = HoldState()
        state.rounds_played = 5
        result = request_handoff(state)
        assert result["rounds"] == 5

    def test_brief_includes_captured_info(self):
        state = HoldState()
        state.captured = {"name": "Test User"}
        result = request_handoff(state)
        assert "name: Test User" in result["brief"]

    def test_brief_includes_score_when_played(self):
        state = HoldState()
        state.rounds_played = 2
        state.score = 1
        result = request_handoff(state)
        assert "scored 1/2" in result["brief"]


# =============================================================================
# Integration: full game flow
# =============================================================================
class TestGameFlow:
    """End-to-end game flow test."""

    def test_full_game_session(self):
        """Simulate a complete game: language set, 3 rounds, morph, handoff."""
        random.seed(42)
        state = HoldState()

        # Set language
        lang_result = set_language(state, "en")
        assert lang_result["language"] == "English"

        # Round 1: correct guess
        r1 = start_guess_round(state)
        answer1 = BY_ID[state.pending_answer_id]
        g1 = check_guess(state, answer1.region)
        assert g1["correct"] is True
        assert state.score == 1

        # Round 2: wrong guess
        r2 = start_guess_round(state)
        g2 = check_guess(state, "Narnia")
        assert g2["correct"] is False
        assert state.score == 1

        # Round 3: correct via alias
        r3 = start_guess_round(state)
        answer3 = BY_ID[state.pending_answer_id]
        if answer3.region_aliases:
            g3 = check_guess(state, answer3.region_aliases[0])
            assert g3["correct"] is True

        # Morph
        m = apply_morph(state, "brazil")
        assert m["matched"] == "wc2014_brazil"

        # Capture detail and handoff
        capture_detail(state, "order", "ORD-123")
        handoff = request_handoff(state)
        assert state.handoff_requested is True
        assert "order: ORD-123" in handoff["brief"]

    def test_deterministic_with_seed(self):
        """Same seed produces same game sequence."""
        results = []
        for _ in range(2):
            random.seed(99)
            state = HoldState()
            start_guess_round(state)
            results.append(state.pending_answer_id)
        assert results[0] == results[1]
