from lib.blink.blinker import BlinkerTypes, Blinker
from blinkstick import blinkstick
from pathlib import Path
from json import JSONDecodeError
from queue import Queue
from blinkstick import blinkstick
import threading
import time

BLINKERS = {}

BLINK_STICKS = {}


LD_PATH = Path('data', 'blink')

BLINKER_DAEMON_PROCESSES = {}
BLINKER_DAEMON_RUNNING = [True]

BD_QUEUES = {}

def _blinker_daemon(stick_name):    
    current_blink = None
    endless = False
    while BLINKER_DAEMON_RUNNING[0]:
        if not BD_QUEUES[stick_name].empty():
            cmd = BD_QUEUES[stick_name].get()
            current_blink = cmd[0]
            endless = cmd[1]
        if current_blink is not None:
            #print("Running: " + stick_name)
            current_blink.animate(BLINK_STICKS[stick_name])
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
            BLINKERS[blinker_file.stem] = Blinker.from_json(blinker_io.read())
        except JSONDecodeError as e:
            print("Error loading blinker file {file}".format(file=blinker_file.absolute()))
    for stick in blinkstick.find_all():
        if default_stick is None:
            default_stick = stick.get_serial()
        BLINK_STICKS[stick.get_serial()] = stick
    for stick_name in BLINK_STICKS:
        BD_QUEUES[stick_name] = Queue()
        print(stick_name)
        arg = str(stick_name)
        BLINKER_DAEMON_PROCESSES[stick_name] = threading.Thread(target=_blinker_daemon, args=(stick_name,), daemon=True)
        BLINKER_DAEMON_PROCESSES[stick_name].start()
    if default_stick is not None:
        BLINK_STICKS['default'] = BLINK_STICKS[default_stick]

def stop():
    BLINKER_DAEMON_RUNNING[0] = False
    for daemon_name in BLINKER_DAEMON_PROCESSES:
        BLINKER_DAEMON_PROCESSES[daemon_name].join()
        BLINK_STICKS[daemon_name]
        for i in range(8):
            BLINK_STICKS[daemon_name].set_color(index=i, red=0, green=0, blue=0)

def save_blinker(name, blinker):
    blinker_file = LD_PATH.joinpath(name + '.json')
    with blinker_file.open(mode='w', encoding="utf8") as blinker_io:
        blinker_io.write(blinker.to_json())
    BLINKERS[name] = blinker

def play_blink(name, device=None, endless=False):
    if device is None:
        device = BLINK_STICKS['default'].get_serial()
    if device not in BLINK_STICKS:
        raise ValueError("No device with the given name {device}".format(device=device))
    if name in BLINKERS:
        cmd = [BLINKERS[name], endless]
        BD_QUEUES[device].put(cmd)
    else:
        raise ValueError("blink {name} does not exist".format(name=name))

def get_devices():
    blink_list = []
    for device_name in BLINK_STICKS:
        if device_name == 'default':
            continue
        device = BLINK_STICKS[device_name]
        entry = {'name': device.get_serial(), 'description': device.get_description(), 'manufacturer':  device.get_manufacturer()}
        blink_list.append(entry)
    return blink_list

def get_blinks():
    return [blink_name for blink_name in BLINKERS]
def get_blink(blink_name):
    return BLINKERS[blink_name] if blink_name in BLINKERS else None

__init__()