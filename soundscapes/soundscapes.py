from .lib.sound import Player, BarOutOfBounds

from typing import Union
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

# player = Player("./songs/Jon-Hopkins-The-Low-Places.mp3", 152, debug=True)
# player = Player("./songs/HollowKnightGreenPath.mp3", 170, time_signature=3, debug=True)
player = Player("./songs/Payday-2-Master-Plan.mp3", 78, debug=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    player.teardown()

app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/play/{start_bar}")
def play(start_bar: int = 0):
    player.play(start_bar, 24 - start_bar)

    return {"status": "playing"}

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

# player = Player("./songs/Jon-Hopkins-The-Low-Places.mp3", 152)

# player.play(22)


# while True:
#     print(player.get_bar_count_for_current_playback())
#     if player.get_bar_count_for_current_playback() >= 25:
#         player.transition_to_bar(110)
#     pass
