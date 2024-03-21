import time
from threading import Timer
from just_playback import Playback
import math

class BarOutOfBounds(Exception):
    pass

class Player(object):
    def __init__(self, song_path: str, song_bpm: int, ws_manager, time_signature: int = 4, debug: bool = False):
        self.song_path = song_path
        self.song_bpm = song_bpm
        self.time_signature = time_signature

        bar_per_minute = self.song_bpm / self.time_signature
        bar_per_second = bar_per_minute / 60
        self.second_per_bar = 1 / bar_per_second

        self.playbacks = [Playback(), Playback()]

        self.timer = None
        self.ws_manager = ws_manager

        self.current_playback = 0

        self.get_current_playback().load_file(self.song_path)
        self.get_standby_playback().load_file(self.song_path)

        self.current_playback_start_time = None
        self.use_heart_beat = debug
        if self.use_heart_beat:
            self.heart_beat = BarHeartBeat(self.second_per_bar, manager=self.ws_manager)
        self.transitionning = False

    def reset(self, song_path: str, song_bpm: int, time_signature: int = 4, debug: bool = False):
        # reuse logic from __init__()
        self.song_path = song_path
        self.song_bpm = song_bpm
        self.time_signature = time_signature

        bar_per_minute = self.song_bpm / self.time_signature
        bar_per_second = bar_per_minute / 60
        self.second_per_bar = 1 / bar_per_second

        self.playbacks = [Playback(), Playback()]

        self.timer = None

        self.current_playback = 0

        self.get_current_playback().load_file(self.song_path)
        self.get_standby_playback().load_file(self.song_path)

        self.current_playback_start_time = None
        self.use_heart_beat = debug
        self.transitionning = False

    def get_duration(self):
        return self.get_current_playback().duration

    def get_total_bars(self):
        return self.get_duration() / self.second_per_bar

    async def play(self, start_bar: int = 0, loop_bar_count: int = None):
        start_time = self.get_time_of_bar(start_bar)
        self.get_current_playback().play()
        self.get_current_playback().seek(start_time)

        if self.use_heart_beat:
            await self.heart_beat.start()

        if loop_bar_count:
            self.timer = Timer(loop_bar_count * self.second_per_bar, self._loop_timer_handler, [0])
            self.timer.start()

    def get_next_bar_time(self):
        return (self.get_current_playback().curr_pos % self.second_per_bar)

    def transition_to_bar_on_next_bar(self, bar: int):
        if self.transitionning:
            raise Exception("Already transitionning")
        if self.get_time_of_bar(bar) > self.get_standby_playback().duration:
            raise BarOutOfBounds()
        self.transitionning = True
        if self.timer:
            self.timer.cancel()
        self.timer = Timer(math.ceil(self.get_bar_count_for_current_playback()) * self.second_per_bar - self.get_current_playback().curr_pos, self._transition_timer_handler, [bar])
        self.timer.start()

    def transition_to_bar_immediately(self, bar: int):
        if self.transitionning:
            raise Exception("Already transitionning")
        if self.get_time_of_bar(bar) > self.get_standby_playback().duration:
            raise BarOutOfBounds()
        self.transitionning = True
        if self.timer:
            self.timer.cancel()
        bar_offset = self.get_time_elapsed_from_last_bar_for_current_playback()
        self._transition_to_bar(bar, bar_offset)

    def _transition_timer_handler(self, bar: int):
        self._transition_to_bar(bar)

    def _loop_timer_handler(self, loop_start_bar: int):
        if self.transitionning:
            print("transitionning, not looping")
            return
        self.transitionning = True
        print("LOOPING!")
        self._transition_to_bar(loop_start_bar)

    def stop(self):
        self.get_current_playback().stop()
        self.get_standby_playback().stop()
        self.teardown()

    def get_bar_count_for_current_playback(self):
        return (self.get_current_playback().curr_pos) / self.second_per_bar

    def get_time_elapsed_from_last_bar_for_current_playback(self):
        return (self.get_current_playback().curr_pos) % self.second_per_bar

    def get_time_of_bar(self, bar: int):
        return self.second_per_bar * bar

    def _transition_to_bar(self, bar: int, offset_seconds: float = 0):
        """
        Transition to the given bar of the song, with a fade in and out of the two playbacks

        :param bar: The bar index to transition to
        :param offset_seconds: The number of seconds to offset the playback by

        The playback will transition from the current playback to the given bar with a fade in and out of the two playbacks
        """
        print(self.get_bar_count_for_current_playback()/ self.second_per_bar)

        self.get_standby_playback().play()

        self.get_standby_playback().seek(self.get_time_of_bar(bar) + offset_seconds)
        self.get_standby_playback().set_volume(0)
        self.get_current_playback().set_volume(100)

        for i in range(100):
            self.get_current_playback().set_volume((100 - i) / 100)
            self.get_standby_playback().set_volume(i / 100)
            time.sleep(3 / 100)
        self.current_playback = (self.current_playback + 1) % len(self.playbacks)
        self.get_standby_playback().stop()
        self.transitionning = False

    def get_current_playback(self):
        return self.playbacks[self.current_playback]

    def get_standby_playback(self):
        return self.playbacks[(self.current_playback + 1) % len(self.playbacks)]


    def teardown(self):
        if self.timer:
            self.timer.cancel()
        if self.use_heart_beat:
            self.heart_beat.stop()
        [playback.stop() for playback in self.playbacks]

class BarHeartBeat(object):

    def __init__(self, hear_beat_interval: float, manager):
        self.heart_beat_interval = hear_beat_interval

        self.manager = manager
        self.timer = None
        self.counter = 0

    async def _beat(self):
        print(f"Heartbeat #{self.counter}!")
        self.counter += 1
        self.timer = Timer(self.heart_beat_interval, self._beat)
        self.timer.start()
        await self.manager.broadcast(f"Heartbeat #{self.counter}!")

    async def start(self):
        await self._beat()


    def stop(self):
        if self.timer:
            self.timer.cancel()
        self.counter = 0
