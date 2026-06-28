"""Unit tests for engine/library.py — Track data, MUSIC_LIBRARY, and constants."""

from engine.library import (
    Track,
    MUSIC_LIBRARY,
    DESTINATIONS,
    DEFAULT_BORING,
    BY_ID,
    LANGUAGE_SKINS,
    LanguageSkin,
    DEFAULT_LANGUAGE,
)


class TestTrackDataclass:
    """Verify Track is frozen and has expected fields."""

    def test_track_is_frozen(self):
        t = MUSIC_LIBRARY[1]
        try:
            t.id = "hacked"
            assert False, "Should not allow mutation"
        except AttributeError:
            pass

    def test_track_fields(self):
        t = MUSIC_LIBRARY[1]
        assert hasattr(t, "id")
        assert hasattr(t, "title")
        assert hasattr(t, "region")
        assert hasattr(t, "region_aliases")
        assert hasattr(t, "genre")
        assert hasattr(t, "decade")
        assert hasattr(t, "file")
        assert hasattr(t, "fact")
        assert hasattr(t, "clue")

    def test_default_clue_is_empty_string(self):
        """Track.clue defaults to '' (the DEFAULT_BORING has no clue)."""
        assert DEFAULT_BORING.clue == ""


class TestDefaultBoring:
    """Verify the pre-match bed track."""

    def test_id(self):
        assert DEFAULT_BORING.id == "default_bed"

    def test_region_is_none_marker(self):
        assert DEFAULT_BORING.region == "(none)"

    def test_region_aliases_empty(self):
        assert DEFAULT_BORING.region_aliases == ()

    def test_file_path(self):
        assert DEFAULT_BORING.file == "assets/stadium_bed.ogg"

    def test_fact_nonempty(self):
        assert len(DEFAULT_BORING.fact) > 0


class TestMusicLibrary:
    """Verify MUSIC_LIBRARY list integrity."""

    def test_not_empty(self):
        assert len(MUSIC_LIBRARY) > 0

    def test_first_entry_is_default_boring(self):
        assert MUSIC_LIBRARY[0] is DEFAULT_BORING

    def test_all_entries_are_tracks(self):
        for t in MUSIC_LIBRARY:
            assert isinstance(t, Track)

    def test_unique_ids(self):
        ids = [t.id for t in MUSIC_LIBRARY]
        assert len(ids) == len(set(ids)), "Track IDs must be unique"

    def test_all_have_nonempty_id(self):
        for t in MUSIC_LIBRARY:
            assert t.id, f"Track has empty id: {t}"

    def test_all_have_nonempty_title(self):
        for t in MUSIC_LIBRARY:
            assert t.title, f"Track has empty title: {t.id}"

    def test_all_have_nonempty_region(self):
        for t in MUSIC_LIBRARY:
            assert t.region, f"Track has empty region: {t.id}"

    def test_all_have_nonempty_file(self):
        for t in MUSIC_LIBRARY:
            assert t.file, f"Track has empty file: {t.id}"

    def test_all_have_nonempty_fact(self):
        for t in MUSIC_LIBRARY:
            assert t.fact, f"Track has empty fact: {t.id}"

    def test_region_aliases_are_lowercased(self):
        """All aliases should be lowercase for matching."""
        for t in MUSIC_LIBRARY:
            for alias in t.region_aliases:
                assert alias == alias.lower(), (
                    f"Alias '{alias}' for track {t.id} is not lowercase"
                )

    def test_game_tracks_have_clues(self):
        """Every non-default track should have a non-empty clue."""
        for t in MUSIC_LIBRARY:
            if t.id != "default_bed":
                assert t.clue, f"Track {t.id} has no clue"


class TestDestinations:
    """Verify DESTINATIONS (playable rounds, excluding default bed)."""

    def test_excludes_default_bed(self):
        ids = [t.id for t in DESTINATIONS]
        assert "default_bed" not in ids

    def test_all_are_tracks(self):
        for t in DESTINATIONS:
            assert isinstance(t, Track)

    def test_has_entries(self):
        assert len(DESTINATIONS) >= 9  # 1990-2022 + wavin flag

    def test_subset_of_music_library(self):
        lib_ids = {t.id for t in MUSIC_LIBRARY}
        for t in DESTINATIONS:
            assert t.id in lib_ids


class TestByIdIndex:
    """Verify BY_ID dict maps correctly."""

    def test_all_library_tracks_indexed(self):
        for t in MUSIC_LIBRARY:
            assert t.id in BY_ID
            assert BY_ID[t.id] is t

    def test_length_matches(self):
        assert len(BY_ID) == len(MUSIC_LIBRARY)

    def test_lookup_known_track(self):
        t = BY_ID["wc2010_southafrica"]
        assert t.region == "South Africa"


class TestLanguageSkins:
    """Verify LANGUAGE_SKINS data."""

    def test_contains_expected_languages(self):
        expected = {"en", "de", "pt", "fr", "it", "es"}
        assert set(LANGUAGE_SKINS.keys()) == expected

    def test_all_are_language_skin_instances(self):
        for skin in LANGUAGE_SKINS.values():
            assert isinstance(skin, LanguageSkin)

    def test_skin_is_frozen(self):
        skin = LANGUAGE_SKINS["en"]
        try:
            skin.code = "xx"
            assert False, "Should not allow mutation"
        except AttributeError:
            pass

    def test_skins_have_nonempty_greeting(self):
        for code, skin in LANGUAGE_SKINS.items():
            assert skin.greeting, f"Skin {code} has empty greeting"

    def test_skins_have_nonempty_label(self):
        for code, skin in LANGUAGE_SKINS.items():
            assert skin.label, f"Skin {code} has empty label"

    def test_code_matches_key(self):
        for code, skin in LANGUAGE_SKINS.items():
            assert skin.code == code

    def test_preferred_regions_are_valid(self):
        """Preferred regions should exist in DESTINATIONS."""
        valid_regions = {t.region for t in DESTINATIONS}
        for code, skin in LANGUAGE_SKINS.items():
            for region in skin.preferred_regions:
                assert region in valid_regions, (
                    f"Skin {code} prefers unknown region '{region}'"
                )

    def test_default_language_exists(self):
        assert DEFAULT_LANGUAGE in LANGUAGE_SKINS
