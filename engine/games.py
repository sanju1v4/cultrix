"""
games.py — the deterministic core. THIS is the part judges should poke at.

Every outcome that must be *correct* — which track plays, whether a guess is
right, the running score, what a "morph" resolves to — is decided here, with
plain Python. The LLM's only jobs are (1) deciding which of these to call and
(2) phrasing the result with personality. If you remember one architectural
line for the demo: "the model picks the move and does the banter; the engine
owns every fact and every number."

Nothing here imports LiveKit. You can run and unit-test it on its own — and you
should, because a working engine means you have a demo even if the voice glue
is still flaky at 4pm.
"""

from __future__ import annotations
import random
from pathlib import Path

from .library import (
    Track, MUSIC_LIBRARY, BY_ID, DESTINATIONS, DEFAULT_BORING,
    LANGUAGE_SKINS, DEFAULT_LANGUAGE,
)
from .state import HoldState


# Repo root (engine/.. ) so we can resolve a Track's "assets/..." file path.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


# --- helpers -----------------------------------------------------------------
def _norm(s: str) -> str:
    return "".join(ch for ch in s.lower().strip() if ch.isalnum() or ch == " ").strip()


def has_audio(track: Track) -> bool:
    """True when the track's song file really exists on disk (a snippet to play)."""
    return (_PROJECT_ROOT / track.file).is_file()


# Rounds we can run as "play the song, name the country". Falls back to the
# full set (spoken-clue mode) if none of the audio files are present.
AUDIO_DESTINATIONS: list[Track] = [t for t in DESTINATIONS if has_audio(t)]


def resolve_track(track_id: str) -> Track:
    return BY_ID.get(track_id, DEFAULT_BORING)


# --- language re-skin --------------------------------------------------------
def set_language(state: HoldState, language: str) -> dict:
    """Switch the experience's language. Returns the greeting + a biased vibe."""
    code = language.lower()[:2]
    skin = LANGUAGE_SKINS.get(code, LANGUAGE_SKINS[DEFAULT_LANGUAGE])
    state.language = skin.code

    # Bias the *next* vibe toward the language's home region, if we have one.
    pick = None
    if skin.preferred_regions:
        matches = [t for t in DESTINATIONS if t.region in skin.preferred_regions]
        if matches:
            pick = random.choice(matches)
    pick = pick or random.choice(DESTINATIONS)
    state.current_track_id = pick.id

    return {
        "language": skin.label,
        "greeting": skin.greeting,
        "now_playing_id": pick.id,
        "now_playing_title": pick.title,
        "play_file": pick.file,
    }


# --- mechanic 1: Around the World on Hold (guess the vibe) --------------------
def start_guess_round(state: HoldState, n_options: int = 4) -> dict:
    """Pick a destination, start it playing, return options WITHOUT the answer.

    When real audio exists, we draw only from audio-backed rounds and the song
    itself is the clue ("Name this one!"); otherwise we fall back to the full
    set with a spoken text clue.

    Two guarantees for a clean game:
      - options are DISTINCT host countries (no region appears twice), and
      - the answer never repeats the immediately-previous round's track, so the
        song actually changes each round (tracked via state.last_track_id).
    """
    pool = AUDIO_DESTINATIONS or DESTINATIONS
    # Don't replay the previous round's track (unless the pool has only one).
    candidates = [t for t in pool if t.id != state.last_track_id] or pool
    answer = random.choice(candidates)

    # Distractors are DISTINCT host countries, never the answer's own region
    # (two tracks can share a region — e.g. both 2010 songs are "South Africa").
    other_regions = sorted({t.region for t in DESTINATIONS} - {answer.region})
    distractors = random.sample(other_regions, k=min(n_options - 1, len(other_regions)))
    options = [answer.region] + distractors
    random.shuffle(options)

    state.pending_answer_id = answer.id
    state.pending_options = options
    state.current_track_id = answer.id
    state.last_track_id = answer.id        # so the next round won't repeat it

    audio = has_audio(answer)
    return {
        "prompt": "Name this one!" if audio else "From the clue, name the host country.",
        "clue": "" if audio else answer.clue,  # song is the clue when we have audio
        "has_audio": audio,           # let the voice layer skip reading a text clue
        "options": options,           # safe to speak — answer is hidden in state
        "play_file": answer.file,     # swap the bed to this round's real song
        "play_title": answer.title,
    }


def check_guess(state: HoldState, guess: str) -> dict:
    """Grade the in-flight guess. Engine owns correctness + score."""
    if not state.pending_answer_id:
        return {"error": "no_round_active"}

    answer = BY_ID[state.pending_answer_id]
    g = _norm(guess)
    correct = g == _norm(answer.region) or any(g == _norm(a) for a in answer.region_aliases)

    state.rounds_played += 1
    if correct:
        state.score += 1
    state.pending_answer_id = None
    state.pending_options = []

    return {
        "correct": correct,
        "answer_region": answer.region,
        "fact": answer.fact,          # reward them with the real cultural note
        "score": state.score,
        "rounds": state.rounds_played,
    }


# --- mechanic 2: Morph this tune (same wait, different culture) ---------------
def morph_options(state: HoldState) -> dict:
    """What can we morph the current vibe into?"""
    return {
        "current_id": state.current_track_id,
        "options": [{"id": t.id, "title": t.title, "genre": t.genre} for t in DESTINATIONS],
    }


def apply_morph(state: HoldState, style: str) -> dict:
    """Resolve a free-text style ('make it Bollywood') to a real track."""
    s = _norm(style)
    target = None
    for t in DESTINATIONS:
        hay = " ".join([_norm(t.region), _norm(t.genre), _norm(t.title),
                        *[_norm(a) for a in t.region_aliases]])
        if s and s in hay:
            target = t
            break
    if target is None:                # no match → surprise them, still deterministic
        target = random.choice(DESTINATIONS)

    state.current_track_id = target.id
    return {
        "matched": target.id,
        "title": target.title,
        "genre": target.genre,
        "fact": target.fact,
        "play_file": target.file,
    }


# --- mechanic 3: Hold anthem (engine constrains, LLM fills the words) ---------
def anthem_spec(state: HoldState, topic: str) -> dict:
    """
    The engine does NOT write the poem — it writes the *rules* for it, then the
    LLM fills the words in the caller's language. Engine owns: language, length,
    rhyme, the required subject. Model owns: the actual lines + delivery.
    """
    skin = LANGUAGE_SKINS.get(state.language, LANGUAGE_SKINS[DEFAULT_LANGUAGE])
    return {
        "language": skin.label,
        "lines": 4,
        "rhyme": "AABB",
        "must_mention": topic,
        "max_words_per_line": 8,
        "tone": "warm, a little cheeky, never mean",
    }


# --- hold lore (real, true, surprising) --------------------------------------
def lore_card(state: HoldState) -> dict:
    return {"fact": DEFAULT_BORING.fact}


# --- productive beat ----------------------------------------------------------
def capture_detail(state: HoldState, kind: str, value: str) -> dict:
    state.captured[_norm(kind) or "note"] = value.strip()
    return {"captured": dict(state.captured)}


# --- handoff ------------------------------------------------------------------
def request_handoff(state: HoldState) -> dict:
    state.handoff_requested = True
    return {"brief": state.brief_for_human(), "score": state.score,
            "rounds": state.rounds_played}


# --- tiny self-test (run: python -m engine.games) ----------------------------
if __name__ == "__main__":
    random.seed(7)
    st = HoldState()

    print("language switch ->", set_language(st, "de")["greeting"])

    r = start_guess_round(st)
    print("round options ->", r["options"], "| (hidden answer:", st.pending_answer_id, ")")
    right = BY_ID[st.pending_answer_id].region
    res = check_guess(st, right)
    assert res["correct"] and res["score"] == 1, res
    print("correct guess ->", res["answer_region"], "| score", res["score"])

    start_guess_round(st)
    res2 = check_guess(st, "Atlantis")          # nonsense
    assert res2["correct"] is False and res2["rounds"] == 2, res2
    print("wrong guess -> scored", res2["score"], "/", res2["rounds"])

    m = apply_morph(st, "brazil")
    assert m["matched"] == "wc2014_brazil", m
    print("morph 'brazil' ->", m["title"])

    spec = anthem_spec(st, "a broken heat pump")
    print("anthem spec ->", spec["lines"], "lines,", spec["rhyme"], "in", spec["language"])

    capture_detail(st, "order number", "DE-4471")
    print("handoff brief ->", request_handoff(st)["brief"])
    print("\nALL ENGINE CHECKS PASSED ✅")
