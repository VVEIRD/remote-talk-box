from lib.mumble.client import MumbleClient
import lib.blink.BlinkFacade as BlinkFacade
import lib.audio.AudioFacade as AudioFacade
from json import JSONDecodeError
from pathlib import Path
from lib.blink.blinker import BlinkTypes, Blink
from queue import Queue
from ssdpy import SSDPServer
import socket, atexit
import traceback

from flask import Flask, Response, json, request

import threading, time, pymumble_py3, uuid

client = MumbleClient()

cmd_queue = Queue()

FLASK_PORT=5020

CONFIGURATION = {}

# ------------------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------------------
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
            cfg_io.write(json.dumps(CONFIGURATION), indent=4)
    except Exception as e:
        print("Error saving config file {file}".format(file=CFG_FILE.absolute()))


# ------------------------------------------------------------------------------------------
# Discoverability with SSDP
# ------------------------------------------------------------------------------------------

# Get IP Adress
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
IPAddr=s.getsockname()[0]
# Init SSDP Server
# Old name: "remote-talk-box-" + str(uuid.getnode())
server = SSDPServer(CONFIGURATION['name'], device_type="remote-box-client", location='http://{ipaddr}:{port}/rt-box'.format(ipaddr=IPAddr, port=CONFIGURATION['flask_port']))
ssdp_daemon = threading.Thread(target=server.serve_forever, args=(), daemon=True)
ssdp_daemon.start()


# ------------------------------------------------------------------------------------------
# API Calls
# ------------------------------------------------------------------------------------------

api = Flask(__name__)

@api.route('/rt-box', methods=['GET'], strict_slashes=False)
def get_overview():
    return Response(json.dumps(get_status(), indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/shutdown', methods=['GET'])
def shutdown_client():
    cmd = {}
    cmd['action'] = 'shutdown'
    cmd_queue.put(cmd)
    return Response(json.dumps({'shutdown': True}, indent=4), status=200, mimetype='application/json')


# ------------------------------------------------------------------------------------------
# LED API Calls
# ------------------------------------------------------------------------------------------

@api.route('/rt-box/leds', methods=['GET'], strict_slashes=False)
def leds_status():
    led_status = get_led_status()
    return Response(json.dumps({'led': led_status}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/led/device/<device_name>', methods=['GET'])
def led_device_status(device_name):
    led_Device = BlinkFacade.get_device(device_name)
    return Response(json.dumps(led_Device, indent=4), status=200, mimetype='application/json')


@api.route('/rt-box/led/device/<device_name>/play/<name>', methods=['GET'])
def play_blink(name, device_name, endless=False):
    endless = True if request.args.get(key='endless', default="", type=str).lower() == "true" else False
    print("Endless: {end}".format(end=endless))
    try:
        BlinkFacade.play_blink(name=name, device=device_name, endless=endless)
    except ValueError as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'blink queued'}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/led/device/<device>/stop', methods=['GET'])
def stop_blink(device):
    endless = False
    try:
        BlinkFacade.stop_animation(device_name=device)
    except ValueError as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'stopping animation queued'}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/led/play/<name>', methods=['GET'])
def play_blink_2(name):
    device = request.args.get(key='device', default=None, type=str)
    endless = True if request.args.get(key='endless', default="", type=str).lower() == "true" else False
    print("Endless: {end}".format(end=endless))
    return play_blink(name=name, device_name=device, endless=endless)

@api.route('/rt-box/led/play', methods=['GET'])
def play_blink_3():
    name = request.args.get('name')
    device = request.args.get(key='device', default=None, type=str)
    endless = request.args.get(key='endless', default=False, type=bool)
    return play_blink(name, device=device, endless=endless)

@api.route('/rt-box/led/stop', methods=['GET'])
def stop_blink_2():
    device = request.args.get(key='device', default=None, type=str)
    return stop_blink(device)

@api.route('/rt-box/blinks', methods=['GET'], strict_slashes=False)
def get_blinks():
    blinks = BlinkFacade.get_blinks()
    return Response(json.dumps(blinks, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/blink/<blink_name>', methods=['GET'])
def get_blink(blink_name):
    blink = BlinkFacade.get_blink(blink_name)
    if blink is not None:
        return Response(blink.to_json(), status=200, mimetype='application/json')
    else:
        return Response(json.dumps({'error': 'A blink with the name {name} does not exist'.format(name=blink_name)}, indent=4), status=400, mimetype='application/json')

@api.route('/rt-box/blink/<blink_name>', methods=['PUT'])
def update_blink(blink_name):
    old_blink = BlinkFacade.get_blink(blink_name)
    try:
        new_blink = Blink.from_json(request.data)
        BlinkFacade.save_blink(blink_name, new_blink)
        if old_blink is None:
            return Response(json.dumps({'status': 'blink saved', 'new': new_blink.to_dict()}, indent=4), status=200, mimetype='application/json')
        return Response(json.dumps({'status': 'blink saved', 'new': new_blink.to_dict(), 'old': old_blink.to_dict()}, indent=4), status=200, mimetype='application/json')
    except Exception as e:
        print('--JSON -------------------------------------------------------')
        print (json.dumps({'error': str(e)}, indent=4))
        print(request.data)
        print('--TRACE ------------------------------------------------------')
        print(traceback.format_exc())
        print('--------------------------------------------------------------')
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')

# ------------------------------------------------------------------------------------------
# Voice API Calls
# ------------------------------------------------------------------------------------------

@api.route('/rt-box/voice', methods=['GET'], strict_slashes=False)
def ROUTE_get_voice_overview():
    voice = get_voice_status()
    return Response(json.dumps({'voice': voice}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/voice/connect', methods=['GET'])
def connect_client():
    host = request.args.get('host')
    port = request.args.get('port')
    try:
        # try converting to integer
        port = int(port)
    except ValueError:
        port = 64738
    username = request.args.get('username')
    password = request.args.get('password')
    cmd = {}
    cmd['action'] = 'connect'
    cmd['host'] = host
    cmd['port'] = port
    cmd['username'] = username
    cmd['password'] = password
    cmd['processed'] = False
    cmd_queue.put(cmd)
    while not cmd['processed']:
        time.sleep(0.2)
    if json.loads(cmd['result'].get_data())['status'] == 'connected':
        CONFIGURATION['host'] = host
        CONFIGURATION['port'] = port
        CONFIGURATION['username'] = username
        CONFIGURATION['password'] = password
        saveConfiguration()
    return cmd['result']

@api.route('/rt-box/voice/disconnect', methods=['GET'])
def disconnect_client():
    cmd = {}
    cmd['action'] = 'disconnect'
    cmd['processed'] = False
    cmd_queue.put(cmd)
    while not cmd['processed']:
        time.sleep(0.2)
    print(cmd['result'])
    return cmd['result']

# URL to Connect to locallhost:
#  http://127.0.0.1:5020/rt-box/voice/connect?host=localhost&port=12000&username=ai-cube-1&password=Asdf1234
# URL to disconnect:
#  http://127.0.0.1:5020/rt-box/voice/disconnect
# URL to Shutdown Client:
#  http://127.0.0.1:5020/rt-box/shutdown


# ------------------------------------------------------------------------------------------
# AUDIO API Calls
# ------------------------------------------------------------------------------------------

@api.route('/rt-box/audio', methods=['GET'], strict_slashes=False)
def _get_audio_status():
    return Response(json.dumps({'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/play/<audio_file>', methods=['GET'])
def _play_audio(audio_file):
    try:
        AudioFacade.play_audio_file(name=audio_file)
        time.sleep(0.3)
    except ValueError as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'Audio queued', 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/flush', methods=['GET'])
def _flush_queue():
    AudioFacade.flush_queue()
    return Response(json.dumps({'status': 'Queue flushed', 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/stop', methods=['GET'])
def _stop_playback():
    try:
        AudioFacade.stop_playback()
    except Exception as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'Playback stopped', 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/random/add/<name>', methods=['GET'])
def _add_random_playback(name):
    try:
        AudioFacade.add_random_playback(name)
    except Exception as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': '{audio} added'.format(audio=name), 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/random/remove/<name>', methods=['GET'])
def _remove_random_playback(name):
    try:
        AudioFacade.remove_random_playback(name)
    except Exception as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': '{audio} removed'.format(audio=name), 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/random/stop', methods=['GET'])
def _stop_random_playback():
    try:
        AudioFacade.stop_random_playback()
    except Exception as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'Random playback stopped', 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/random/disable', methods=['GET'])
def _disable_random_playback():
    try:
        AudioFacade.disable_random_playback()
    except Exception as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'Random playback disabled', 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/random/enable', methods=['GET'])
def _enable_random_playback():
    try:
        AudioFacade.enable_random_playback()
    except Exception as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'Random playback enabled', 'audio': get_audio_status()}, indent=4), status=200, mimetype='application/json')

# ------------------------------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------------------------------

def get_status():
    voice = get_voice_status()
    led_status= get_led_status()
    audio = get_audio_status()
    return {'voice': voice, 'led': led_status, 'audio': audio}

def get_voice_status():
    voice = client.get_session()
    if voice is None:
        voice = {'status': 'disconnected'}
    else:
        voice['status'] = 'connected'
    return voice

def get_led_status():
    leds = BlinkFacade.get_devices()
    blinks = BlinkFacade.get_blinks()
    return {'devices': leds, 'blinks': blinks}

def get_audio_status():
    audio_status = AudioFacade.get_audio_status()
    audio_files = AudioFacade.get_audio_files()
    random_playback = AudioFacade.get_random_playback()
    audio_config = {'status': audio_status, 'audio_files': audio_files, 'random_playback': random_playback}
    return audio_config

def connect_to_server(host, port, username, password):
    try:
        client.connect(host=host, username=username, pwd=password, port=port)
    except Exception as e:
        print(e)
        return Response(json.dumps({'error': 'internal server error'}, indent=4), status=500, mimetype='application/json')
    except pymumble_py3.errors.ConnectionRejectedError as e:
        print(e)
        return Response(json.dumps({'error': 'invalid password, connection refused'}, indent=4), status=401, mimetype='application/json')
    except:
        return Response(json.dumps({'error': 'internal server error'}, indent=4), status=500, mimetype='application/json')
    return Response(json.dumps(get_voice_status(), indent=4), status=200, mimetype='application/json')

def disconnect_from_server():
    try:
        client.disconnect()
    except Exception as e:
        print(e)
        return Response(json.dumps(get_voice_status(), indent=4), status=400, mimetype='application/json')
    return Response(json.dumps(get_voice_status(), indent=4), status=200, mimetype='application/json')



def exit_handler():
    BlinkFacade.shutdown()

atexit.register(exit_handler)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=api.run, args=('0.0.0.0', CONFIGURATION['flask_port']), daemon=True)
    flask_thread.start()

# Autoconnect to voice server

if "host" in CONFIGURATION and "username" in CONFIGURATION and "password" in CONFIGURATION and "port" in CONFIGURATION:
    cmd = {}
    cmd['action']   = 'connect'
    cmd['host']     = CONFIGURATION['host']
    cmd['username'] = CONFIGURATION['username']
    cmd['port']     = CONFIGURATION['port']
    cmd['password'] = CONFIGURATION['password']
    cmd['processed'] = False
    cmd_queue.put(cmd)

# Process connect and disconnect commands
while True:
    cmd = cmd_queue.get()
    if cmd is not None:
        if cmd['action'] ==  'connect':
            cmd['result'] = connect_to_server(cmd['host'], cmd['port'], cmd['username'], cmd['password'])
            if cmd['result']  is None:
                cmd['result'] = Response(json.dumps(get_voice_status(), indent=4), status=500, mimetype='application/json')
        if cmd['action'] ==  'disconnect':
            cmd['result'] = disconnect_from_server()
            if cmd['result']  is None:
                cmd['result'] = Response(json.dumps(get_voice_status(), indent=4), status=500, mimetype='application/json')
        if cmd['action'] ==  'shutdown':
            time.sleep(1)
            exit()
        cmd['processed'] = True
    time.sleep(0.5)
