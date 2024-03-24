import time
from threading import Timer
from just_playback import Playback
import math
import asyncio
import json

from ..exceptions import SongNotLoaded, AlreadyTransitionning, BarOutOfBounds, SongNotPlaying


class Player(object):
    initialized = False
    timer = None
    playbacks = [Playback(), Playback()]
    current_playback = 0
    current_playback_start_time = None
    transitionning = False
    heart_beat = None
    playing = False

    def __init__(self, ws_manager):
        self.ws_manager = ws_manager


    def set_song(self, song_path: str, song_bpm: int, time_signature: int = 4):
        self.song_path = song_path
        self.song_bpm = song_bpm
        self.time_signature = time_signature

        bar_per_minute = self.song_bpm / self.time_signature
        bar_per_second = bar_per_minute / 60
        self.second_per_bar = 1 / bar_per_second

        self.playbacks = [Playback(), Playback()]

        self.current_playback = 0

        self.get_current_playback().load_file(self.song_path)
        self.get_standby_playback().load_file(self.song_path)

        self.current_playback_start_time = None
        if self.heart_beat is not None:
            self.heart_beat.stop()
        self.heart_beat = BarHeartBeat(self.second_per_bar, manager=self.ws_manager, on_new_bar=self.on_new_bar, on_end=self.on_end)
        self.initialized = True
        self.transitionning = False

    async def on_new_bar(self, bar: int):
        print(f"New bar: {bar}")
        await self.ws_manager.broadcast(json.dumps({"type": "bar", "bar": bar}))

    def on_end(self):
        pass

    def get_duration(self):
        return self.get_current_playback().duration

    def get_total_bars(self):
        return self.get_duration() / self.second_per_bar

    def play(self, start_bar: int = 0, loop_bar_count: int = None):
        if not self.initialized:
            raise SongNotLoaded()
        start_time = self.get_time_of_bar(start_bar)
        self.get_current_playback().play()
        self.get_current_playback().seek(start_time)

        self.heart_beat.start()

        if loop_bar_count:
            self.timer = Timer(loop_bar_count * self.second_per_bar, self._loop_timer_handler, [0])
            self.timer.start()
        self.playing = True

    def get_next_bar_time(self):
        return (self.get_current_playback().curr_pos % self.second_per_bar)

    def transition_to_bar_on_next_bar(self, bar: int):
        if not self.initialized:
            raise SongNotLoaded()
        if self.playing == False:
            raise SongNotPlaying()
        if self.transitionning:
            raise AlreadyTransitionning()
        if self.get_time_of_bar(bar) > self.get_standby_playback().duration:
            raise BarOutOfBounds()
        self.transitionning = True
        if self.timer:
            self.timer.cancel()
        self.timer = Timer(math.ceil(self.get_bar_count_for_current_playback()) * self.second_per_bar - self.get_current_playback().curr_pos, self._transition_timer_handler, [bar])
        self.timer.start()

    def transition_to_bar_immediately(self, bar: int):
        if not self.initialized:
            raise SongNotLoaded()
        if self.playing == False:
            raise SongNotPlaying()
        if self.transitionning:
            raise AlreadyTransitionning()
        if self.get_time_of_bar(bar) > self.get_standby_playback().duration:
            raise BarOutOfBounds()
        self.transitionning = True
        if self.timer:
            self.timer.cancel()
        bar_offset = self.get_time_elapsed_from_last_bar_for_current_playback()
        self._transition_to_bar(bar, bar_offset)

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

    def get_bar_count_for_current_playback_from_heartbeat(self):
        return self.heart_beat.counter

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
        self.heart_beat.set_bar(bar)
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
        self.playing = False
        if self.initialized:
            if self.timer:
                self.timer.cancel()
            self.heart_beat.stop()
            [playback.stop() for playback in self.playbacks]


class BarHeartBeat(object):

    def __init__(self, hear_beat_interval: float, manager, on_new_bar, on_end):
        self.heart_beat_interval = hear_beat_interval

        self.manager = manager
        self.run = False
        self.counter = 0
        self.on_new_bar = on_new_bar
        self.on_end = on_end
        print(self.heart_beat_interval)

    def set_bar(self, bar: int):
        print(f"Setting bar to {bar}")
        self.counter = bar

    async def _emit_beat(self):
        if not self.run:
            return
        await self.on_new_bar(self.counter)
        self.counter += 1

    async def _beat(self):
        if not self.run:
            return
        await asyncio.sleep(self.heart_beat_interval)
        asyncio.create_task(self._beat())

        await self._emit_beat()

    def start(self):
        asyncio.create_task(self._emit_beat())
        self.run = True
        asyncio.create_task(self._beat())


    def stop(self):
        self.counter = 0
        self.run = False
