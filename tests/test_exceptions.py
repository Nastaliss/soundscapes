from soundscapes.exceptions import (
    SoundScapeBaseException,
    BarOutOfBounds,
    SongNotLoaded,
    SongNotPlaying,
    AlreadyTransitionning,
    SongAlreadyPlaying,
)


class TestSoundScapeBaseException:
    def test_base_exception_defaults(self):
        assert SoundScapeBaseException.detail is None
        assert SoundScapeBaseException.errorCode is None
        assert SoundScapeBaseException.status_code is None

    def test_base_exception_is_exception(self):
        exc = SoundScapeBaseException()
        assert isinstance(exc, Exception)


class TestBarOutOfBounds:
    def test_attributes(self):
        assert BarOutOfBounds.detail == "Bar out of bounds"
        assert BarOutOfBounds.errorCode == "bar_out_of_bounds"
        assert BarOutOfBounds.status_code == 400

    def test_inherits_from_base(self):
        exc = BarOutOfBounds()
        assert isinstance(exc, SoundScapeBaseException)


class TestSongNotLoaded:
    def test_attributes(self):
        assert SongNotLoaded.detail == "No song loaded"
        assert SongNotLoaded.errorCode == "no_song_loaded"
        assert SongNotLoaded.status_code == 400

    def test_inherits_from_base(self):
        assert issubclass(SongNotLoaded, SoundScapeBaseException)


class TestSongNotPlaying:
    def test_attributes(self):
        assert SongNotPlaying.detail == "No song playing"
        assert SongNotPlaying.errorCode == "no_song_playing"
        assert SongNotPlaying.status_code == 400

    def test_inherits_from_base(self):
        assert issubclass(SongNotPlaying, SoundScapeBaseException)


class TestAlreadyTransitionning:
    def test_attributes(self):
        assert AlreadyTransitionning.detail == "Already transitioning"
        assert AlreadyTransitionning.errorCode == "already_transitionning"
        assert AlreadyTransitionning.status_code == 400

    def test_inherits_from_base(self):
        assert issubclass(AlreadyTransitionning, SoundScapeBaseException)


class TestSongAlreadyPlaying:
    def test_attributes(self):
        assert SongAlreadyPlaying.detail == "Already playing"
        assert SongAlreadyPlaying.errorCode == "song_already_playing"
        assert SongAlreadyPlaying.status_code == 400

    def test_inherits_from_base(self):
        assert issubclass(SongAlreadyPlaying, SoundScapeBaseException)
