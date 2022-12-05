import pyaudio
import wave
import sys
import threading
import time
from pathlib import Path
from queue import Queue

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

AUDIO_FILES = {}

AUDIO_PLAYER = [None]

AUDIO_DAEMON = [None]

AUDIO_QUEUE = Queue()

DAEMON_RUNNING = [True]
CURRENTLY_PLAYING = [None]

# -------------------------------------------------------
# METHODs

def __init__():
    LD_PATH.mkdir(parents=True, exist_ok=True)
    # Load Audio library
    for audio_file in LD_PATH.rglob("*.wav"):
        AUDIO_FILES[audio_file.stem] = str(audio_file.resolve())
    AUDIO_DAEMON = threading.Thread(target=_audio_daemon, daemon=True)
    AUDIO_DAEMON.start()

def _audio_daemon():
    print('Start audio daemon')
    audio_file = None
    while DAEMON_RUNNING[0]:
        if not AUDIO_QUEUE.empty():
            audio = AUDIO_QUEUE.get()
            audio_file = AUDIO_FILES[audio]
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
            time.sleep(0.2)
    print('Stop audio daemon')

def play_audio_file(name:str):
    if name not in AUDIO_FILES:
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

def get_audio_files():
    ''' Returns all available audio files '''
    return [audio_name for audio_name in AUDIO_FILES]

__init__()