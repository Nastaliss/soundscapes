from .lib.sound import Player, BarOutOfBounds

from typing import Union
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import csv
from typing import TypedDict

METADATA_FILE = "songs/metadata.csv"
# player = Player("./songs/Jon-Hopkins-The-Low-Places.mp3", 152, debug=True)
player = Player("./songs/HollowKnightGreenPath.mp3", 170, time_signature=3, debug=True)
# player = Player("./songs/Payday-2-Master-Plan.mp3", 78, debug=True)

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


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/play/{start_bar}")
def play(start_bar: int = 0):
    player.play(start_bar, 24 - start_bar)

    return {"status": "playing"}

class PlayRequest(BaseModel):
    startBar: int

@app.post("/play")
def play(play_request: PlayRequest):
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
    try:
        player.transition_to_bar_immediately(transition_request.bar)
    except BarOutOfBounds as e:
        raise HTTPException(status_code=400, detail="Bar out of bounds")
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

@app.post("/song")
def set_song(song: Song):
    global player
    try:
        player.teardown()
        player = Player(f"songs/{song.name}", 170, time_signature=3, debug=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load song: {e}")
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
        "bpm": song["bpm"]
    }

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

@app.get("/cc")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")
