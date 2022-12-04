from lib.blink.blinker import BlinkerTypes, Blinker
from blinkstick import blinkstick
from pathlib import Path
from json import JSONDecodeError
from queue import Queue
from blinkstick import blinkstick
import threading
import time

BLINKS = {}

BLINK_DEVICES = {}

LED_COUNT = {}

LED_STATES = {}


LD_PATH = Path('data', 'blink')

BLINKER_DAEMON_PROCESSES = {}
BLINKER_DAEMON_RUNNING = {}

BD_QUEUES = {}

def _blinker_daemon(stick_name):    
    current_blink = None
    endless = False
    while BLINKER_DAEMON_RUNNING[stick_name]:
        if not BD_QUEUES[stick_name].empty():
            cmd = BD_QUEUES[stick_name].get()
            current_blink = cmd[0]
            endless = cmd[1]
        if current_blink is not None:
            #print("Running: " + stick_name)
            current_blink.animate(device=BLINK_DEVICES[stick_name], current_led_state=LED_STATES[stick_name])
            if not endless:
                #print("Removing: " + stick_name)
                current_blink = None
        else:
            time.sleep(0.2)

def __init__():
    LD_PATH.mkdir(parents=True, exist_ok=True)
    default_stick = None
    for blinker_file in LD_PATH.rglob("*.json"):
     with blinker_file.open(mode='r', encoding="utf8") as blinker_io:
        try:
            BLINKS[blinker_file.stem] = Blinker.from_json(blinker_io.read())
        except JSONDecodeError as e:
            print("Error loading blinker file {file}".format(file=blinker_file.absolute()))
    for stick in blinkstick.find_all():
        serial = stick.get_serial()
        blick_type = serial.split('-')[1]
        if default_stick is None:
            default_stick = serial
        BLINK_DEVICES[serial] = stick
        LED_COUNT[serial] = 8 if blick_type.startswith('3.') else 1
        LED_STATES[serial] = [[0, 0, 0] for i in range(LED_COUNT[serial])]
    for stick_name in BLINK_DEVICES:
        BD_QUEUES[stick_name] = Queue()
        print(stick_name)
        arg = str(stick_name)
        BLINKER_DAEMON_RUNNING[stick_name] = True
        BLINKER_DAEMON_PROCESSES[stick_name] = threading.Thread(target=_blinker_daemon, args=(stick_name,), daemon=True)
        BLINKER_DAEMON_PROCESSES[stick_name].start()
    if default_stick is not None:
        BLINK_DEVICES['default'] = BLINK_DEVICES[default_stick]

def stop(device_name=None):
    if device_name is None:
        for i in BLINKER_DAEMON_RUNNING:
            BLINKER_DAEMON_RUNNING[i] = False
    elif device_name in BLINKER_DAEMON_RUNNING:
        BLINKER_DAEMON_RUNNING[device_name] = False
    else:
        raise ValueError("No device with the name {name} exists".format(name=device_name))
    for daemon_name in BLINKER_DAEMON_PROCESSES:
        BLINKER_DAEMON_PROCESSES[daemon_name].join()
        for i in range(8):
            BLINK_DEVICES[daemon_name].set_color(index=i, red=0, green=0, blue=0)

def save_blinker(name, blinker):
    blinker_file = LD_PATH.joinpath(name + '.json')
    with blinker_file.open(mode='w', encoding="utf8") as blinker_io:
        blinker_io.write(blinker.to_json())
    BLINKS[name] = blinker

def play_blink(name, device=None, endless=False):
    if device is None:
        device = BLINK_DEVICES['default'].get_serial()
    if device not in BLINK_DEVICES:
        raise ValueError("No device with the given name {device}".format(device=device))
    if name in BLINKS:
        cmd = [BLINKS[name], endless]
        BD_QUEUES[device].put(cmd)
    else:
        raise ValueError("blink {name} does not exist".format(name=name))

def get_devices():
    blink_list = []
    for device_name in BLINK_DEVICES:
        if device_name == 'default':
            continue
        device = BLINK_DEVICES[device_name]
        entry = {'name': device.get_serial(), 'description': device.get_description(), 'manufacturer':  device.get_manufacturer()}
        blink_list.append(entry)
    return blink_list

def get_blinks():
    return [blink_name for blink_name in BLINKS]

def get_blink(blink_name):
    return BLINKS[blink_name] if blink_name in BLINKS else None

__init__()