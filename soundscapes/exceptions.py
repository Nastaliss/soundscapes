class SoundScapeBaseException(Exception):
  detail = None
  errorCode = None
  status_code = None

class BarOutOfBounds(SoundScapeBaseException):
  detail = "Bar out of bounds"
  errorCode = "bar_out_of_bounds"
  status_code = 400

class SongNotLoaded(SoundScapeBaseException):
  detail = "No song loaded"
  errorCode = "no_song_loaded"
  status_code = 400

class SongNotPlaying(SoundScapeBaseException):
  detail = "No song playing"
  errorCode = "no_song_playing"
  status_code = 400

class AlreadyTransitionning(SoundScapeBaseException):
  detail = "Already transitioning"
  errorCode = "already_transitionning"
  status_code = 400
