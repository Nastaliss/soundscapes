import librosa
import numpy as np

y, sr = librosa.load("./songs/Jon-Hopkins-The-Low-Places.mp3")
# get onset envelope
onset_env = librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.median)
# get tempo and beats
tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)

# we assume 4/4 time
meter = 4
# calculate number of full measures 
measures = (len(beats) // meter)

# get onset strengths for the known beat positions
# Note: this is somewhat naive, as the main strength may be *around*
#       rather than *on* the detected beat position. 
beat_strengths = onset_env[beats]
# make sure we only consider full measures
# and convert to 2d array with indices for measure and beatpos
measure_beat_strengths = beat_strengths[:measures * meter].reshape(-1, meter)
print('beats: {}'.format(measure_beat_strengths))
# add up strengths per beat position
beat_pos_strength = np.sum(measure_beat_strengths, axis=0)
print('beatsposstr: {}'.format(beat_pos_strength))
# find the beat position with max strength
downbeat_pos = np.argmax(beat_pos_strength)
# convert the beat positions to the same 2d measure format
full_measure_beats = beats[:measures * meter].reshape(-1, meter)
# and select the beat position we want: downbeat_pos
downbeat_frames = full_measure_beats[:, downbeat_pos]
print('Downbeat frames: {}'.format(downbeat_frames))
# print times
downbeat_times = librosa.frames_to_time(downbeat_frames, sr=sr)
print('Downbeat times in s: {}'.format(downbeat_times))