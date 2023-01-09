from lib.mumble.client import MumbleClient
from lib.helper import is_int
from json import JSONDecodeError
from pathlib import Path
from queue import Queue
from ssdpy import SSDPServer
import socket
import sys

from flask import Flask, Response, json, request

import threading, time, pymumble_py3, uuid

client = MumbleClient()

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
            cfg_io.write(json.dumps(CONFIGURATION, indent=4))
    except Exception as e:
        print("Error saving config file {file}".format(file=CFG_FILE.absolute()))

FLASK_PORT=int(sys.argv[1]) if len(sys.argv) >= 2 and is_int(sys.argv[1]) and int(sys.argv[1]) > 1000 else CONFIGURATION['flask_port']


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
# Voice API Calls
# ------------------------------------------------------------------------------------------


@api.route('/rt-box/voice', methods=['GET'], strict_slashes=False)
def ROUTE_get_voice_overview():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    voice = get_voice_status()
    return Response(json.dumps({'voice': voice}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/voice/connect', methods=['GET'])
def connect_client():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
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
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
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
# Functions
# ------------------------------------------------------------------------------------------

def get_status():
    voice = get_voice_status()
    return voice

def get_voice_status():
    voice = client.get_session()
    if voice is None:
        voice = {'status': 'disconnected'}
    else:
        voice['status'] = 'connected'
    return voice

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

if __name__ == '__main__':
    flask_thread = threading.Thread(target=api.run, args=('0.0.0.0', FLASK_PORT), daemon=True)
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
            time.sleep(0.5)
            exit()
        cmd['processed'] = True
    time.sleep(0.5)
