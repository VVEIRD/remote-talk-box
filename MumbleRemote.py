from lib.mumble.client import MumbleClient
import lib.blink.BlinkFacade as BlinkFacade
from queue import Queue
from ssdpy import SSDPServer
import socket, atexit

from flask import Flask, Response, json, request

import threading, time, pymumble_py3, uuid

client = MumbleClient()

cmd_queue = Queue()

FLASK_PORT=5020

# ------------------------------------------------------------------------------------------
# Discoverability with SSDP
# ------------------------------------------------------------------------------------------

# Get IP Adress
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
IPAddr=s.getsockname()[0]
# Init SSDP Server
server = SSDPServer("remote-talk-box-" + str(uuid.getnode()), device_type="mumble-remote-client", location='http://{ipaddr}:{port}/rt-box'.format(ipaddr=IPAddr, port=FLASK_PORT))
ssdp_daemon = threading.Thread(target=server.serve_forever, args=(), daemon=True)
ssdp_daemon.start()


# ------------------------------------------------------------------------------------------
# API Calls
# ------------------------------------------------------------------------------------------

api = Flask(__name__)

@api.route('/rt-box', methods=['GET'])
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

@api.route('/rt-box/led', methods=['GET'])
def leds_status():
    leds = BlinkFacade.get_devices()
    blinks = BlinkFacade.get_blinks()
    return Response(json.dumps({'devices': leds, 'blinks': blinks}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/led/play', methods=['GET'])
def play_blink():
    name = request.args.get('name')
    endless = request.args.get(key='endless', default=False, type=bool)
    try:
        BlinkFacade.play_blink(name=name, endless=endless)
    except ValueError as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'blink queued'}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/blinks', methods=['GET'])
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


# ------------------------------------------------------------------------------------------
# Voice API Calls
# ------------------------------------------------------------------------------------------

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
#  http://127.0.0.1:5020/rt-box/connect?host=localhost&port=12000&username=ai-cube-1&password=Asdf1234
# URL to disconnect:
#  http://127.0.0.1:5020/rt-box/disconnect
# URL to Shutdown Client:
#  http://127.0.0.1:5020/rt-box/shutdown

if __name__ == '__main__':
    flask_thread = threading.Thread(target=api.run, args=('0.0.0.0', FLASK_PORT), daemon=True)
    flask_thread.start()

# ------------------------------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------------------------------

def get_status():
    voice = client.get_session()
    if voice is None:
        voice = {'status': 'disconnected'}
    else:
        voice['status'] = 'connected'
    leds = BlinkFacade.get_devices()
    blinks = BlinkFacade.get_blinks()
    return {'voice': voice, 'leds': {'devices': leds, 'blinks': blinks}}

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
    return Response(json.dumps(get_status(), indent=4), status=200, mimetype='application/json')

def disconnect_from_server():
    try:
        client.disconnect()
    except Exception as e:
        print(e)
        return Response(json.dumps(get_status(), indent=4), status=400, mimetype='application/json')
    return Response(json.dumps(get_status(), indent=4), status=200, mimetype='application/json')



def exit_handler():
    BlinkFacade.stop()

atexit.register(exit_handler)

# Process connect and disconnect commands
while True:
    cmd = cmd_queue.get()
    if cmd is not None:
        if cmd['action'] ==  'connect':
            cmd['result'] = connect_to_server(cmd['host'], cmd['port'], cmd['username'], cmd['password'])
            if cmd['result']  is None:
                cmd['result'] = Response(json.dumps(get_status(), indent=4), status=500, mimetype='application/json')
        if cmd['action'] ==  'disconnect':
            cmd['result'] = disconnect_from_server()
            if cmd['result']  is None:
                cmd['result'] = Response(json.dumps(get_status(), indent=4), status=500, mimetype='application/json')
        if cmd['action'] ==  'shutdown':
            time.sleep(1)
            exit()
        cmd['processed'] = True
    time.sleep(0.5)