"""
library.py — World Cup edition.

The game: the agent gives a spoken CLUE about a World Cup's official song, the
caller guesses the HOST COUNTRY, and the reveal names the real song + artist.

Why clues instead of playing the songs: the official FIFA tracks (Waka Waka,
Cup of Life, ...) are commercial copyrighted recordings. We do NOT play them.
We state facts (year, artist, host) and paraphrase the vibe — facts aren't
copyrightable, and this keeps a public demo clean. The `file` bed is a generic
stadium-ambience loop you make/source yourself, not the real song.

All host/song/artist pairings below were fact-checked. `region` is the answer.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Track:
    id: str
    title: str                       # what the agent calls this round
    region: str                      # THE ANSWER: host country
    region_aliases: tuple[str, ...]  # accepted answers (lowercased match)
    genre: str                       # kept generic for the morph mechanic
    decade: str                      # the year
    file: str                        # generic stadium bed (NOT the real song)
    fact: str                        # the reveal: real song + artist + year
    clue: str = ""                   # the spoken hint, all factual/paraphrased


# Generic bed that plays before a round starts (stadium hum — make your own).
DEFAULT_BORING = Track(
    id="default_bed",
    title="the pre-match wait",
    region="(none)",
    region_aliases=(),
    genre="stadium ambience",
    decade="-",
    file="assets/stadium_bed.ogg",
    fact="Just the hum of the stadium before kickoff.",
    clue="",
)


# --- The rounds (1990-2022 official-song era) --------------------------------
MUSIC_LIBRARY: list[Track] = [
    DEFAULT_BORING,
    Track(
        id="wc1990_italy",
        title="the 1990 World Cup anthem",
        region="Italy",
        region_aliases=("italy", "italia", "italian"),
        genre="anthem",
        decade="1990",
        file="assets/wc1990_italy.ogg",
        fact="1990 - \"Un'estate italiana (To Be Number One)\" by Edoardo Bennato & Gianna Nannini, "
             "with Giorgio Moroder on the English version. By sales, the best-selling World Cup song ever.",
        clue="Nineteen-ninety. 'An Italian summer.' Giorgio Moroder produced the English version, "
             "and by record sales it's still the best-selling World Cup song of all time.",
    ),
    Track(
        id="wc1994_usa",
        title="the 1994 World Cup anthem",
        region="United States",
        region_aliases=("usa", "united states", "america", "us", "u s a", "states"),
        genre="anthem",
        decade="1994",
        file="assets/wc1994_usa.ogg",
        fact="1994 - \"Gloryland\" by Daryl Hall (of Hall & Oates) with Sounds of Blackness. "
             "(Double-check this pairing before stage - it's the least-famous of the set.)",
        clue="Nineteen-ninety-four. A gospel-tinged official song sung by one half of Hall & Oates.",
    ),
    Track(
        id="wc1998_france",
        title="the 1998 World Cup anthem",
        region="France",
        region_aliases=("france", "french", "la france"),
        genre="anthem",
        decade="1998",
        file="assets/wc1998_france.ogg",
        fact="1998 - \"The Cup of Life (La Copa de la Vida)\" by Ricky Martin. "
             "A career-maker that hit number one in some thirty countries.",
        clue="Nineteen-ninety-eight. A Puerto Rican star's breakout - it won a Latin pop Grammy "
             "and topped the charts in about thirty countries.",
    ),
    Track(
        id="wc2002_koreajapan",
        title="the 2002 World Cup anthem",
        region="South Korea and Japan",
        region_aliases=("korea", "south korea", "japan", "korea and japan", "korea/japan",
                        "korea japan", "south korea and japan", "japan and korea"),
        genre="anthem",
        decade="2002",
        file="assets/wc2002_koreajapan.ogg",
        fact="2002 - \"Boom\" by Anastacia (official song), with Vangelis's instrumental \"Anthem\". "
             "The first World Cup held in Asia - and co-hosted by two countries.",
        clue="Two-thousand-two. The first World Cup in Asia, and the only one co-hosted by two "
             "countries. An American pop singer performed the official song, 'Boom'.",
    ),
    Track(
        id="wc2006_germany",
        title="the 2006 World Cup anthem",
        region="Germany",
        region_aliases=("germany", "deutschland", "german"),
        genre="anthem",
        decade="2006",
        file="assets/wc2006_germany.ogg",
        fact="2006 - \"The Time of Our Lives\" by Il Divo & Toni Braxton (official song); "
             "Gronemeyer's \"Zeit, dass sich was dreht\" was the German-language anthem.",
        clue="Two-thousand-six. A swelling power ballad - an operatic quartet paired with an "
             "R&B star, singing about the glory and the pain of the big game.",
    ),
    Track(
        id="wc2010_southafrica",
        title="the 2010 World Cup anthem",
        region="South Africa",
        region_aliases=("south africa", "africa", "rsa", "south-africa"),
        genre="anthem",
        decade="2010",
        file="assets/wc2010_southafrica.ogg",
        fact="2010 - \"Waka Waka (This Time for Africa)\" by Shakira ft. Freshlyground. "
             "The most-streamed World Cup song ever, with billions of views.",
        clue="Twenty-ten. A Colombian superstar teamed up with an Afro-fusion band. 'This time' - "
             "for a whole continent hosting its first World Cup.",
    ),
    Track(
        id="wc2014_brazil",
        title="the 2014 World Cup anthem",
        region="Brazil",
        region_aliases=("brazil", "brasil", "brazilian"),
        genre="anthem",
        decade="2014",
        file="assets/wc2014_brazil.ogg",
        fact="2014 - \"We Are One (Ole Ola)\" by Pitbull ft. Jennifer Lopez & Claudia Leitte. "
             "Shakira also returned that year with \"La La La\".",
        clue="Twenty-fourteen. Mr. Worldwide, J-Lo, and a Brazilian singer over Afro-Latin "
             "rhythms - 'ole ola'.",
    ),
    Track(
        id="wc2018_russia",
        title="the 2018 World Cup anthem",
        region="Russia",
        region_aliases=("russia", "russian", "rossiya"),
        genre="anthem",
        decade="2018",
        file="assets/wc2018_russia.ogg",
        fact="2018 - \"Live It Up\" by Nicky Jam ft. Will Smith & Era Istrefi, "
             "performed at the closing ceremony.",
        clue="Twenty-eighteen. A reggaeton star, Era Istrefi, and Will Smith - performed live at "
             "the closing ceremony.",
    ),
    Track(
        id="wc2022_qatar",
        title="the 2022 World Cup anthem",
        region="Qatar",
        region_aliases=("qatar", "katar", "qatari"),
        genre="anthem",
        decade="2022",
        file="assets/wc2022_qatar.ogg",
        fact="2022 - \"Hayya Hayya (Better Together)\" by Trinidad Cardona, Davido & Aisha - the "
             "lead single of the first-ever multi-song World Cup soundtrack.",
        clue="Twenty-twenty-two. The first World Cup with a whole soundtrack of official songs. "
             "The lead single's title means 'let's go' in Arabic.",
    ),
    Track(
        id="wc2010_wavinflag",
        title="a famous 2010 World Cup song",
        region="South Africa",
        region_aliases=("south africa", "africa", "rsa"),
        genre="anthem",
        decade="2010",
        file="assets/wc2010_wavinflag.ogg",
        fact="2010 - \"Wavin' Flag\" by K'naan was the Coca-Cola PROMOTIONAL anthem for the 2010 "
             "World Cup, NOT the official FIFA World Cup song (that was Shakira's \"Waka Waka\"). "
             "The host nation was still South Africa.",
        clue="Twenty-ten. A Somali-Canadian artist's stadium chant, picked by Coca-Cola for its "
             "global World Cup campaign that year.",
    ),
]

BY_ID: dict[str, Track] = {t.id: t for t in MUSIC_LIBRARY}
DESTINATIONS: list[Track] = [t for t in MUSIC_LIBRARY if t.id != "default_bed"]


# --- Language re-skin (unchanged mechanic; biases the next pick) -------------
@dataclass(frozen=True)
class LanguageSkin:
    code: str
    label: str
    greeting: str
    preferred_regions: tuple[str, ...]


LANGUAGE_SKINS: dict[str, LanguageSkin] = {
    "en": LanguageSkin("en", "English", "Stuck on hold? Let's play a quick World Cup round.", ()),
    "de": LanguageSkin("de", "Deutsch", "Warteschleife? Kurzes WM-Quiz gefaellig?", ("Germany",)),
    "pt": LanguageSkin("pt", "Portugues", "Em espera? Bora jogar um quiz da Copa.", ("Brazil",)),
    "fr": LanguageSkin("fr", "Francais", "En attente? Petit quiz de la Coupe du monde?", ("France",)),
    "it": LanguageSkin("it", "Italiano", "In attesa? Un quiz veloce sui Mondiali?", ("Italy",)),
    "es": LanguageSkin("es", "Espanol", "En espera? Juguemos un quiz del Mundial.", ()),
}
DEFAULT_LANGUAGE = "en"
