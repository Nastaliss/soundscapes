import asyncio
import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from soundscapes.exceptions import (
    SongNotLoaded,
    SongAlreadyPlaying,
    SongNotPlaying,
    AlreadyTransitionning,
    BarOutOfBounds,
)
from soundscapes.lib.sound import Player, BarHeartBeat


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_playback(duration=120.0):
    pb = MagicMock()
    pb.duration = duration
    pb.curr_pos = 0.0
    return pb


def _make_ws_manager():
    m = MagicMock()
    m.broadcast = AsyncMock()
    return m


def _make_player(duration=120.0, bpm=120, time_signature=4):
    """Return a Player whose Playback objects are mocked out."""
    mgr = _make_ws_manager()
    with patch("soundscapes.lib.sound.Playback", side_effect=lambda: _make_mock_playback(duration)):
        p = Player(mgr)
        p.set_song("songs/test.mp3", bpm, time_signature)
    return p


# ---------------------------------------------------------------------------
# Player – initialisation & set_song
# ---------------------------------------------------------------------------

class TestPlayerInit:
    def test_player_not_initialized_by_default(self):
        mgr = _make_ws_manager()
        p = Player(mgr)
        assert p.initialized is False

    def test_set_song_marks_initialized(self):
        p = _make_player()
        assert p.initialized is True

    def test_set_song_computes_second_per_bar(self):
        p = _make_player(bpm=120, time_signature=4)
        # 120 bpm / 4 beats = 30 bars per minute = 0.5 bars/s → 2s per bar
        assert p.second_per_bar == pytest.approx(2.0)

    def test_set_song_creates_heartbeat(self):
        p = _make_player()
        assert p.heart_beat is not None

    def test_set_song_resets_transitionning(self):
        p = _make_player()
        p.transitionning = True
        with patch("soundscapes.lib.sound.Playback", side_effect=lambda: _make_mock_playback()):
            p.set_song("songs/test.mp3", 120, 4)
        assert p.transitionning is False


# ---------------------------------------------------------------------------
# Player – play
# ---------------------------------------------------------------------------

class TestPlayerPlay:
    def test_play_raises_if_not_initialized(self):
        mgr = _make_ws_manager()
        p = Player(mgr)
        with pytest.raises(SongNotLoaded):
            p.play(0)

    def test_play_raises_if_already_playing(self):
        p = _make_player()
        p.playing = True
        with pytest.raises(SongAlreadyPlaying):
            p.play(0)

    def test_play_sets_playing_flag(self):
        p = _make_player()
        p.heart_beat.start = MagicMock()
        p.play(0)
        assert p.playing is True

    def test_play_calls_playback_play_and_seek(self):
        p = _make_player()
        p.heart_beat.start = MagicMock()
        p.play(2)
        pb = p.get_current_playback()
        pb.play.assert_called_once()
        pb.seek.assert_called_once_with(p.get_time_of_bar(2))


# ---------------------------------------------------------------------------
# Player – stop / teardown
# ---------------------------------------------------------------------------

class TestPlayerStop:
    def test_stop_stops_both_playbacks(self):
        p = _make_player()
        p.heart_beat.start = MagicMock()
        p.play(0)
        p.stop()
        p.get_current_playback().stop.assert_called()
        assert p.playing is False

    def test_teardown_resets_playing(self):
        p = _make_player()
        p.playing = True
        p.teardown()
        assert p.playing is False


# ---------------------------------------------------------------------------
# Player – transition guards
# ---------------------------------------------------------------------------

class TestPlayerTransitionGuards:
    def test_transition_immediately_raises_if_not_initialized(self):
        mgr = _make_ws_manager()
        p = Player(mgr)
        with pytest.raises(SongNotLoaded):
            p.transition_to_bar_immediately(0)

    def test_transition_immediately_raises_if_not_playing(self):
        p = _make_player()
        with pytest.raises(SongNotPlaying):
            p.transition_to_bar_immediately(0)

    def test_transition_immediately_raises_if_already_transitioning(self):
        p = _make_player()
        p.playing = True
        p.transitionning = True
        with pytest.raises(AlreadyTransitionning):
            p.transition_to_bar_immediately(0)

    def test_transition_immediately_raises_if_bar_out_of_bounds(self):
        p = _make_player(duration=10.0, bpm=120, time_signature=4)
        p.playing = True
        with pytest.raises(BarOutOfBounds):
            p.transition_to_bar_immediately(9999)

    def test_transition_on_next_bar_raises_if_not_initialized(self):
        mgr = _make_ws_manager()
        p = Player(mgr)
        with pytest.raises(SongNotLoaded):
            p.transition_to_bar_on_next_bar(0)

    def test_transition_on_next_bar_raises_if_not_playing(self):
        p = _make_player()
        with pytest.raises(SongNotPlaying):
            p.transition_to_bar_on_next_bar(0)

    def test_transition_on_next_bar_raises_if_already_transitioning(self):
        p = _make_player()
        p.playing = True
        p.transitionning = True
        with pytest.raises(AlreadyTransitionning):
            p.transition_to_bar_on_next_bar(0)

    def test_transition_on_next_bar_raises_if_bar_out_of_bounds(self):
        p = _make_player(duration=10.0, bpm=120, time_signature=4)
        p.playing = True
        with pytest.raises(BarOutOfBounds):
            p.transition_to_bar_on_next_bar(9999)


# ---------------------------------------------------------------------------
# Player – utility methods
# ---------------------------------------------------------------------------

class TestPlayerUtilities:
    def test_get_time_of_bar(self):
        p = _make_player(bpm=120, time_signature=4)
        assert p.get_time_of_bar(3) == pytest.approx(6.0)

    def test_get_total_bars(self):
        p = _make_player(duration=120.0, bpm=120, time_signature=4)
        assert p.get_total_bars() == pytest.approx(60.0)

    def test_get_duration(self):
        p = _make_player(duration=42.0)
        assert p.get_duration() == 42.0

    def test_get_current_and_standby_playback_differ(self):
        p = _make_player()
        assert p.get_current_playback() is not p.get_standby_playback()

    def test_get_bar_count_for_current_playback(self):
        p = _make_player(bpm=120, time_signature=4)
        p.get_current_playback().curr_pos = 4.0  # 4s / 2s per bar = 2 bars
        assert p.get_bar_count_for_current_playback() == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Player – callbacks
# ---------------------------------------------------------------------------

class TestPlayerCallbacks:
    @pytest.mark.asyncio
    async def test_on_new_bar_broadcasts(self):
        p = _make_player()
        await p.on_new_bar(3)
        p.ws_manager.broadcast.assert_awaited_once()
        msg = json.loads(p.ws_manager.broadcast.call_args[0][0])
        assert msg == {"type": "bar", "bar": 3, "subBar": 0}

    @pytest.mark.asyncio
    async def test_on_new_sub_bar_broadcasts(self):
        p = _make_player()
        await p.on_new_sub_bar(2, 1)
        msg = json.loads(p.ws_manager.broadcast.call_args[0][0])
        assert msg == {"type": "bar", "bar": 2, "subBar": 1}

    @pytest.mark.asyncio
    async def test_on_end_broadcasts_and_stops_playing(self):
        p = _make_player()
        p.playing = True
        await p.on_end()
        assert p.playing is False
        msg = json.loads(p.ws_manager.broadcast.call_args[0][0])
        assert msg == {"type": "end"}


# ---------------------------------------------------------------------------
# BarHeartBeat
# ---------------------------------------------------------------------------

class TestBarHeartBeat:
    def test_init_stores_interval(self):
        hb = BarHeartBeat(
            hear_beat_interval=2.0,
            manager=_make_ws_manager(),
            on_new_bar=AsyncMock(),
            on_new_sub_bar=AsyncMock(),
            on_end=AsyncMock(),
            sub_bar_count=4,
            song_duration=60.0,
        )
        assert hb.heart_beat_interval == 2.0
        assert hb.counter == 0

    def test_set_bar(self):
        hb = BarHeartBeat(
            hear_beat_interval=2.0,
            manager=_make_ws_manager(),
            on_new_bar=AsyncMock(),
            on_new_sub_bar=AsyncMock(),
            on_end=AsyncMock(),
            sub_bar_count=4,
            song_duration=60.0,
        )
        hb.set_bar(5)
        assert hb.counter == 5

    def test_stop_resets(self):
        hb = BarHeartBeat(
            hear_beat_interval=2.0,
            manager=_make_ws_manager(),
            on_new_bar=AsyncMock(),
            on_new_sub_bar=AsyncMock(),
            on_end=AsyncMock(),
            sub_bar_count=4,
            song_duration=60.0,
        )
        hb.counter = 10
        hb.run = True
        hb.stop()
        assert hb.counter == 0
        assert hb.run is False

    @pytest.mark.asyncio
    async def test_emit_beat_does_nothing_when_stopped(self):
        on_bar = AsyncMock()
        hb = BarHeartBeat(
            hear_beat_interval=2.0,
            manager=_make_ws_manager(),
            on_new_bar=on_bar,
            on_new_sub_bar=AsyncMock(),
            on_end=AsyncMock(),
            sub_bar_count=4,
            song_duration=60.0,
        )
        hb.run = False
        await hb._emit_beat()
        on_bar.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_emit_beat_calls_on_new_bar_when_running(self):
        on_bar = AsyncMock()
        hb = BarHeartBeat(
            hear_beat_interval=2.0,
            manager=_make_ws_manager(),
            on_new_bar=on_bar,
            on_new_sub_bar=AsyncMock(),
            on_end=AsyncMock(),
            sub_bar_count=4,
            song_duration=60.0,
        )
        hb.run = True
        hb.counter = 3
        await hb._emit_beat()
        on_bar.assert_awaited_once_with(3)

    @pytest.mark.asyncio
    async def test_emit_sub_beat_does_nothing_when_stopped(self):
        on_sub = AsyncMock()
        hb = BarHeartBeat(
            hear_beat_interval=2.0,
            manager=_make_ws_manager(),
            on_new_bar=AsyncMock(),
            on_new_sub_bar=on_sub,
            on_end=AsyncMock(),
            sub_bar_count=4,
            song_duration=60.0,
        )
        hb.run = False
        await hb._emit_sub_beat(1)
        on_sub.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_beat_calls_on_end_when_song_over(self):
        on_end = AsyncMock()
        hb = BarHeartBeat(
            hear_beat_interval=2.0,
            manager=_make_ws_manager(),
            on_new_bar=AsyncMock(),
            on_new_sub_bar=AsyncMock(),
            on_end=on_end,
            sub_bar_count=4,
            song_duration=4.0,
        )
        hb.run = True
        hb.counter = 2  # 2 * 2.0 = 4.0 >= 4.0 → song ended
        await hb._beat()
        on_end.assert_awaited_once()
        assert hb.run is False
