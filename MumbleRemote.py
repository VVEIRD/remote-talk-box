from lib.mumble.client import MumbleClient
from queue import Queue
from ssdpy import SSDPServer
import socket

from flask import Flask, json, request

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
server = SSDPServer("remote-talk-box-" + str(uuid.getnode()), device_type="mumble-remote-client", location='http://{ipaddr}:{port}/mumble-client'.format(ipaddr=IPAddr, port=FLASK_PORT))
ssdp_daemon = threading.Thread(target=server.serve_forever, args=(), daemon=True)
ssdp_daemon.start()


# ------------------------------------------------------------------------------------------
# API Calls
# ------------------------------------------------------------------------------------------

api = Flask(__name__)

@api.route('/mumble-client/shutdown', methods=['GET'])
def shutdown_client():
    cmd = {}
    cmd['action'] = 'shutdown'
    cmd_queue.put(cmd)
    return json.dumps({'shutdown': True})

@api.route('/mumble-client', methods=['GET'])
def get_status():
    return json.dumps(client.get_session())

@api.route('/mumble-client/connect', methods=['GET'])
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
    return json.dumps(cmd['result'])

@api.route('/mumble-client/disconnect', methods=['GET'])
def disconnect_client():
    cmd = {}
    cmd['action'] = 'disconnect'
    cmd['processed'] = False
    cmd_queue.put(cmd)
    while not cmd['processed']:
        time.sleep(0.2)
    return json.dumps(cmd['result'])

# URL to Connect to locallhost:
#  http://127.0.0.1:5000/mumble-client/connect?host=localhost&port=12000&username=ai-cube-1&password=Asdf1234
# URL to disconnect:
#  http://127.0.0.1:5000/mumble-client/disconnect
# URL to Shutdown Client:
#  http://127.0.0.1:5000/mumble-client/shutdown

if __name__ == '__main__':
    flask_thread = threading.Thread(target=api.run, args=('0.0.0.0', FLASK_PORT), daemon=True)
    flask_thread.start()

# ------------------------------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------------------------------

def connect_to_server(host, port, username, password):
    try:
        client.connect(host=host, username=username, pwd=password, port=port)
    except Exception as e:
        print(e)
        return {'error': 'internal server error'}
    except pymumble_py3.errors.ConnectionRejectedError as e:
        print(e)
        return {'error': 'invalid password, connection refused'}
    except:
        return {'error': 'internal server error'}
    return client.get_session()

def disconnect_from_server():
    try:
        client.disconnect()
    except Exception as e:
        print(e)
    return client.get_session()


# Process connect and disconnect commands
while True:
    cmd = cmd_queue.get()
    if cmd is not None:
        if cmd['action'] ==  'connect':
            cmd['result'] = connect_to_server(cmd['host'], cmd['port'], cmd['username'], cmd['password'])
            if cmd['result']  is None:
                cmd['result'] = {'status': 'disconnected'}
        if cmd['action'] ==  'disconnect':
            cmd['result'] = disconnect_from_server()
            if cmd['result']  is None:
                cmd['result'] = {'status': 'disconnected'}
        if cmd['action'] ==  'shutdown':
            time.sleep(1)
            exit()
        cmd['processed'] = True
    time.sleep(0.5)