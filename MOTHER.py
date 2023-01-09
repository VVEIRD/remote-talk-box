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

FLASK_PORT = CONFIGURATION['flask_port']


LED_PROCESS = None
ENDPOINT_STATUS = {'led': None, 'audio': None, 'voice': None}

AUDIO_PROCESS = None

VOICE_PROCESS = None

# ------------------------------------------------------------------------------------------
# Autostart subprocesses
# ------------------------------------------------------------------------------------------

if CONFIGURATION['led_process']:
    py_script = str(Path('LedProcess.py').resolve())
    port = FLASK_PORT + 1
    agrs = ['python', py_script, str(port)]
    LED_PROCESS = subprocess.Popen(agrs, shell=CONFIGURATION['use_shell'])

if CONFIGURATION['audio_process']:
    py_script = str(Path('AudioProcess.py').resolve())
    port = FLASK_PORT + 2
    agrs = ['python', py_script, str(port)]
    AUDIO_PROCESS = subprocess.Popen(agrs, shell=CONFIGURATION['use_shell'])

if CONFIGURATION['voice_process']:
    py_script = str(Path('VoiceProcess.py').resolve())
    port = FLASK_PORT + 3
    agrs = ['python', py_script, str(port)]
    VOICE_PROCESS = subprocess.Popen(agrs, shell=CONFIGURATION['use_shell'])

print('------------------ 1 -----------------')

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

print('------------------ 2 -----------------')

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

print('------------------ 3 -----------------')

# ------------------------------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------------------------------

def is_process_running(process):
    return process is not None and process.poll() is None

def get_status():
    voice = get_voice_process_status()
    led_status= get_led_process_status()
    audio = get_audio_process_status()
    return {'voice': voice, 'led': led_status, 'audio': audio}
    return AUDIO_STATUS

def get_led_process_status():
    if not is_process_running(LED_PROCESS):
        return {'status': 'offline'}
    return ENDPOINT_STATUS['led']

def get_audio_process_status():
    if not is_process_running(AUDIO_PROCESS):
        return {'status': 'offline'}
    return ENDPOINT_STATUS['audio']

# TODO create status functions
def get_voice_process_status():
    if not is_process_running(VOICE_PROCESS):
        return {'status': 'offline'}
    return ENDPOINT_STATUS['voice']

def exit_handler():
    if LED_PROCESS is not None:
        LED_PROCESS.terminate()
    if AUDIO_PROCESS is not None:
        AUDIO_PROCESS.terminate()
    if VOICE_PROCESS is not None:
        VOICE_PROCESS.terminate()

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
    led_url   = "http://{ip_addr}:{port}/rt-box".format(ip_addr=IPAddr, port=FLASK_PORT+1)
    audio_url = "http://{ip_addr}:{port}/rt-box".format(ip_addr=IPAddr, port=FLASK_PORT+2)
    voice_url = "http://{ip_addr}:{port}/rt-box".format(ip_addr=IPAddr, port=FLASK_PORT+3)
    while DAEMON_RUNNING and not run_once:
        if is_process_running(LED_PROCESS):
            response = requests.get(led_url, cookies=cookies)
            if response.status_code == 200:
                status = response.json()
                status['last_update'] = datetime.now().isoformat()
            else:
                status = {'status': 'process not reachable', 'last_update': datetime.now()}
            ENDPOINT_STATUS['led'] = status
        if is_process_running(AUDIO_PROCESS):
            response = requests.get(audio_url, cookies=cookies)
            if response.status_code == 200:
                status = response.json()
                status['last_update'] = datetime.now().isoformat()
            else:
                status = {'status': 'process not reachable', 'last_update': datetime.now()}
            ENDPOINT_STATUS['audio'] = status
        if is_process_running(VOICE_PROCESS):
            response = requests.get(voice_url, cookies=cookies)
            if response.status_code == 200:
                status = response.json()
                status['last_update'] = datetime.now().isoformat()
            else:
                status = {'status': 'process not reachable', 'last_update': datetime.now()}
            ENDPOINT_STATUS['voice'] = status
        time.sleep(.75)

time.sleep(1)
_status_updater(True)

STATUS_UPDATER_DAEMON = threading.Thread(target=_status_updater, daemon=True)
STATUS_UPDATER_DAEMON.start()

print('------------------ 5 -----------------')

time.sleep(5)
print('-------------------------------------')
print("LED Process:   " + str(LED_PROCESS))
po = LED_PROCESS.poll()
print("LED Poll:      " + str(len(po) if po is not None else po))
print("is Running:    " + str(is_process_running(LED_PROCESS)))
print('-------------------------------------')
print("Audio Process: " + str(AUDIO_PROCESS))
po = AUDIO_PROCESS.poll()
print("Audio Poll:    " + str(len(po) if po is not None else po))
print("is Running:    " + str(is_process_running(AUDIO_PROCESS)))
print('-------------------------------------')
print("Voice Process: " + str(VOICE_PROCESS))
po = VOICE_PROCESS.poll()
print("Voice Poll:    " + str(len(po) if po is not None else po))
print("is Running:    " + str(is_process_running(VOICE_PROCESS)))
print('-------------------------------------')

print('------------------ 6 -----------------')

# Process connect and disconnect commands
while True:
    cmd = cmd_queue.get()
    if cmd is not None:
        if cmd['action'] ==  'shutdown':
            time.sleep(1)
            exit()
        cmd['processed'] = True
    time.sleep(0.5)
