
class SoundScapeBaseException(Exception):
  detail = None
  errorCode = None
  status_code = None

  def __init__(self, *args, **kwargs):
      raise NotImplementedError

class SoundScapeHttpException(Exception):
    def __init__(self, exception: SoundScapeBaseException):
        self.detail = exception.detail
        self.errorCode = exception.errorCode
        self.status_code = exception.status_code

class BarOutOfBounds(SoundScapeBaseException):
  detail = "Bar out of bounds"
  errorCode = "bar_out_of_bounds"
  status_code = 400

class SongNotLoaded(Exception):
  detail = "No song loaded"
  errorCode = "no_song_loaded"
  status_code = 400

class SongNotPlaying(Exception):
  detail = "No song playing"
  errorCode = "no_song_playing"
  status_code = 400

class AlreadyTransitionning(Exception):
  data = "Already transitioning"
  errorCode = "already_transitionning"
  status_code = 400
