from .lib.sound import Player

from typing import Union
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import csv
from typing import TypedDict, Any
import json
from sqlalchemy.orm import Session
from .models import Song, Base
from .db import SessionLocal, engine
from . import crud
from .schemas import SongInfoBase
from .exceptions import SongNotFound, SoundScapeBaseException, SongInfoNotFound, SongNotLoaded

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def update_songs_in_db_based_on_local_songs(db: Session):
    songs_from_dir = [song for song in os.listdir("songs") if song.split(".")[-1] in ALLOWED_SONGS_FORMATS]
    songs_from_db = crud.get_song_names(db)

    for song_from_dir in songs_from_dir:
        print(songs_from_db, song_from_dir)
        if song_from_dir not in songs_from_db:
            crud.create_song(db, Song(name=song_from_dir))
            print(f"Added {song_from_dir} to the database")


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

Base.metadata.create_all(bind=engine)

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

update_songs_in_db_based_on_local_songs(next(get_db()))

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
    player.play(play_request.startBar)
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
    player.transition_to_bar_on_next_bar(bar)
    return {"status": "transitioning"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.post("/song/{song_id}")
def set_song(song_id: int, db: Session = Depends(get_db)):
    global player
    song = crud.get_song_by_id(db, song_id)
    if song is None:
        raise SongNotFound()
    info = crud.get_song_info_by_song_id(db, song_id)
    if info is None:
        raise SongInfoNotFound()
    player.set_song(f"songs/{song.name}", info.bpm, time_signature=info.time_signature)
    return {"status": "loaded"}

@app.post("/song/{song_id}/info")
def set_song_info(song_id: int, song_info: SongInfoBase, db: Session = Depends(get_db)):
    song = crud.get_song_by_id(db, song_id)
    if song is None:
        raise SongNotFound()
    crud.add_song_info(db, song_info, song_id)
    return {"status": "info_added"}

@app.get("/songs")
def get_songs(db: Session = Depends(get_db)):
    songs = crud.get_songs(db)
    return {"songs": songs}


@app.get("/song")
def get_current_song_info(db: Session = Depends(get_db)):
    if player.initialized is False:
        raise SongNotLoaded()
    song_name = player.song_path.split("/")[-1]
    song = crud.get_song_by_name(db, song_name)
    if song is None:
        raise SongNotFound()
    song_info = crud.get_song_info_by_song_id(db, song.id)
    if song_info is None:
        raise SongInfoNotFound()
    return {
        "id": song.id,
        "name": song.name,
        "duration": player.get_duration(),
        "timeSignature": song_info.time_signature,
        "barCount": player.get_total_bars(),
        "bpm": song_info.bpm,
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
