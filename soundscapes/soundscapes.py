from .lib.sound import Player

from typing import Union
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import csv
from typing import TypedDict, Any
import json

from .exceptions import SoundScapeBaseException, SongNotLoaded, BarOutOfBounds, SongNotPlaying


class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    def _format_message(self, message_type: str, message: str):
        return json.dumps({
            "type": message_type,
            "message": message
        })

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def respond(self, websocket: WebSocket, message: str):
        await websocket.send_text(self._format_message("response", message))

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

METADATA_FILE = "songs/metadata.csv"
player = Player(manager)

ALLOWED_SONGS_FORMATS = ["mp3", "wav"]



@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    player.teardown()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(SoundScapeBaseException)
async def soundscapes_exception_handler(request: Request, exc: SoundScapeBaseException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "errorCode": exc.errorCode, "status_code": exc.status_code}
    )


@app.get("/")
def read_root():
    return HTMLResponse("Soundscape API")


class PlayRequest(BaseModel):
    startBar: int

@app.post("/play")
async def play(play_request: PlayRequest):
    try:
        player.play(play_request.startBar)
    except SongNotLoaded as e:
        raise HTTPException(status_code=400, detail="No song loaded")
    return {"status": "playing"}

@app.post("/stop")
def stop():
    player.stop()

    return {"status": "stopped"}

class TransitionRequest(BaseModel):
    bar: int

@app.post("/transition")
def transition_immediately(transition_request: TransitionRequest):
    player.transition_to_bar_immediately(transition_request.bar)
    return {"status": "transitioning"}


@app.get("/stop")
def play():
    player.stop()
    return {"status": "stopped"}

@app.get("/transition/{bar}")
def transition_to_bar(bar: int):
    try:
        player.transition_to_bar_on_next_bar(bar)
    except BarOutOfBounds as e:
        raise HTTPException(status_code=400, detail="Bar out of bounds")
    return {"status": "transitioning"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

class Song(BaseModel):
    name: str

def get_info_from_metadata(song_name: str):
    with open(METADATA_FILE, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["song_name"] == song_name:
                return row
    return None

@app.post("/song")
def set_song(song: Song):
    global player
    try:
        metadata = get_info_from_metadata(song.name)
        player.set_song(f"songs/{song.name}", int(metadata["bpm"]), time_signature=int(metadata["time_signature"]))
    except Exception as e:
        print(e)
        raise SoundScapeException(status_code=400, detail=f"Could not load song: {e}", )
    return {"status": "loaded"}

@app.get("/songs")
def get_songs():
    songs = [song for song in os.listdir("songs") if song.split(".")[-1] in ALLOWED_SONGS_FORMATS]
    return {"songs": songs}

class MetadataEntry(TypedDict):
    song_name: str
    bpm: int
    time_signature: int

@app.get("/song")
def get_current_song_info():
    if player.initialized is False:
        raise HTTPException(status_code=404, detail="No song loaded")
    song_path = player.song_path.split("/")[-1]
    song: MetadataEntry = None
    with open(METADATA_FILE, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["song_name"] == song_path:
                song = row
                break
    if song is None:
        raise HTTPException(status_code=400, detail="Song not found in metadata")
    return {
        "name": song["song_name"],
        "duration": player.get_duration(),
        "timeSignature": song["time_signature"],
        "barCount": player.get_total_bars(),
        "bpm": song["bpm"],
        "playing": player.playing,
        "currentBar": player.get_bar_count_for_current_playback_from_heartbeat()
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print("Connected")
    try:
        while True:
            data = await websocket.receive_text()
            await manager.respond(websocket, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client left the chat")
