# HoldVibes 🎧

**The voice agent that turns hold music into the best part of the call.**

Most people hang up while waiting on hold — and a lot of them were ready to buy.
HoldVibes keeps the caller on the line by turning the dead air into a 60-second
interactive cultural moment, in *their* language, then hands off cleanly the
instant a human is ready.

Built for the telli × LiveKit Voice AI Hack.

---

## The idea in one breath

The hold music stops being something you endure and becomes something you play
with. The caller picks a vibe, the music re-skins to a culture (Berlin techno,
Mumbai filmi, Lagos afrobeat…), the agent drops one true cultural note, and you
can morph the tune on command or get a tiny custom hold-anthem about why you
called. Underneath, it's quietly productive: it grabs your order number so the
human is faster.

## The architecture (say this to the judges)

> **The model picks the move and does the banter; the engine owns every fact
> and every number.**

```
  caller speaks
       │
  LiveKit  (STT · turn-detection · interruptions)   ← the hard real-time stuff
       │
  LLM      decides which tool to call, phrases the reply with personality
       │
  engine/  ← DETERMINISTIC. owns: which track plays, whether a guess is right,
  games.py    the score, what a "morph" resolves to, the anthem's rules.
              No LLM. No hallucinated facts. Unit-tested on its own.
       │
  music    background track on its own channel — agent talks over it & ducks it
```

`engine/` has **zero** LiveKit imports, so it runs and tests standalone. That's
deliberate: a green engine means you have a demo even if the voice glue is still
flaky at 4pm.

```
holdvibes/
├── engine/            # the deterministic core (the part to be proud of)
│   ├── library.py     #   curated vibes + true cultural facts + language skins
│   ├── state.py       #   per-call state (score, pending answer, captured info)
│   └── games.py       #   selection, scoring, morph, anthem spec  ← run this
├── agent.py           # LiveKit glue: session, tools, music control, handoff
├── assets/            # drop your 8 short music loops here (see assets/README)
├── requirements.txt
└── .env.example
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in LIVEKIT_* and OPENAI_API_KEY
# add your loops to assets/  (see assets/README.md)
```

## Run

```bash
# 1) Prove the engine works — no creds, no audio, instant:
python -m engine.games        # -> ALL ENGINE CHECKS PASSED ✅

# 2) Iterate on the conversation fast (terminal mic, NO background music):
python agent.py console

# 3) Full demo (music track needs a real room):
python agent.py dev
#    then connect via the LiveKit Agents Playground or your own token page,
#    and have a teammate join the room to trigger the live handoff.
```

> Background audio is intentionally disabled in `console` mode — use `console`
> for logic, `dev` + a room for the music demo.

---

## The 6-hour battle plan (build risky-first)

Building starts 10:30, demos at 17:00. Order matters — do the thing most likely
to break **first**.

- **10:30–11:30 — Audio spine (the risk).** Get `agent.py dev` up with music
  looping on the background track and the agent able to talk over it *and be
  interrupted*. If this works, you have a demo. Everything else is content.
  → de-risk the three `# VERIFY` spots in `agent.py` here (BackgroundAudioPlayer
    signature, `AudioConfig`/`play(loop=)`, `PlayHandle.stop()`). Ask Codex or
    the LiveKit MCP server; don't burn 40 minutes guessing.
- **11:30–12:30 — The swap.** Wire `morph_music` + `play_guessing_round` so the
  music visibly re-skins on command. The boring→cultural swap is your "whoa".
- **12:30–13:00 — Lunch / let it breathe.**
- **13:00–14:00 — Language re-skin.** `set_language` mid-call → music + greeting
  change together. This is the beat that flatters telli's multilingual moat.
- **14:00–14:45 — Productive beat + handoff.** `capture_detail`, then the
  teammate-joins-room handoff with the spoken brief.
- **14:45–15:30 — Anthem + lore** as bonus mechanics if time allows.
- **15:30–16:15 — Ducking polish + bake the 8 loops** so it sounds good.
- **16:15–17:00 — Rehearse the 90 seconds. Twice.** A clean run beats a
  feature nobody sees.

If you fall behind, cut in this order: anthem → lore → ducking → language.
**Never cut:** music swap, interruption, handoff. Those three *are* the demo.

## The 90-second demo script

1. "Every one of you has rage-quit a hold queue. After two minutes, ~60% hang
   up — and a lot of them were ready to buy." → phone rings, "all agents busy",
   the dull tune starts.
2. Agent pipes up: *"Stuck on hold? I can fix the music. Want to travel?"* →
   **morph to Berlin techno** live. (room reacts)
3. Quick guess-the-vibe round → caller nails it → agent rewards with the real
   cultural fact. *(engine scored that, not the model — mention it.)*
4. Switch to German mid-call → whole thing re-skins. *(telli's exact strength)*
5. *"By the way, grabbed your order number so they're faster."* → teammate
   joins the room → agent gives its one-line brief → goes quiet → handoff.
6. Land it: *"We didn't make a better hold experience. We made one nobody hangs
   up on."*

## Honest gaps to own if asked
- Music is pre-baked, not generated live (a feature, not a bug — faster & better).
- Auto language-detection is light; in the demo you can also just ask. The
  re-skin machinery is the real point.
- Single-call demo, not load-tested — but the engine/voice split is exactly the
  shape that *would* scale.
