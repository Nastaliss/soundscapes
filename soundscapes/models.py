from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from .db import Base

class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)

    info = relationship("SongInfo", uselist=False, back_populates="song")
    zones = relationship("Zone", back_populates="song")

class SongInfo(Base):
    __tablename__ = "song_info"

    id = Column(Integer, primary_key=True)
    song_id = Column(Integer, ForeignKey("songs.id"))
    time_signature = Column(Integer)
    bpm = Column(Integer)

    song = relationship("Song", back_populates="info")

class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"))

    song = relationship("Song", back_populates="zones")
