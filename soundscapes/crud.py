from sqlalchemy.orm import Session

from . import models, schemas

def get_song_by_id(db: Session, song_id: int):
    return db.query(models.Song).filter(models.Song.id == song_id).first()

def get_song_by_name(db: Session, song_name: str):
    return db.query(models.Song).filter(models.Song.name == song_name).first()

def get_song_info_by_song_id(db: Session, song_id: int):
    return db.query(models.SongInfo).filter(models.SongInfo.song_id == song_id).first()

def add_song_info(db: Session, song_info: schemas.SongInfoCreate, song_id: int):
    db_song_info = models.SongInfo(**song_info.model_dump(), song_id=song_id)
    db.add(db_song_info)
    db.commit()
    db.refresh(db_song_info)
    return db_song_info

def get_songs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Song).offset(skip).limit(limit).all()

def get_song_names(db: Session):
    return [song.name for song in get_songs(db)]

def create_song(db: Session, song: schemas.SongCreate):
    db_song = models.Song(name=song.name)
    db.add(db_song)
    db.commit()
    db.refresh(db_song)
    return db_song
