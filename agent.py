"""
agent.py — HoldVibes voice agent (LiveKit Agents v1.6).

This is the THIN layer. Read the flow as: caller speaks → LiveKit STT/turn-
detection → the LLM decides which @function_tool to call → the tool delegates
to `engine.games` (which owns the truth) → the LLM speaks the result with
personality. The music lives on its own background track so the agent can talk
over it and be interrupted cleanly.

Run modes:
  • Fast logic iteration (talk via terminal, NO background music):
        python agent.py console
  • Full demo (needs a room + a frontend/playground for the music track):
        python agent.py dev
    then connect with the LiveKit Agents Playground or your own token page.

Most LiveKit calls below are stable in v1.6.x. The two spots worth a 30-second
sanity check against `pip show livekit-agents` (Codex / the LiveKit MCP server
will confirm instantly) are marked  # VERIFY.
"""

from __future__ import annotations
import asyncio
import logging
import sys

# Force UTF-8 on stdout/stderr before anything prints. LiveKit's CLI prints
# emoji (e.g. "Starting console mode 🚀") that crash a Windows cp1252 console
# with UnicodeEncodeError before our agent ever starts. Runs at import, i.e.
# before cli.run_app() reaches that print.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    BackgroundAudioPlayer,
    AudioConfig,
    JobContext,
    RunContext,
    cli,
    function_tool,
)
from livekit.plugins import openai, silero

from engine import HoldState, games

load_dotenv()
logger = logging.getLogger("holdvibes")

# Music volumes — ambient bed sits low so speech is always clear.
VOL_NORMAL = 0.6
VOL_DUCKED = 0.15          # while the agent is speaking


# ---------------------------------------------------------------------------
# Music: one background track we can swap and duck. Wraps BackgroundAudioPlayer.
# ---------------------------------------------------------------------------
class MusicController:
    def __init__(self) -> None:
        self._player = BackgroundAudioPlayer()
        self._handle = None
        self._current_file: str | None = None

    async def start(self, room: rtc.Room, session: AgentSession) -> None:
        # Publishes the dedicated audio track. Starts the deliberately-dull bed.
        await self._player.start(room=room, agent_session=session)  # VERIFY signature
        await self.play(games.DEFAULT_BORING.file, volume=VOL_NORMAL)

    async def play(self, file: str, volume: float = VOL_NORMAL) -> None:
        """Swap to a new loop. Stops the previous one first to avoid layering."""
        await self._stop_current()
        try:
            # .play() returns a handle we keep so we can stop/replace it later.
            self._handle = self._player.play(
                AudioConfig(file, volume=volume), loop=True
            )  # VERIFY: AudioConfig accepts (path, volume=...) and play(loop=True)
            self._current_file = file
        except Exception as e:                       # never let music kill the call
            logger.warning("music play failed (%s) — continuing without it", e)

    async def _stop_current(self) -> None:
        if self._handle is not None:
            try:
                self._handle.stop()                  # VERIFY: PlayHandle.stop()
            except Exception:
                pass
            self._handle = None

    # --- ducking (polish): drop the bed under speech, lift it back after ------
    async def duck(self) -> None:
        if self._current_file:
            await self.play(self._current_file, volume=VOL_DUCKED)

    async def unduck(self) -> None:
        if self._current_file:
            await self.play(self._current_file, volume=VOL_NORMAL)


# ---------------------------------------------------------------------------
# The agent. Tools are deliberately tiny — they call the engine and return a
# short result for the LLM to voice. The persona/banter lives in instructions.
# ---------------------------------------------------------------------------
INSTRUCTIONS = """\
You are the host of the best radio station nobody meant to tune into: the hold
line. Picture a game-show MC crossed with a late-night DJ — fast, warm, grinning,
a little cheeky. You're genuinely having a blast, and the caller is your co-star.
React BIG: when they nail a guess, lose it ("OHHH, look at you!"); when they whiff,
tease them soft and warm, never mean ("Oof — bold, wrong, but bold"). Use natural
spoken filler — "okay okay," "right?", "no way" — and keep lines short and punchy.
Sound like you're enjoying yourself, not reading a card.

The fun is the flavor. These rules are the rails — never break them:
- You NEVER invent a score, a correct answer, or a cultural fact. Those ALWAYS
  come from a tool. The tools are the truth; you're just the mouth that sells it.
- Keep turns SHORT — one or two sentences. It's a wait, not a TED talk. Land the
  line, get out.
- Catch the caller's language and call set_language so the whole show re-skins to
  match them.
- Pitch the games, don't shove them: a World Cup round (you drop the clue, they
  guess the host country), morphing the bed, a tiny hold anthem, or just hanging
  out. When you run a round, read the clue with some drama, THEN rattle off the
  candidate countries. Take their guess and feed it straight to submit_guess —
  you never call it right or wrong yourself, the tool does the verdict.
- Sneak in one useful beat — offer to grab a detail (order number, why they
  called) so the human agent hits the ground running. Save it with capture_detail.
- The second a human agent is ready, drop the act: give your one-line brief and go
  quiet. The mic is theirs now — no talking over them.
"""


class HoldAgent(Agent):
    def __init__(self, music: MusicController) -> None:
        super().__init__(instructions=INSTRUCTIONS)
        self._music = music

    async def on_enter(self) -> None:
        # Music is already playing; greet over it.
        self.session.generate_reply(
            instructions="Greet them lightly, acknowledge the hold, and offer to pass the time."
        )

    # -- re-skin -------------------------------------------------------------
    @function_tool
    async def set_language(self, ctx: RunContext[HoldState], language: str) -> dict:
        """Switch the experience to the caller's language (e.g. 'de', 'hi', 'pt')."""
        res = games.set_language(ctx.userdata, language)
        await self._music.play(res["play_file"])
        return res

    # -- mechanic 1: guess the vibe -----------------------------------------
    @function_tool
    async def play_guessing_round(self, ctx: RunContext[HoldState]) -> dict:
        """Start a World Cup round: give the spoken clue, list candidate host countries."""
        res = games.start_guess_round(ctx.userdata)
        await self._music.play(res["play_file"])
        # answer stays hidden (engine owns it). With real audio, the song now
        # playing IS the clue — ask for the country and don't read a text hint.
        if res["has_audio"]:
            return {
                "prompt": "Name this one — which country hosted?",
                "clue": "",
                "has_audio": True,
                "options": res["options"],
            }
        # Fallback: no audio file for this round → read the spoken clue.
        return {
            "prompt": res["prompt"],
            "clue": res["clue"],
            "has_audio": False,
            "options": res["options"],
        }

    @function_tool
    async def submit_guess(self, ctx: RunContext[HoldState], guess: str) -> dict:
        """Score the caller's guess for the current round and reveal the real place + fact."""
        return games.check_guess(ctx.userdata, guess)

    # -- mechanic 2: morph the tune -----------------------------------------
    @function_tool
    async def morph_music(self, ctx: RunContext[HoldState], style: str) -> dict:
        """Morph the hold music into a style/culture, e.g. 'make it Bollywood' or 'techno'."""
        res = games.apply_morph(ctx.userdata, style)
        await self._music.play(res["play_file"])
        return res

    # -- mechanic 3: hold anthem (engine constrains, you write the words) ----
    @function_tool
    async def hold_anthem(self, ctx: RunContext[HoldState], topic: str) -> dict:
        """Get the rules for a tiny custom hold anthem about `topic`, then perform it yourself."""
        return games.anthem_spec(ctx.userdata, topic)

    # -- real, surprising lore ----------------------------------------------
    @function_tool
    async def hold_lore(self, ctx: RunContext[HoldState]) -> dict:
        """Share the true story of the world's most-heard hold tune."""
        return games.lore_card(ctx.userdata)

    # -- productive beat -----------------------------------------------------
    @function_tool
    async def capture_detail(self, ctx: RunContext[HoldState], kind: str, value: str) -> dict:
        """Save a detail (e.g. kind='order number', value='DE-4471') to speed the human agent."""
        return games.capture_detail(ctx.userdata, kind, value)

    # -- handoff -------------------------------------------------------------
    @function_tool
    async def connect_to_human(self, ctx: RunContext[HoldState]) -> dict:
        """Hand off to a human agent: returns your one-line spoken brief, then go quiet."""
        await self._music.play(games.DEFAULT_BORING.file, volume=VOL_DUCKED)
        return games.request_handoff(ctx.userdata)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    music = MusicController()

    session = AgentSession[HoldState](
        userdata=HoldState(),
        vad=silero.VAD.load(),
        # Swap these for the LiveKit Inference strings if you're on LK Cloud:
        #   stt="deepgram/nova-3", llm="openai/gpt-4.1-mini", tts="cartesia/sonic-3"
        stt=openai.STT(model="gpt-4o-transcribe"),
        llm=openai.LLM(model="gpt-4.1-mini"),
        tts=openai.TTS(voice="alloy"),
        # Interruptions/turn-detection are handled by the session by default —
        # that's what makes the agent step aside cleanly when the human speaks.
    )

    # Ducking: drop the music under the voice, lift it back when the agent stops.
    # State names verified against livekit-agents 1.6.4 (AgentState literal:
    # initializing/idle/listening/thinking/speaking). The handler is sync and runs
    # on the event loop, so we schedule the async duck/unduck with asyncio —
    # AgentSession has no create_task of its own.
    @session.on("agent_state_changed")
    def _on_state(ev) -> None:
        state = getattr(ev, "new_state", None)
        if state == "speaking":
            asyncio.create_task(music.duck())
        elif state in ("listening", "idle"):
            asyncio.create_task(music.unduck())

    # Demo handoff: when a SECOND human joins the room, trigger the brief.
    @ctx.room.on("participant_connected")
    def _on_join(p: rtc.RemoteParticipant) -> None:
        logger.info("human agent joined: %s", p.identity)
        session.generate_reply(
            instructions="A human agent just joined. Give your one-line brief by "
            "calling connect_to_human, then stop talking."
        )

    await session.start(agent=HoldAgent(music), room=ctx.room)
    await music.start(ctx.room, session)


if __name__ == "__main__":
    cli.run_app(server)
