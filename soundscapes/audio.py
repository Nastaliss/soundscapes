import vlc
import time
import math
# start : 1.64S
# Intro : 1.64s - 37.8


# y, sr = librosa.load("./songs/Jon-Hopkins-The-Low-Places.mp3")

# tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
# print('Estimated tempo: {:.2f} beats per minute'.format(tempo))

# open a file and play it at 3 mins 30

song_stages = {
    "Startup": (0, 1.64),
    "Intro": (1.64, 37.8),
    "Main": (37.8, 1000)
}

target = "Main"

bpm = 152

bar_per_minute = bpm / 4
bar_per_second = bar_per_minute / 60
second_per_bar = 1 / bar_per_second
print(second_per_bar)


start_time = time.time()

transitioning = False
transition_start_time = None

def get_current_stage():
    if get_current_duration() < 1.64:
        return "Startup"
    elif get_current_duration() < 37.8:
        return "Intro"
    else:
        return "Main"

def get_current_duration():
    return time.time() - start_time

def get_current_song_time(song: vlc.MediaPlayer):
    return song.get_time()

def set_current_song_bar(player: vlc.MediaPlayer, bar: int):
    print(bar * second_per_bar * 1000)
    player.set_time(math.ceil(bar * second_per_bar * 1000))

def get_current_song_bar(player: vlc.MediaPlayer):
    return  get_current_song_time(player) / (second_per_bar*1000)

current_stage = None
players = [vlc.MediaPlayer("./songs/Jon-Hopkins-The-Low-Places.mp3"), vlc.MediaPlayer("./songs/Jon-Hopkins-The-Low-Places.mp3")]

current_player = 0
previous_player = 1
players[current_player].audio_set_volume(100)
players[previous_player].audio_set_volume(0)

players[current_player].play()
# players[previous_player].play()
# players[previous_player].audio_set_volume(0)

# this is temporary
set_current_song_bar(players[current_player], 2)

players[previous_player].set_time(1640)

previous_bar = 0

while True:
    # if (get_current_song_time(players[current_player]) / (second_per_bar*1000)) > 11 :

    if target == "Intro" and get_current_song_bar(players[current_player]) > 20:
        # transition to intro using other player
        target = "Main"
        previous_player = current_player
        current_player = (current_player + 1) % len(players)
        transitioning = True
        print("Transitioning to Main")
        transition_start_time = time.time()

        players[current_player].play()
        set_current_song_bar(players[current_player], 156)
        # transition_volume = 20


    if transitioning:
        transition_factor = math.ceil(((time.time() - transition_start_time) / second_per_bar ) * 100)
        print(transition_factor)
        players[current_player].audio_set_volume(transition_factor)
        players[previous_player].audio_set_volume(100 - transition_factor)
        if (transition_factor >= 100):
            transitioning = False
            players[previous_player].stop()
            players[previous_player].audio_set_volume(0)
            print("Transition finished")

            
    curr_bar = math.floor(get_current_song_bar(players[current_player]))
    if previous_bar != curr_bar:
        print(curr_bar)
        previous_bar = curr_bar
    # print(( time.time() - start_time )/ second_per_bar)


    # current_stage = get_current_stage()
    # if current_stage == transition_to:
    #     print("Finish transition")
    #     transition_to = None

    # if get_current_song_time(players[current_player]) > 37.8 and transition_to is None:
    #     print("Transitioning to Intro")
    #     transition_to = "Intro"
    #     players[current_player].set_time(33800)
    #     print("here")


    pass