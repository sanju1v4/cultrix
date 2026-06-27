# HoldVibes — the hold line that plays a World Cup guessing game

A voice agent for the worst part of any phone call: being on hold. Instead of
elevator music, HoldVibes turns the wait into a fast, friendly **World Cup anthem
guessing game**, hosted by an AI with the energy of a late-night radio DJ.

## The concept

1. You're stuck on hold. A playful host greets you and offers a quick game.
2. The agent **plays a real World Cup anthem snippet** — that snippet *is* the clue.
3. You guess the **host country** of that World Cup.
4. The agent reveals the answer: the real **song, artist, and year**, then keeps score.

The music **ducks down low while the agent talks** so the voice is always clear,
then swells back up between turns.

### The Wavin' Flag trap 🪤

One round is a deliberate trick. It plays K'naan's **"Wavin' Flag"** — which most
people "know" was the 2010 World Cup song. The reveal sets the record straight:
"Wavin' Flag" was the **Coca-Cola promotional anthem**, *not* FIFA's official
World Cup song (that was Shakira's **"Waka Waka"**). The host country is still
South Africa — so the answer can be right even when the trivia surprises you.

## Architecture — why the answers are trustworthy

> **The model picks the move and does the banter; the engine owns every fact and
> every number.**

- **`engine/`** is plain, deterministic Python with no LiveKit imports. It decides
  which track plays, whether a guess is correct, the running score, and every
  spoken fact. You can run and unit-test it on its own.
- **`agent.py`** is a thin voice layer. The LLM's only jobs are (1) choosing which
  engine tool to call and (2) phrasing the result with personality. It never holds
  the score or the hidden answer in its head — that lives in `HoldState`, which is
  attached to the session and mutated only by engine code.

This split means the fun, improvised banter can never corrupt a score or invent a
"fact" — the things that must be correct are decided in code judges can read.

## Project structure

```
agent.py              # LiveKit voice agent: tools, persona, music ducking
engine/
  __init__.py
  library.py          # Track data: the rounds, host answers, clues, reveal facts
  games.py            # Deterministic core: pick round, check guess, score
  state.py            # HoldState: per-call score/answer/captured details
assets/               # .ogg song clips live here (NOT committed — see below)
  .gitkeep
.env.example          # Copy to .env and fill in your keys
requirements.txt
```

## Setup

1. **Python 3.10+**, then install dependencies (a virtualenv is recommended):
   ```bash
   pip install -r requirements.txt
   ```
2. **Keys.** Copy the template and fill it in:
   ```bash
   cp .env.example .env
   ```
   You'll need a **LiveKit** project (URL + API key/secret) and an **OpenAI** key
   (used for STT `gpt-4o-transcribe`, LLM `gpt-4.1-mini`, and TTS `alloy`).
3. **Audio clips.** The `.ogg` song snippets are **not** in the repo (large and
   possibly copyrighted). Drop your own clips into `assets/`. The engine activates
   a round as a "play-the-song" clue **only when its `.ogg` file is present**; the
   currently-wired audio rounds expect:
   - `assets/wc2010_southafrica.ogg` — "Waka Waka" (Shakira)
   - `assets/wc2014_brazil.ogg` — "We Are One" (Pitbull ft. J.Lo)
   - `assets/wc2010_wavinflag.ogg` — "Wavin' Flag" (K'naan) — the trap
   - `assets/stadium_bed.ogg` — the neutral bed before a round starts

   If **no** clips are present, the game still runs — it falls back to spoken text
   clues for the full 1990–2022 set instead of playing audio.

## Running

**Verify the engine first (no audio or network needed):**
```bash
python -m engine.games        # prints "ALL ENGINE CHECKS PASSED ✅"
```

**Talk to it locally (terminal voice, no background music):**
```bash
python agent.py console
```

**Full demo with the music track (needs a room + frontend):**
```bash
python agent.py dev
```
then connect with the [LiveKit Agents Playground](https://agents-playground.livekit.io/)
(or your own token page). Watch the terminal for `registered worker` and, when you
connect, `received job request`.

### Windows note

LiveKit's CLI prints emoji that crash a default `cp1252` Windows console. `agent.py`
already fixes this at startup (it reconfigures `stdout`/`stderr` to UTF-8), so
`python agent.py console` works out of the box. For other scripts (e.g. the engine
self-test's `✅`), force UTF-8:
```powershell
$env:PYTHONIOENCODING='utf-8'; python -m engine.games
```

## Demo script (≈60 seconds)

1. **Greeting.** Agent: *"Stuck on hold? Okay okay — let's play. Quick World Cup round?"*
2. **Round + snippet.** A real anthem plays; the music ducks as the agent speaks:
   *"Name this one — which country hosted? Italy, Brazil, South Africa, or Qatar?"*
3. **Guess + reveal.** You say *"South Africa."* Engine scores it, agent celebrates:
   *"OHHH, yes! That's Shakira's 'Waka Waka,' 2010 — South Africa's first World Cup."*
4. **The trap.** Next snippet is "Wavin' Flag." You confidently say *"That's the 2010
   World Cup song!"* — Agent reveals from the engine: *"Host's right, South Africa —
   but gotcha: 'Wavin' Flag' was Coca-Cola's promo anthem. FIFA's official song was
   'Waka Waka.'"*
5. **(Optional) productive beat.** Agent offers to grab your order number so a human
   picks up faster.

## Also wired (secondary tools)

Beyond the core game, the agent exposes a few extra engine-backed tools the host
can reach for. They follow the same rule — the engine owns the facts:

- **Language re-skin** (`set_language`) — switches the greeting and biases the next
  round toward a caller's language/home region (en/de/pt/fr/it/es).
- **Morph the bed** (`morph_music`) — free-text style ("make it Brazilian") resolves
  deterministically to one of the real tracks.
- **Hold anthem** (`hold_anthem`) — the engine returns the *rules* (language, 4 lines,
  AABB rhyme, required topic); the LLM improvises the words.
- **Hold lore** (`hold_lore`) — a true factual aside for the wait.
- **Human handoff** (`connect_to_human`) — when a second participant joins the room,
  the agent gives a one-line brief (captured details + score) and goes quiet.
