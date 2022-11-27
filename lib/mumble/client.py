
import pymumble_py3 as pymumble_py3
from pymumble_py3.callbacks import PYMUMBLE_CLBK_SOUNDRECEIVED as PCS
import pyaudio
import threading, copy

class MumbleClient:
    def __init__(self, host=None, username=None, pwd=None, port=64738):
        # Connection details for mumble server. Hardcoded for now, will have to be
        # command line arguments eventually
        self.pwd = pwd 
        self.server = host 
        self.nick = username
        self.port = port
        # pyaudio set up
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16  
        self.CHANNELS = 1
        self.RATE = 48000 
        self.active = False
        self.mumble = pymumble_py3.Mumble(host=self.server, user=self.nick, password=self.pwd, port=self.port, reconnect=True)


    # mumble client set up
    def sound_received_handler(self, user, soundchunk):
        """ play sound received from mumble server upon its arrival """
        self.stream.write(soundchunk.pcm)

    def audio_reciver_daemon(self):
        # constant capturing sound and sending it to mumble server
        while self.active:
            data = self.stream.read(self.CHUNK, exception_on_overflow=False)
            self.mumble.sound_output.add_sound(data)

    def connect(self, host=None, username=None, pwd=None, port=None):
        if host is not None:
            self.server = host
        if username is not None:
            self.nick = username
        if pwd is not None:
            self.pwd = pwd
        if port is not None:
            self.port = port
        #if self.get_session() is not None:
        #    self.disconnect()
        self.active = True
        self.pyAudio = pyaudio.PyAudio()
        self.stream = self.pyAudio.open(format=self.FORMAT,
                        channels=self.CHANNELS,
                        rate=self.RATE,
                        input=True,  # enable both talk
                        output=True,  # and listen
                        frames_per_buffer=self.CHUNK)   
        # Spin up a client and connect to mumble server
        self.mumble = pymumble_py3.Mumble(host=self.server, user=self.nick, password=self.pwd, port=self.port, reconnect=True)
        # set up callback called when PCS event occurs
        self.mumble.callbacks.set_callback(PCS, self.sound_received_handler)
        self.mumble.set_receive_sound(1)  # Enable receiving sound from mumble server
        self.mumble.start()
        self.mumble.is_ready()  # Wait for client is ready
        self.audio_daemon = threading.Thread(target=self.audio_reciver_daemon, args=(), daemon=True)
        if self.mumble.is_alive():
            self.audio_daemon.start()
        return self.get_session()

    def get_session(self):
        if hasattr(self.mumble, 'users') and hasattr(self.mumble.users, 'myself_session') and self.mumble.users.myself_session is not None:
            session = copy.copy(self.mumble.users[self.mumble.users.myself_session]) 
            session['host'] = self.mumble.host
            session['port'] = self.mumble.port
            return session
        return None


    def disconnect(self):
        '''Disconnect from Mumble Server and tell the audio daemon to stop'''
        self.mumble.stop()
        self.active = False
        # close the stream and pyaudio instance
        self.stream.stop_stream()
        self.stream.close()
        self.pyAudio.terminate()
        self.mumble = pymumble_py3.Mumble(host=self.server, user=self.nick, password=self.pwd, port=self.port, reconnect=True)