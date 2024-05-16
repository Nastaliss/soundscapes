from pydantic import BaseModel

class SongBase(BaseModel):
    name: str

class SongCreate(SongBase):
    pass

class SongInfoBase(BaseModel):
    time_signature: int
    bpm: int


class SongWithInfo(SongBase, SongInfoBase):
    id: int

    class Config:
        orm_mode = True

class SongInfoCreate(SongInfoBase):
    pass
