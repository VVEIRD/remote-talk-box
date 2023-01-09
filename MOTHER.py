from json import JSONDecodeError
from pathlib import Path
from queue import Queue
from ssdpy import SSDPServer
import socket
import requests
from datetime import datetime
from flask import Flask, Response, json, request

import threading, time, subprocess, atexit


cmd_queue = Queue()

FLASK_PORT=5020

CONFIGURATION = {}

# ------------------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------------------

# Get IP Adress
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
IPAddr=s.getsockname()[0]

# Load Configuration file
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

FLASK_PORT = CONFIGURATION['flask_port']

PROCESSES = {'led': None, 'audio': None, 'voice': None}

ENDPOINT_STATUS = {'led': None, 'audio': None, 'voice': None}

ENDPOINTS = {
    'led':   'http://{ip_addr}:{port}/rt-box'.format(ip_addr=IPAddr, port=FLASK_PORT+1),
    'audio': 'http://{ip_addr}:{port}/rt-box'.format(ip_addr=IPAddr, port=FLASK_PORT+2),
    'voice': 'http://{ip_addr}:{port}/rt-box'.format(ip_addr=IPAddr, port=FLASK_PORT+3),
}

# ------------------------------------------------------------------------------------------
# Autostart subprocesses
# ------------------------------------------------------------------------------------------

if CONFIGURATION['led_process']:
    py_script = str(Path('LedProcess.py').resolve())
    port = FLASK_PORT + 1
    agrs = ['python', py_script, str(port)]
    PROCESSES['led'] = subprocess.Popen(agrs, shell=CONFIGURATION['use_shell'])

if CONFIGURATION['audio_process']:
    py_script = str(Path('AudioProcess.py').resolve())
    port = FLASK_PORT + 2
    agrs = ['python', py_script, str(port)]
    PROCESSES['audio'] = subprocess.Popen(agrs, shell=CONFIGURATION['use_shell'])

if CONFIGURATION['voice_process']:
    py_script = str(Path('VoiceProcess.py').resolve())
    port = FLASK_PORT + 3
    agrs = ['python', py_script, str(port)]
    PROCESSES['voice'] = subprocess.Popen(agrs, shell=CONFIGURATION['use_shell'])

print('------------------ 1 -----------------')

# ------------------------------------------------------------------------------------------
# Discoverability with SSDP
# ------------------------------------------------------------------------------------------

# Init SSDP Server
# Old name: "remote-talk-box-" + str(uuid.getnode())
server = SSDPServer(CONFIGURATION['name'], device_type="remote-box-client", location='http://{ipaddr}:{port}/rt-box'.format(ipaddr=IPAddr, port=FLASK_PORT))
ssdp_daemon = threading.Thread(target=server.serve_forever, args=(), daemon=True)
ssdp_daemon.start()

print('------------------ 2 -----------------')

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

print('------------------ 3 -----------------')

# ------------------------------------------------------------------------------------------
# Startup API Calls
# ------------------------------------------------------------------------------------------

@api.route('/rt-box/led/startup', methods=['GET'])
def startup_led():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    if not is_process_running(PROCESSES['led']):
        py_script = str(Path('LedProcess.py').resolve())
        port = FLASK_PORT + 1
        agrs = ['python', py_script, str(port)]
        PROCESSES['led'] = subprocess.Popen(agrs, shell=CONFIGURATION['use_shell'])
        return Response(json.dumps({'status': 'LED process started'}, indent=4), status=200, mimetype='application/json')
    return Response(json.dumps({'status': 'LED process started'}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/startup', methods=['GET'])
def startup_audio():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    if not is_process_running(PROCESSES['audio']):
        py_script = str(Path('AudioProcess.py').resolve())
        port = FLASK_PORT + 2
        agrs = ['python', py_script, str(port)]
        PROCESSES['audio'] = subprocess.Popen(agrs, shell=CONFIGURATION['use_shell'])
        return Response(json.dumps({'status': 'Audio process started'}, indent=4), status=200, mimetype='application/json')
    return Response(json.dumps({'status': 'Audio process started'}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/voice/startup', methods=['GET'])
def startup_voice():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    if not is_process_running(PROCESSES['voice']):
        py_script = str(Path('VoiceProcess.py').resolve())
        port = FLASK_PORT + 3
        agrs = ['python', py_script, str(port)]
        PROCESSES['voice'] = subprocess.Popen(agrs, shell=CONFIGURATION['use_shell'])
        return Response(json.dumps({'status': 'Voice process started'}, indent=4), status=200, mimetype='application/json')
    return Response(json.dumps({'status': 'Voice process started'}, indent=4), status=200, mimetype='application/json')


# ------------------------------------------------------------------------------------------
# Shutdown API Calls
# ------------------------------------------------------------------------------------------

@api.route('/rt-box/led/shutdown', methods=['GET'])
def shutdown_led():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    force = True if request.args.get(key='force', default="", type=str).lower() == "true" else False
    if is_process_running(PROCESSES['led']):
        # Try gracefull termination
        succ = call_shutdown_endpoint('led')
        if force:
            PROCESSES['led'].terminate()
        PROCESSES['led'] = None
        if succ:
            return Response(json.dumps({'status': 'LED process killed'}, indent=4), status=200, mimetype='application/json')
    return Response(json.dumps({'status': 'LED process not killed'}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/audio/shutdown', methods=['GET'])
def shutdown_audio():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    force = True if request.args.get(key='force', default="", type=str).lower() == "true" else False
    if is_process_running(PROCESSES['audio']):
        # Try gracefull termination
        succ = call_shutdown_endpoint('audio')
        if force:
            PROCESSES['audio'].terminate()
        PROCESSES['audio'] = None
        if succ:
            return Response(json.dumps({'status': 'Audio process killed'}, indent=4), status=200, mimetype='application/json')
    return Response(json.dumps({'status': 'Audio process not killed'}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/voice/shutdown', methods=['GET'])
def shutdown_voice():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    force = True if request.args.get(key='force', default="", type=str).lower() == "true" else False
    if is_process_running(PROCESSES['voice']):
        # Try gracefull termination
        succ = call_shutdown_endpoint('voice')
        if force:
            PROCESSES['voice'].terminate()
        PROCESSES['voice'] = None
        if succ:
            return Response(json.dumps({'status': 'Voice process killed'}, indent=4), status=200, mimetype='application/json')
    return Response(json.dumps({'status': 'Voice process not killed'}, indent=4), status=200, mimetype='application/json')


# ------------------------------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------------------------------

def is_process_running(process):
    return process is not None and process.poll() is None

def get_status():
    voice = get_voice_process_status()
    led_status= get_led_process_status()
    audio = get_audio_process_status()
    processes = {}
    endpoints = {}
    processes['led']   = 'online' if is_process_running(PROCESSES['led']) else 'offline'
    processes['audio'] = 'online' if is_process_running(PROCESSES['audio']) else 'offline'
    processes['voice'] = 'online' if is_process_running(PROCESSES['voice']) else 'offline'
    status = {'voice': voice, 'led': led_status, 'audio': audio, 'endpoints': endpoints, 'processes': processes}
    if is_process_running(PROCESSES['led']):
        endpoints['led'] = ENDPOINTS['led']
    if is_process_running(PROCESSES['audio']):
        endpoints['audio'] = ENDPOINTS['audio']
    if is_process_running(PROCESSES['voice']):
        endpoints['voice'] = ENDPOINTS['voice']
    return status

def get_led_process_status():
    if not is_process_running(PROCESSES['led']):
        return None
    return ENDPOINT_STATUS['led']

def get_audio_process_status():
    if not is_process_running(PROCESSES['audio']):
        return None
    return ENDPOINT_STATUS['audio']

# TODO create status functions
def get_voice_process_status():
    if not is_process_running(PROCESSES['voice']):
        return None
    return ENDPOINT_STATUS['voice']

def call_shutdown_endpoint(endpointName:str):
    if endpointName in PROCESSES:
        cookies = {'accessToken': CONFIGURATION['secret']}
        ep = ENDPOINTS[endpointName] + '/shutdown'
        response = requests.get(ep, cookies=cookies)
        if response.status_code == 200:
            return True
    return False

def exit_handler():
    if PROCESSES['led'] is not None:
        PROCESSES['led'].terminate()
    if PROCESSES['audio'] is not None:
        PROCESSES['audio'].terminate()
    if PROCESSES['voice'] is not None:
        PROCESSES['voice'].terminate()

atexit.register(exit_handler)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=api.run, args=('0.0.0.0', FLASK_PORT), daemon=True)
    flask_thread.start()

print('------------------ 4 -----------------')

# ------------------------------------------------------------------------------------------
# Daemons
# ------------------------------------------------------------------------------------------

DAEMON_RUNNING = True

def _status_updater(run_once=False):
    cookies = {'accessToken': CONFIGURATION['secret']}
    while DAEMON_RUNNING and not run_once:
        try:
            if is_process_running(PROCESSES['led']):
                response = requests.get(ENDPOINTS['led'], cookies=cookies)
                if response.status_code == 200:
                    status = response.json()
                    status['last_update'] = datetime.now().isoformat()
                else:
                    status = {'status': 'process not reachable', 'last_update': datetime.now()}
                ENDPOINT_STATUS['led'] = status
            if is_process_running(PROCESSES['audio']):
                response = requests.get(ENDPOINTS['audio'], cookies=cookies)
                if response.status_code == 200:
                    status = response.json()
                    status['last_update'] = datetime.now().isoformat()
                else:
                    status = {'status': 'process not reachable', 'last_update': datetime.now()}
                ENDPOINT_STATUS['audio'] = status
            if is_process_running(PROCESSES['voice']):
                response = requests.get(ENDPOINTS['voice'], cookies=cookies)
                if response.status_code == 200:
                    status = response.json()
                    status['last_update'] = datetime.now().isoformat()
                else:
                    status = {'status': 'process not reachable', 'last_update': datetime.now()}
                ENDPOINT_STATUS['voice'] = status
        except Exception as e:
            print("Error getting status update")
            print(e)
        time.sleep(.75)

time.sleep(1)
_status_updater(True)

STATUS_UPDATER_DAEMON = threading.Thread(target=_status_updater, daemon=True)
STATUS_UPDATER_DAEMON.start()

print('------------------ 5 -----------------')

time.sleep(1)
print('-------------------------------------')
print("LED Process:   " + str(PROCESSES['led']))
po = PROCESSES['led'].poll()
print("LED Poll:      " + str(len(po) if po is not None else po))
print("is Running:    " + str(is_process_running(PROCESSES['led'])))
print('-------------------------------------')
print("Audio Process: " + str(PROCESSES['audio']))
po = PROCESSES['audio'].poll()
print("Audio Poll:    " + str(len(po) if po is not None else po))
print("is Running:    " + str(is_process_running(PROCESSES['audio'])))
print('-------------------------------------')
print("Voice Process: " + str(PROCESSES['voice']))
po = PROCESSES['voice'].poll()
print("Voice Poll:    " + str(len(po) if po is not None else po))
print("is Running:    " + str(is_process_running(PROCESSES['voice'])))
print('-------------------------------------')

print('------------------ 6 -----------------')

# Process connect and disconnect commands
while True:
    cmd = cmd_queue.get()
    if cmd is not None:
        if cmd['action'] ==  'shutdown':
            time.sleep(0.5)
            exit()
        cmd['processed'] = True
    time.sleep(0.5)
