import lib.audio.AudioFacade as AudioFacade
from lib.helper import is_int
from json import JSONDecodeError
from pathlib import Path
from queue import Queue
from ssdpy import SSDPServer
import socket
import sys

from flask import Flask, flash, Response, json, request

import threading, time

cmd_queue = Queue()

CONFIGURATION = {}


# ------------------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------------------

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

CFG_FILE = Path('data', 'configuration.json')

with CFG_FILE.open(mode='r', encoding="utf8") as cfg_io:
    try:
        CONFIGURATION = json.loads(cfg_io.read())
        print(CONFIGURATION)
    except JSONDecodeError as e:
        print("Error loading config file {file}".format(file=CFG_FILE.absolute()))

def saveConfiguration():
    try:
        with CFG_FILE.open(mode='w', encoding="utf8") as cfg_io:
            cfg_io.write(json.dumps(CONFIGURATION))
    except Exception as e:
        print("Error saving config file {file}".format(file=CFG_FILE.absolute()))

FLASK_PORT = int(sys.argv[1]) if len(sys.argv) >= 2 and is_int(sys.argv[1]) and int(sys.argv[1]) > 1000 else CONFIGURATION['flask_port']
print(sys.argv)
# ------------------------------------------------------------------------------------------
# Discoverability with SSDP
# ------------------------------------------------------------------------------------------


# Get IP Adress
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
IPAddr=s.getsockname()[0]
# Init SSDP Server
# Old name: "remote-talk-box-" + str(uuid.getnode())
server = SSDPServer(CONFIGURATION['name'], device_type="remote-box-client", location='http://{ipaddr}:{port}/rt-box'.format(ipaddr=IPAddr, port=FLASK_PORT))
ssdp_daemon = threading.Thread(target=server.serve_forever, args=(), daemon=True)
ssdp_daemon.start()


# ------------------------------------------------------------------------------------------
# API Calls
# ------------------------------------------------------------------------------------------

api = Flask(__name__)

@api.route('/rt-box', methods=['GET'], strict_slashes=False)
def get_overview():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    return Response(json.dumps(get_status(), indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/shutdown', methods=['GET'])
def shutdown_client():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    cmd = {}
    cmd['action'] = 'shutdown'
    cmd_queue.put(cmd)
    return Response(json.dumps({'shutdown': True}, indent=4), status=200, mimetype='application/json')


# ------------------------------------------------------------------------------------------
# AUDIO API Calls
# ------------------------------------------------------------------------------------------

@api.route('/rt-box/audio', methods=['GET'], strict_slashes=False)
def _get_audio_status():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    return Response(json.dumps({'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/play/<audio_file>', methods=['GET'])
def _play_audio(audio_file):
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    try:
        AudioFacade.play_audio_file(name=audio_file)
        time.sleep(0.3)
    except ValueError as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'Audio queued', 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/flush', methods=['GET'])
def _flush_queue():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    AudioFacade.flush_queue()
    return Response(json.dumps({'status': 'Queue flushed', 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/stop', methods=['GET'])
def _stop_playback():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    try:
        AudioFacade.stop_playback()
    except Exception as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'Playback stopped', 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ['wav']

@api.route('/rt-box/audio/upload/<file_name>', methods=['POST'])
def upload_file(file_name):
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            return Response(json.dumps({'status': 'No file provided'}, indent=4), status=400, mimetype='application/json')
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return Response(json.dumps({'status': 'Empty file provided'}, indent=4), status=400, mimetype='application/json')
        if file and allowed_file(file.filename):
            file_name = file_name.replace(' ', '-') + ".wav"
            file.save(AudioFacade.get_audio_folder(), file_name)
            return Response(json.dumps({'status': 'File uploaded', 'file_name': file_name}, indent=4), status=200, mimetype='application/json')
        return Response(json.dumps({'status': 'File not a wav file'}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'No file provided'}, indent=4), status=400, mimetype='application/json')

@api.route('/rt-box/audio/random/add/<name>', methods=['GET'])
def _add_random_playback(name):
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    try:
        AudioFacade.add_random_playback(name)
    except Exception as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': '{audio} added'.format(audio=name), 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/random/remove/<name>', methods=['GET'])
def _remove_random_playback(name):
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    try:
        AudioFacade.remove_random_playback(name)
    except Exception as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': '{audio} removed'.format(audio=name), 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/random/stop', methods=['GET'])
def _stop_random_playback():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    try:
        AudioFacade.stop_random_playback()
    except Exception as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'Random playback stopped', 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/random/disable', methods=['GET'])
def _disable_random_playback():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    try:
        AudioFacade.disable_random_playback()
    except Exception as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'Random playback disabled', 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/random/enable', methods=['GET'])
def _enable_random_playback():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    try:
        AudioFacade.enable_random_playback()
    except Exception as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'Random playback enabled', 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

# ------------------------------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------------------------------

def get_status():
    audio = get_audio_status()
    return audio

def get_audio_status():
    audio_status = AudioFacade.get_audio_status()
    audio_files = AudioFacade.get_audio_files()
    random_playback = AudioFacade.get_random_playback()
    audio_config = {'status': audio_status, 'audio_files': audio_files, 'random_playback': random_playback}
    return audio_config

if __name__ == '__main__':
    flask_thread = threading.Thread(target=api.run, args=('0.0.0.0', FLASK_PORT), daemon=True)
    flask_thread.start()


# Process shutdown command
while True:
    cmd = cmd_queue.get()
    if cmd is not None:
        if cmd['action'] ==  'shutdown':
            time.sleep(0.5)
            exit()
        cmd['processed'] = True
    time.sleep(0.5)
