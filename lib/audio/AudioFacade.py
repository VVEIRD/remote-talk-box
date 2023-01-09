import pyaudio
import wave
import sys
import threading
import time
import random
import json
from json import JSONDecodeError
from pathlib import Path
from queue import Queue
from datetime import datetime, timedelta

# -------------------------------------------------------
# CLASSes

class AudioFile:
    chunk = 4096

    def __init__(self, file):
        """ Init audio stream """ 
        print(file)
        self.interruped = False
        self.finished = False
        self.wf = wave.open(file, 'rb')
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format = self.p.get_format_from_width(self.wf.getsampwidth()),
            channels = self.wf.getnchannels(),
            rate = self.wf.getframerate(),
            output = True
        )

    def play(self):
        """ Play entire file """
        self.finished = False
        data = self.wf.readframes(self.chunk)
        while data != b''and not self.interruped:
            self.stream.write(data)
            data = self.wf.readframes(self.chunk)
        self.finished = True

    def close(self):
        """ Graceful shutdown """ 
        if self.finished:
            return
        self.interruped = True
        # Wait for audio to stop
        while not self.finished:
            time.sleep(0.2)
        self.stream.close()
        self.p.terminate()


# -------------------------------------------------------
# VARs

LD_PATH = Path('data', 'audio')

AUDIO_PLAYER = [None]

AUDIO_DAEMON = [None]

RANDOM_PLAYBACK_PLAYER = [None]

RANDOM_PLAYBACK_DAEMON = [None]
RANDOM_PLAYBACK_NEXT_UP = ['Nothing', -1]

RANDOM_CONFIG = {'min_interval': 900, 'max_interval': 3600, 'list': []}

AUDIO_QUEUE = Queue()

DAEMON_RUNNING = [True, True]

CURRENTLY_PLAYING = [None, None]

# -------------------------------------------------------
# METHODs

def __init__():
    LD_PATH.mkdir(parents=True, exist_ok=True)
    AUDIO_DAEMON = threading.Thread(target=_audio_daemon, daemon=True)
    AUDIO_DAEMON.start()
    # Load Random Audio player
    with LD_PATH.joinpath('random.json').open(mode='r', encoding="utf8") as random_io:
        try:
            json_o = json.loads(random_io.read())
            RANDOM_CONFIG['min_interval'] = json_o['min_interval']
            RANDOM_CONFIG['max_interval'] = json_o['max_interval']
            RANDOM_CONFIG['list'] = json_o['list']
        except JSONDecodeError as e:
            print("Error loading random file {file}".format(file=random_io.absolute()))
    RANDOM_PLAYBACK_DAEMON[0] = threading.Thread(target=_random_audio_daemon, daemon=True)
    RANDOM_PLAYBACK_DAEMON[0].start()

def _audio_daemon():
    print('Start audio daemon')
    audio_file = None
    while DAEMON_RUNNING[0]:
        if not AUDIO_QUEUE.empty():
            audio = AUDIO_QUEUE.get()
            audio_file = read_audio_files()[audio]
        if audio_file is not None:
            CURRENTLY_PLAYING[0] = audio
            audio = AudioFile(file=audio_file)
            AUDIO_PLAYER[0] = audio
            try:
                audio.play()
            finally:
                AUDIO_PLAYER[0] = None
                audio.close()
            CURRENTLY_PLAYING[0] = None
            audio_file = None
        else:
            time.sleep(0.5)
    print('Stop audio daemon')

def _random_audio_daemon():
    print('Start random audio daemon')
    audio_file = None
    while DAEMON_RUNNING[1]:
        sleepy_time = random.randint(RANDOM_CONFIG['min_interval'], RANDOM_CONFIG['max_interval'])
        playback_starts_at = datetime.today() + timedelta(seconds=sleepy_time)
        audio = random.choice(RANDOM_CONFIG['list'])
        RANDOM_PLAYBACK_NEXT_UP[0] = audio
        RANDOM_PLAYBACK_NEXT_UP[1] = playback_starts_at.isoformat()
        audio_file = read_audio_files()[audio]
        # Queue file only if it exists (It should, but it could have been deleted on fs)
        if audio_file is not None:
            start_time = datetime.now()
            end_time = datetime.now()
            print('Queing random playback for file {audio} at {date}'.format(audio=audio, date=playback_starts_at))
            while end_time - start_time < timedelta(seconds=sleepy_time) and DAEMON_RUNNING[1]:
                time.sleep(0.5)
                end_time = datetime.now()
        if audio_file is not None and DAEMON_RUNNING[1]:
            CURRENTLY_PLAYING[1] = audio
            audio = AudioFile(file=audio_file)
            RANDOM_PLAYBACK_PLAYER[0] = audio
            try:
                audio.play()
            finally:
                RANDOM_PLAYBACK_PLAYER[0] = None
                audio.close()
            CURRENTLY_PLAYING[1] = None
            audio_file = None
        time.sleep(0.5)
    print('Stop random audio daemon')

def get_audio_folder():
    return str(LD_PATH.resolve())

def read_audio_files():
    AUDIO_FILES = {}
    for audio_file in LD_PATH.rglob("*.wav"):
        AUDIO_FILES[audio_file.stem] = str(audio_file.resolve())
    return AUDIO_FILES

def play_audio_file(name:str):
    if name not in read_audio_files():
        raise ValueError("Audiofile {name} does not exists".format(name=name))
    AUDIO_QUEUE.put(name)

def flush_queue():
    with AUDIO_QUEUE.mutex:
        AUDIO_QUEUE.queue.clear()

def get_audio_status():
    queue_count = AUDIO_QUEUE.qsize()
    currently_playing = CURRENTLY_PLAYING[0]
    queue = list(AUDIO_QUEUE.queue)
    return {'currently_playing': currently_playing, 'queue_count': queue_count, 'queue': queue}

def stop_playback():
    if AUDIO_PLAYER[0] is not None:
        AUDIO_PLAYER[0].close()

def stop_random_playback():
    if RANDOM_PLAYBACK_PLAYER[0] is not None:
        RANDOM_PLAYBACK_PLAYER[0].close()

def disable_random_playback():
    DAEMON_RUNNING[1] = False
    if RANDOM_PLAYBACK_PLAYER[0] is not None:
        RANDOM_PLAYBACK_PLAYER[0].close()
    RANDOM_PLAYBACK_NEXT_UP[0] = "Nothing"
    RANDOM_PLAYBACK_NEXT_UP[1] = -1

def enable_random_playback():
    DAEMON_RUNNING[1] = True
    if RANDOM_PLAYBACK_DAEMON[0] is None or not RANDOM_PLAYBACK_DAEMON[0].is_alive():
        RANDOM_PLAYBACK_DAEMON[0] = threading.Thread(target=_random_audio_daemon, daemon=True)
        RANDOM_PLAYBACK_DAEMON[0].start()
        time.sleep(0.2)

def get_audio_files():
    ''' Returns all available audio files '''
    return [file for file in read_audio_files()]

def get_random_playback():
    random_playback_status = RANDOM_CONFIG.copy()
    random_playback_status['status'] =  "enabled" if DAEMON_RUNNING[1] else "disabled"
    random_playback_status['next_up'] = RANDOM_PLAYBACK_NEXT_UP[0]
    random_playback_status['played_at'] = RANDOM_PLAYBACK_NEXT_UP[1]
    return random_playback_status

def add_random_playback(name:str):
    if name not in read_audio_files():
        raise ValueError("Cannot Audiofile {name} to random playback, it does not exists".format(name=name))
    if name not in RANDOM_CONFIG['list']:
        RANDOM_CONFIG['list'].append(name)
        save_random_playback_config()

def remove_random_playback(name:str):
    if name not in RANDOM_CONFIG['list']:
        raise ValueError("Cannot remove Audiofile {name} from random playback, it is not in the list".format(name=name))
    RANDOM_CONFIG['list'].remove(name)
    save_random_playback_config()

def save_random_playback_config():
    random_file = LD_PATH.joinpath('random.json')
    with random_file.open(mode='w', encoding="utf8") as random_io:
        random_io.write(json.dumps(RANDOM_CONFIG))

__init__()