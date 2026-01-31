import json
import os
import csv
import tempfile
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from fastapi.testclient import TestClient

from soundscapes.soundscapes import app, manager, ConnectionManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def songs_dir(tmp_path):
    """Create a temporary songs directory with a metadata file and a fake song."""
    meta_path = tmp_path / "metadata.csv"
    with open(meta_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["song_name", "bpm", "time_signature"])
        writer.writeheader()
        writer.writerow({"song_name": "test.mp3", "bpm": "120", "time_signature": "4"})
    # create a dummy song file
    (tmp_path / "test.mp3").write_bytes(b"\x00" * 100)
    return tmp_path


# ---------------------------------------------------------------------------
# ConnectionManager unit tests
# ---------------------------------------------------------------------------

class TestConnectionManager:
    def test_format_message(self):
        cm = ConnectionManager()
        result = json.loads(cm._format_message("response", "hello"))
        assert result == {"type": "response", "message": "hello"}

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        cm = ConnectionManager()
        ws = MagicMock()
        ws.accept = pytest.importorskip("unittest.mock").AsyncMock()
        await cm.connect(ws)
        assert ws in cm.active_connections
        cm.disconnect(ws)
        assert ws not in cm.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self):
        from unittest.mock import AsyncMock
        cm = ConnectionManager()
        ws1, ws2 = MagicMock(), MagicMock()
        ws1.send_text = AsyncMock()
        ws2.send_text = AsyncMock()
        ws1.accept = AsyncMock()
        ws2.accept = AsyncMock()
        await cm.connect(ws1)
        await cm.connect(ws2)
        await cm.broadcast("ping")
        ws1.send_text.assert_awaited_once_with("ping")
        ws2.send_text.assert_awaited_once_with("ping")

    @pytest.mark.asyncio
    async def test_respond_sends_formatted(self):
        from unittest.mock import AsyncMock
        cm = ConnectionManager()
        ws = MagicMock()
        ws.send_text = AsyncMock()
        await cm.respond(ws, "hello")
        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent["type"] == "response"
        assert sent["message"] == "hello"


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------

class TestRootEndpoint:
    def test_get_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Soundscape API" in resp.text


# ---------------------------------------------------------------------------
# /songs – list songs
# ---------------------------------------------------------------------------

class TestGetSongs:
    def test_get_songs(self, client, songs_dir):
        with patch("soundscapes.soundscapes.os.listdir", return_value=["test.mp3", "readme.txt", "track.wav"]):
            resp = client.get("/songs")
        assert resp.status_code == 200
        data = resp.json()
        assert "test.mp3" in data["songs"]
        assert "track.wav" in data["songs"]
        assert "readme.txt" not in data["songs"]


# ---------------------------------------------------------------------------
# /play – play controls
# ---------------------------------------------------------------------------

class TestPlayEndpoint:
    def test_play_without_song_loaded(self, client):
        """Player not initialised → should raise SongNotLoaded (400)."""
        from soundscapes import soundscapes as mod
        original_player = mod.player
        mock_player = MagicMock()
        mock_player.play.side_effect = __import__("soundscapes.exceptions", fromlist=["SongNotLoaded"]).SongNotLoaded()
        mod.player = mock_player
        try:
            resp = client.post("/play", json={"startBar": 0})
            assert resp.status_code == 400
            assert resp.json()["errorCode"] == "no_song_loaded"
        finally:
            mod.player = original_player

    def test_play_success(self, client):
        from soundscapes import soundscapes as mod
        original_player = mod.player
        mock_player = MagicMock()
        mod.player = mock_player
        try:
            resp = client.post("/play", json={"startBar": 0})
            assert resp.status_code == 200
            assert resp.json()["status"] == "playing"
            mock_player.play.assert_called_once_with(0)
        finally:
            mod.player = original_player


# ---------------------------------------------------------------------------
# /stop
# ---------------------------------------------------------------------------

class TestStopEndpoint:
    def test_post_stop(self, client):
        from soundscapes import soundscapes as mod
        original_player = mod.player
        mock_player = MagicMock()
        mod.player = mock_player
        try:
            resp = client.post("/stop")
            assert resp.status_code == 200
            assert resp.json()["status"] == "stopped"
            mock_player.stop.assert_called_once()
        finally:
            mod.player = original_player

    def test_get_stop(self, client):
        from soundscapes import soundscapes as mod
        original_player = mod.player
        mock_player = MagicMock()
        mod.player = mock_player
        try:
            resp = client.get("/stop")
            assert resp.status_code == 200
            assert resp.json()["status"] == "stopped"
        finally:
            mod.player = original_player


# ---------------------------------------------------------------------------
# /transition
# ---------------------------------------------------------------------------

class TestTransitionEndpoint:
    def test_post_transition(self, client):
        from soundscapes import soundscapes as mod
        original_player = mod.player
        mock_player = MagicMock()
        mod.player = mock_player
        try:
            resp = client.post("/transition", json={"bar": 4})
            assert resp.status_code == 200
            assert resp.json()["status"] == "transitioning"
            mock_player.transition_to_bar_immediately.assert_called_once_with(4)
        finally:
            mod.player = original_player

    def test_get_transition_by_bar(self, client):
        from soundscapes import soundscapes as mod
        original_player = mod.player
        mock_player = MagicMock()
        mod.player = mock_player
        try:
            resp = client.get("/transition/7")
            assert resp.status_code == 200
            assert resp.json()["status"] == "transitioning"
            mock_player.transition_to_bar_on_next_bar.assert_called_once_with(7)
        finally:
            mod.player = original_player


# ---------------------------------------------------------------------------
# /song – set & get song info
# ---------------------------------------------------------------------------

class TestSongEndpoints:
    def test_post_song(self, client, songs_dir):
        from soundscapes import soundscapes as mod
        original_player = mod.player
        mock_player = MagicMock()
        mod.player = mock_player
        original_meta = mod.METADATA_FILE
        mod.METADATA_FILE = str(songs_dir / "metadata.csv")
        try:
            resp = client.post("/song", json={"name": "test.mp3"})
            assert resp.status_code == 200
            assert resp.json()["status"] == "loaded"
            mock_player.set_song.assert_called_once_with("songs/test.mp3", 120, time_signature=4)
        finally:
            mod.player = original_player
            mod.METADATA_FILE = original_meta

    def test_get_song_not_loaded(self, client):
        from soundscapes import soundscapes as mod
        original_player = mod.player
        mock_player = MagicMock()
        mock_player.initialized = False
        mod.player = mock_player
        try:
            resp = client.get("/song")
            assert resp.status_code == 404
        finally:
            mod.player = original_player

    def test_get_song_info(self, client, songs_dir):
        from soundscapes import soundscapes as mod
        original_player = mod.player
        mock_player = MagicMock()
        mock_player.initialized = True
        mock_player.song_path = "songs/test.mp3"
        mock_player.get_duration.return_value = 120.0
        mock_player.get_total_bars.return_value = 60.0
        mock_player.playing = True
        mock_player.get_bar_count_for_current_playback_from_heartbeat.return_value = 5
        mod.player = mock_player
        original_meta = mod.METADATA_FILE
        mod.METADATA_FILE = str(songs_dir / "metadata.csv")
        try:
            resp = client.get("/song")
            assert resp.status_code == 200
            data = resp.json()
            assert data["name"] == "test.mp3"
            assert data["duration"] == 120.0
            assert data["bpm"] == 120
            assert data["timeSignature"] == 4
            assert data["barCount"] == 60.0
            assert data["playing"] is True
            assert data["currentBar"] == 5
        finally:
            mod.player = original_player
            mod.METADATA_FILE = original_meta


# ---------------------------------------------------------------------------
# /items (leftover demo endpoint)
# ---------------------------------------------------------------------------

class TestItemsEndpoint:
    def test_read_item(self, client):
        resp = client.get("/items/42?q=test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["item_id"] == 42
        assert data["q"] == "test"

    def test_read_item_without_query(self, client):
        resp = client.get("/items/1")
        assert resp.status_code == 200
        assert resp.json()["q"] is None


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

class TestWebSocket:
    def test_websocket_echo(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_text("hello")
            data = json.loads(ws.receive_text())
            assert data["type"] == "response"
            assert data["message"] == "hello"

    def test_websocket_disconnect(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_text("ping")
            ws.receive_text()
        # no error means graceful disconnect was handled


# ---------------------------------------------------------------------------
# Exception handler
# ---------------------------------------------------------------------------

class TestExceptionHandler:
    def test_soundscape_exception_returns_json(self, client):
        """When a SoundScapeBaseException is raised, the handler returns structured JSON."""
        from soundscapes import soundscapes as mod
        from soundscapes.exceptions import SongAlreadyPlaying
        original_player = mod.player
        mock_player = MagicMock()
        mock_player.play.side_effect = SongAlreadyPlaying()
        mod.player = mock_player
        try:
            resp = client.post("/play", json={"startBar": 0})
            assert resp.status_code == 400
            body = resp.json()
            assert body["errorCode"] == "song_already_playing"
            assert body["detail"] == "Already playing"
            assert body["status_code"] == 400
        finally:
            mod.player = original_player
