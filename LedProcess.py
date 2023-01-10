import lib.blink.BlinkFacade as BlinkFacade
from lib.helper import is_int
from json import JSONDecodeError
from pathlib import Path
from lib.blink.blinker import BlinkTypes, Blink
from queue import Queue
import socket, atexit
import traceback
import sys

from flask import Flask, Response, json, request

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
            cfg_io.write(json.dumps(CONFIGURATION, indent=4))
    except Exception as e:
        print("Error saving config file {file}".format(file=CFG_FILE.absolute()))

# Set FLask Port
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
# LED API Calls
# ------------------------------------------------------------------------------------------

@api.route('/rt-box/leds', methods=['GET'], strict_slashes=False)
def leds_status():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    led_status = get_led_status()
    return Response(json.dumps({'led': led_status}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/led/device/<device_name>', methods=['GET'])
def led_device_status(device_name):
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    led_Device = BlinkFacade.get_device(device_name)
    return Response(json.dumps(led_Device, indent=4), status=200, mimetype='application/json')


@api.route('/rt-box/led/device/<device_name>/play/<name>', methods=['GET'])
def play_blink(name, device_name, endless=False):
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    endless = True if request.args.get(key='endless', default="", type=str).lower() == "true" else False
    print("Endless: {end}".format(end=endless))
    try:
        BlinkFacade.play_blink(name=name, device=device_name, endless=endless)
    except ValueError as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'blink queued'}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/led/device/<device>/stop', methods=['GET'])
def stop_blink(device):
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    endless = False
    try:
        BlinkFacade.stop_animation(device_name=device)
    except ValueError as e:
        return Response(json.dumps({'error': str(e)}, indent=4), status=400, mimetype='application/json')
    return Response(json.dumps({'status': 'stopping animation queued'}, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/led/play/<name>', methods=['GET'])
def play_blink_2(name):
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    device = request.args.get(key='device', default=None, type=str)
    endless = True if request.args.get(key='endless', default="", type=str).lower() == "true" else False
    print("Endless: {end}".format(end=endless))
    return play_blink(name=name, device_name=device, endless=endless)

@api.route('/rt-box/led/play', methods=['GET'])
def play_blink_3():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    name = request.args.get('name')
    device = request.args.get(key='device', default=None, type=str)
    endless = request.args.get(key='endless', default=False, type=bool)
    return play_blink(name, device=device, endless=endless)

@api.route('/rt-box/led/stop', methods=['GET'])
def stop_blink_2():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    device = request.args.get(key='device', default=None, type=str)
    return stop_blink(device)

@api.route('/rt-box/blinks', methods=['GET'], strict_slashes=False)
def get_blinks():
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    blinks = BlinkFacade.get_blinks()
    return Response(json.dumps(blinks, indent=4), status=200, mimetype='application/json')

@api.route('/rt-box/blink/<blink_name>', methods=['GET'])
def get_blink(blink_name):
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
    blink = BlinkFacade.get_blink(blink_name)
    if blink is not None:
        return Response(blink.to_json(), status=200, mimetype='application/json')
    else:
        return Response(json.dumps({'error': 'A blink with the name {name} does not exist'.format(name=blink_name)}, indent=4), status=400, mimetype='application/json')

@api.route('/rt-box/blink/<blink_name>', methods=['PUT'])
def update_blink(blink_name):
    if (request.cookies.get('accessToken') != CONFIGURATION['secret']):
        return Response(json.dumps({'status': 'Access forbidden, please provide a valid access token'}, indent=4), status=403, mimetype='application/json')
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
# Functions
# ------------------------------------------------------------------------------------------

def get_status():
    led_status= get_led_status()
    return led_status

def get_led_status():
    leds = BlinkFacade.get_devices()
    blinks = BlinkFacade.get_blinks()
    return {'devices': leds, 'blinks': blinks}

def exit_handler():
    BlinkFacade.shutdown()

atexit.register(exit_handler)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=api.run, args=('0.0.0.0', FLASK_PORT), daemon=True)
    flask_thread.start()


# Process connect and disconnect commands
while True:
    cmd = cmd_queue.get()
    if cmd is not None:
        if cmd['action'] ==  'shutdown':
            time.sleep(0.5)
            exit()
        cmd['processed'] = True
    time.sleep(0.5)
