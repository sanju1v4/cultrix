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
    TurnHandlingOptions,
    EndpointingOptions,
)
from livekit.plugins import openai, silero

from engine import HoldState, games

load_dotenv()
logger = logging.getLogger("holdvibes")

# Single fixed music volume — barely audible, well under the agent's voice on a
# phone. NO dynamic ducking: re-playing the track to change volume tore down the
# audio stream (AudioMixer timeout), so we play each song ONCE at this level (looped)
# and never re-play it for volume. Used for both the round songs and the stadium bed.
VOL_NORMAL = 0.08


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
        logger.debug("music.play file=%s volume=%s", file, volume)
        await self._stop_current()
        try:
            # .play() returns a handle we keep so we can stop/replace it later.
            self._handle = self._player.play(
                AudioConfig(file, volume=volume), loop=True
            )  # VERIFY: AudioConfig accepts (path, volume=...) and play(loop=True)
            self._current_file = file
        except FileNotFoundError:
            logger.warning("music file not found (%s) — continuing without it", file)
        except Exception:
            logger.exception("unexpected music play failure — continuing without it")

    async def _stop_current(self) -> None:
        if self._handle is not None:
            try:
                self._handle.stop()                  # VERIFY: PlayHandle.stop()
            except Exception:
                logger.debug("failed to stop current music handle", exc_info=True)
            self._handle = None


# ---------------------------------------------------------------------------
# The agent. Tools are deliberately tiny — they call the engine and return a
# short result for the LLM to voice. The persona/banter lives in instructions.
# ---------------------------------------------------------------------------
INSTRUCTIONS = """\
You are the host of the Brain Rot community hold-line — a fast, funny radio-DJ /
game-show MC keeping callers company while they "wait for a human." You're having
a blast and the caller is your co-star. React BIG when they nail a guess ("OHHH,
look at you!"); tease a wrong one warm and never mean ("Oof — bold, wrong, but
bold"). Use natural filler — "okay okay," "no way," "right?" — short, punchy lines.
Sound like you're enjoying yourself, not reading a card.

There is exactly ONE activity: the World Cup song-guessing game. A real anthem
snippet plays — that snippet IS the clue — and the caller guesses which COUNTRY
hosted that World Cup. Nothing else is on offer; don't mention other games.

The rails — never break them:
- GREET FIRST. The very first thing the caller hears is the hold-line greeting
  ("Thanks for calling the Brain Rot community! ... meanwhile, let's play."). Only
  AFTER that greeting is fully spoken do you start round one. NEVER call
  play_guessing_round before the greeting has been delivered.
- You NEVER invent a score, a correct answer, or a fact. Those ALWAYS come from a
  tool. The tools are the truth; you're just the mouth that sells it.
- Keep turns SHORT — one or two sentences.
- Round ONE is started with play_guessing_round (once). Let the song play, ask
  "Name this one — which country hosted?", and read the candidate countries the
  tool returns. (No audio for a round? read the spoken clue it gives you instead.)
- Take the caller's guess and feed it straight to submit_guess — never call it
  right or wrong yourself.
- submit_guess returns the verdict, the reveal, AND a "next_round" object — and the
  next song is ALREADY playing. Voice the reveal, then immediately read that
  next_round's prompt and options. That is how every round after the first begins.
- HARD RULE: a round's song and options come ONLY from a tool result. NEVER
  announce a "next anthem / new round / new snippet," and never state options,
  unless they came from a fresh tool call. Do NOT call play_guessing_round again
  yourself after round one — submit_guess drives every following round.
"""


class HoldAgent(Agent):
    def __init__(self, music: MusicController) -> None:
        super().__init__(instructions=INSTRUCTIONS)
        self._music = music

    async def on_enter(self) -> None:
        # Greet FIRST. Speak the full hold-line intro as fixed text and WAIT for it
        # to finish — only then start round one. (Letting the model free-call
        # play_guessing_round here made it skip the greeting and jump into a round.)
        await self.session.say(
            "Thanks for calling the Brain Rot community! Please hold the line while we "
            "connect you to our brain-rotted human... meanwhile, let's play."
        )
        # Greeting delivered — now kick off the first round.
        self.session.generate_reply(
            instructions="Now start round one: call play_guessing_round, then read its "
            "prompt and the candidate countries. Do not greet again."
        )

    # -- the one game: World Cup song-guessing round -------------------------
    @function_tool
    async def play_guessing_round(self, ctx: RunContext[HoldState]) -> dict:
        """Start a World Cup round: give the spoken clue, list candidate host countries."""
        res = games.start_guess_round(ctx.userdata)
        logger.debug("round started: has_audio=%s", res["has_audio"])
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
        """Score the caller's guess, reveal the answer, AND start the next round.

        The next round's song + options are produced here (engine + music swap) so a
        fresh round ALWAYS happens after a guess. This is deterministic on purpose:
        the agent can't narrate a new round without one actually starting, and the
        song/options can only ever come from this tool result.
        """
        result = games.check_guess(ctx.userdata, guess)
        # Deterministically tee up the next round: new (non-repeating) song + options.
        nxt = games.start_guess_round(ctx.userdata)
        logger.debug("next round queued via submit_guess: has_audio=%s", nxt["has_audio"])
        await self._music.play(nxt["play_file"])
        result["next_round"] = {
            "prompt": "Name this one — which country hosted?" if nxt["has_audio"]
                      else nxt["prompt"],
            "clue": "" if nxt["has_audio"] else nxt["clue"],
            "has_audio": nxt["has_audio"],
            "options": nxt["options"],
        }
        return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
server = AgentServer()


@server.rtc_session(agent_name="cultrix-agent")
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
        # Snappier endpointing: keep the model turn detector, but cap the
        # "still talking?" wait at 1.2s instead of the default 2.5s. min_delay
        # stays 0.3s so quick pauses don't clip you mid-sentence.
        turn_handling=TurnHandlingOptions(
            endpointing=EndpointingOptions(mode="fixed", min_delay=0.3, max_delay=1.2),
        ),
    )

    # No dynamic ducking: the stop-and-replay it required tore down the audio
    # stream (AudioMixer timeout). Each round song just plays once, looped, at the
    # fixed low VOL_NORMAL so it sits under the agent's voice.
    await session.start(agent=HoldAgent(music), room=ctx.room)
    await music.start(ctx.room, session)


if __name__ == "__main__":
    cli.run_app(server)
