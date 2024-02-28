from .pygame_wrapper.pygame_wrapper import Player


from typing import Union
from contextlib import asynccontextmanager
from fastapi import FastAPI

player = Player("./songs/Jon-Hopkins-The-Low-Places.mp3", 152)

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
    player.transition_to_bar_on_next_bar(bar)
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
