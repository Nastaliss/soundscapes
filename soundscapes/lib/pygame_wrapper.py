import time
from threading import Timer
from just_playback import Playback
import math

class Player(object):
    def __init__(self, song_path: str, song_bpm: int, time_signature: int = 4):
        self.song_path = song_path
        self.song_bpm = song_bpm
        self.time_signature = time_signature


        bar_per_minute = self.song_bpm / 4
        bar_per_second = bar_per_minute / 60
        self.second_per_bar = 1 / bar_per_second

        self.playbacks = [Playback(), Playback()]

        self.timer = None

        self.current_playback = 0

        self.get_current_playback().load_file(self.song_path)
        self.get_standby_playback().load_file(self.song_path)

        self.current_playback_start_time = None

    def play(self, start_bar: int = 0, loop_bar_count: int = None):
        start_time = self.get_time_of_bar(start_bar)
        self.get_current_playback().play()
        self.get_current_playback().seek(start_time)
        if loop_bar_count:
            self.timer = Timer(loop_bar_count * self.second_per_bar, self._loop_timer_handler, [0])
            self.timer.start()

    def transition_to_bar_on_next_bar(self, bar: int):
        print(self.get_current_playback().curr_pos)
        if self.timer:
            self.timer.cancel()
        print(self.get_time_of_bar(math.ceil(self.get_bar_count_for_current_playback())))
        self.timer = Timer(self.second_per_bar * (bar - self.get_bar_count_for_current_playback()), self._transition_timer_handler, [bar])
        self.timer.start()

    def _transition_timer_handler(self, bar: int):
        print("TRANSITIONNING!")
        self._transition_to_bar(bar)

    def _loop_timer_handler(self, loop_start_bar: int):
        print("LOOPING!")
        self._transition_to_bar(loop_start_bar)

    def stop(self):
        self.get_current_playback().stop()
        self.get_standby_playback().stop()

    def get_bar_count_for_current_playback(self):
        # return self.get_current_playback().get_sound().  
        return (self.get_current_playback().curr_pos) / self.second_per_bar

    def get_time_of_bar(self, bar: int):
        return self.second_per_bar * bar

    def _transition_to_bar(self, bar: int):
        self.get_standby_playback().play()
        self.get_standby_playback().seek(self.get_time_of_bar(bar))
        self.get_standby_playback().set_volume(0)
        self.get_current_playback().set_volume(100)
        for i in range(100):
            self.get_current_playback().set_volume((100 - i) / 100)
            self.get_standby_playback().set_volume(i / 100)
            time.sleep(self.second_per_bar / 100)
        self.current_playback = (self.current_playback + 1) % len(self.playbacks)

    def get_current_playback(self):
        return self.playbacks[self.current_playback]

    def get_standby_playback(self):
        return self.playbacks[(self.current_playback + 1) % len(self.playbacks)]


    def teardown(self):
        if self.timer:
            self.timer.cancel()
        [playback.stop() for playback in self.playbacks]