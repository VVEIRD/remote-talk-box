from lib.blink.blinker import BlinkTypes, Blink
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


# Playback Variables
LED_STATES = {}
CURRENTLY_PLAYING = {}
ENDLESS_PLAY = {}


LD_PATH = Path('data', 'blink')

BLINKER_DAEMON_PROCESSES = {}
BLINKER_DAEMON_RUNNING = {}

BD_QUEUES = {}

def _blinker_daemon(stick_name):    
    current_blink = None
    while BLINKER_DAEMON_RUNNING[stick_name]:
        if not BD_QUEUES[stick_name].empty():
            cmd = BD_QUEUES[stick_name].get()
            current_blink = cmd[0]
            ENDLESS_PLAY[stick_name] = cmd[1]
            CURRENTLY_PLAYING[stick_name] = cmd[2]
        if current_blink is not None:
            #print("Running: " + stick_name)
            current_blink.animate(device=BLINK_DEVICES[stick_name], current_led_state=LED_STATES[stick_name])
            if not ENDLESS_PLAY[stick_name]:
                #print("Removing: " + stick_name)
                current_blink = None
                CURRENTLY_PLAYING[stick_name] = None
                ENDLESS_PLAY[stick_name] = False
        else:
            time.sleep(0.2)

def __init__():
    LD_PATH.mkdir(parents=True, exist_ok=True)
    max_led_count = None
    default_stick = None
    for stick in blinkstick.find_all():
        serial = stick.get_serial()
        blick_type = serial.split('-')[1]
        if default_stick is None:
            default_stick = serial
        BLINK_DEVICES[serial] = stick
        LED_COUNT[serial] = 8 if blick_type.startswith('3.') else 1
        if max_led_count is None:
            max_led_count = LED_COUNT[serial]
        LED_STATES[serial] = [[0, 0, 0] for i in range(LED_COUNT[serial])]
        CURRENTLY_PLAYING[serial] = None
        ENDLESS_PLAY[serial] = False
    for stick_name in BLINK_DEVICES:
        BD_QUEUES[stick_name] = Queue()
        print(stick_name)
        arg = str(stick_name)
        BLINKER_DAEMON_RUNNING[stick_name] = True
        BLINKER_DAEMON_PROCESSES[stick_name] = threading.Thread(target=_blinker_daemon, args=(stick_name,), daemon=True)
        BLINKER_DAEMON_PROCESSES[stick_name].start()
    if default_stick is not None:
        BLINK_DEVICES['default'] = BLINK_DEVICES[default_stick]
    if max_led_count is None:
        max_led_count = 8
    # Load Blink Animations
    for blinker_file in LD_PATH.rglob("*.json"):
     with blinker_file.open(mode='r', encoding="utf8") as blinker_io:
        try:
            BLINKS[blinker_file.stem] = Blink.from_json(blinker_io.read())
        except JSONDecodeError as e:
            print("Error loading blinker file {file}".format(file=blinker_file.absolute()))
    # Generate Stop blink
    BLINKS['stop'] = Blink(BlinkTypes.DECAY, "#000000", duration_ms=510, led_count=max_led_count, decay=0.2, loop=1)

def stop_animation(device_name=None):
    '''
     '' Stops any animation if currently playing and pulls down the LEDs to 0
    '''
    if device_name is not None:
        if device_name not in BLINK_DEVICES:
            raise ValueError("No device with the given name {device} found".format(device=device_name))
        if CURRENTLY_PLAYING[device_name] is not None:
            ENDLESS_PLAY[device_name] = False
            blink_name = CURRENTLY_PLAYING[device_name]
            BLINKS[blink_name].stop_animation()
            play_blink('stop', device=device_name, endless=False)
    else:
        for device_name in BLINK_DEVICES:
            if device_name == 'default':
                continue
            if CURRENTLY_PLAYING[device_name] is not None:
                ENDLESS_PLAY[device_name] = False
                blink_name = CURRENTLY_PLAYING[device_name]
                BLINKS[blink_name].stop_animation()
                play_blink('stop', device=device_name, endless=False)

def shutdown(device_name=None):
    if device_name is None:
        for i in BLINKER_DAEMON_RUNNING:
            BLINKER_DAEMON_RUNNING[i] = False
        # Stop currently playing Animations
        for device_name in BLINK_DEVICES:
            if device_name == 'default':
                continue
            if CURRENTLY_PLAYING[device_name] is not None:
                BLINKS[device_name].stop_animation()
    elif device_name in BLINKER_DAEMON_RUNNING and device_name != 'default':
        if CURRENTLY_PLAYING[device_name] is not None:
            BLINKS[device_name].stop_animation()
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
        raise ValueError("No device with the given name {device} found".format(device=device))
    if name in BLINKS:
        cmd = [BLINKS[name], endless, name]
        BD_QUEUES[device].put(cmd)
    else:
        raise ValueError("blink {name} does not exist".format(name=name))

def get_devices():
    blink_list = []
    for device_name in BLINK_DEVICES:
        if device_name == 'default':
            continue
        device = BLINK_DEVICES[device_name]
        currenty_playing = {'blink': CURRENTLY_PLAYING[device_name], 'endless': ENDLESS_PLAY[device_name]} if CURRENTLY_PLAYING[device_name] is not None else None
        entry = {'name': device.get_serial(), 'description': device.get_description(), 'manufacturer':  device.get_manufacturer(), 'currently_playing': currenty_playing}
        blink_list.append(entry)
    return blink_list

def get_device(device_name):
    if device_name not in BLINK_DEVICES:
        raise ValueError("No device with the given name {device} found".format(device=device_name))
    blink_list = []
    device = BLINK_DEVICES[device_name]
    currenty_playing = {'blink': CURRENTLY_PLAYING[device_name], 'endless': ENDLESS_PLAY[device_name]} if CURRENTLY_PLAYING[device_name] is not None else None
    entry = {'name': device.get_serial(), 'description': device.get_description(), 'manufacturer':  device.get_manufacturer(), 'currently_playing': currenty_playing}
    return entry

def get_blinks():
    return [blink_name for blink_name in BLINKS if blink_name != 'stop']

def get_blink(blink_name):
    return BLINKS[blink_name] if blink_name in BLINKS else None

__init__()