from blinkstick import blinkstick
from random import random
import re
import time

for bstick in blinkstick.find_all():
    print("Found device:")
    print("    Manufacturer:  " + bstick.get_manufacturer())
    print("    Description:   " + bstick.get_description())
    print("    Serial:        " + bstick.get_serial())
#    print("    Current Color: " + bstick.get_color(color_format="hex"))
    print("    Info Block 1:  " + bstick.get_info_block1())
    print("    Info Block 2:  " + bstick.get_info_block2())
    #bstick.set_mode(2)

#for bstick in blinkstick.find_all():
#    print("aaa")
#    bstick.pulse(red=200, green=50, blue=50, repeats=5, duration=2000, steps=50)
#    print("bbb")
led_color = [
    [0,0,0] , # LED 1
    [0,0,0] , # LED 2
    [0,0,0] , # LED 3
    [0,0,0] , # LED 4
    [0,0,0] , # LED 5
    [0,0,0] , # LED 6
    [0,0,0] , # LED 7
    [0,0,0] , # LED 8
]

max_brightnes = 0.8

def hex_to_rgb(color_hex):
    HEX_COLOR_RE = re.compile(r'^#([a-fA-F0-9]{3}|[a-fA-F0-9]{6})$')
    try:
        hex_digits = HEX_COLOR_RE.match(color_hex).groups()[0]
    except AttributeError:
        raise ValueError("'%s' is not a valid hexadecimal color value." % color_hex)
    if len(hex_digits) == 3:
        hex_digits = ''.join([2 * s for s in hex_digits])
    hex_digits = '#%s' % hex_digits.lower()
    return tuple([int(s, 16) for s in (hex_digits[1:3], hex_digits[3:5], hex_digits[5:7])])

def morph(bstick, color_target, color_source='#000000', duration=1000, steps=50):
    r_start, g_start, b_start = hex_to_rgb(color_source)
    r_end, g_end, b_end = hex_to_rgb(color_target)
    gradient = []
    steps += 1
    print("Morph from {source} to {target}".format(source=color_source, target=color_target))
    for n in range(1, steps):
        d = 1.0 * n / steps
        r = ((r_start * (1 - d)) + (r_end * d)) * max_brightnes
        g = ((g_start * (1 - d)) + (g_end * d)) * max_brightnes
        b = ((b_start * (1 - d)) + (b_end * d)) * max_brightnes
        gradient.append((r, g, b))
    ms_delay = float(duration) / float(1000 * steps)
    for grad in gradient:
        st = time.time()
        grad_r, grad_g, grad_b = grad
        for i in range(8):
            led_color[i] = [grad_r, grad_g, grad_b]
            bstick.set_color(index=i, red=grad_r, green=grad_g, blue=grad_b)
        et = time.time()
        time.sleep(ms_delay-(et - st) if ms_delay-(et - st) > 0 else 0)

def pulse(bstick, color_hex, duration=1000, steps=40, loop=1):
    run = 0
    while run < loop:
        morph(bstick=bstick, color_target=color_hex, color_source='#000000', duration=duration, steps=steps)
        morph(bstick=bstick, color_target='#000000', color_source=color_hex, duration=duration, steps=steps)
        run += 1

def animate_led(blink, color_hex, animation, delay=0.250, decay=0.9, loop=3):
    run = 0
    r, g, b = hex_to_rgb(color_hex)
    r = r*max_brightnes
    g = g*max_brightnes
    b = b*max_brightnes
    # TODO: Precalc steps
    gradient = []
    while run < loop:
        ms_delay = delay
        for i in range(len(animation)):
            st = time.time()
            leds = animation[i]
            led_color[0] = [r, g, b] if leds[0] == 1 else [led_color[0][0]*(1.0-decay), led_color[0][1]*(1.0-decay), led_color[0][2]*(1.0-decay)]
            led_color[1] = [r, g, b] if leds[1] == 1 else [led_color[1][0]*(1.0-decay), led_color[1][1]*(1.0-decay), led_color[1][2]*(1.0-decay)]
            led_color[2] = [r, g, b] if leds[2] == 1 else [led_color[2][0]*(1.0-decay), led_color[2][1]*(1.0-decay), led_color[2][2]*(1.0-decay)]
            led_color[3] = [r, g, b] if leds[3] == 1 else [led_color[3][0]*(1.0-decay), led_color[3][1]*(1.0-decay), led_color[3][2]*(1.0-decay)]
            led_color[4] = [r, g, b] if leds[4] == 1 else [led_color[4][0]*(1.0-decay), led_color[4][1]*(1.0-decay), led_color[4][2]*(1.0-decay)]
            led_color[5] = [r, g, b] if leds[5] == 1 else [led_color[5][0]*(1.0-decay), led_color[5][1]*(1.0-decay), led_color[5][2]*(1.0-decay)]
            led_color[6] = [r, g, b] if leds[6] == 1 else [led_color[5][0]*(1.0-decay), led_color[6][1]*(1.0-decay), led_color[6][2]*(1.0-decay)]
            led_color[7] = [r, g, b] if leds[7] == 1 else [led_color[5][0]*(1.0-decay), led_color[7][1]*(1.0-decay), led_color[7][2]*(1.0-decay)]
            for i in range(8):
                bstick.set_color(index=i, red=led_color[i][0], green=led_color[i][1], blue=led_color[i][2])
            et = time.time()
            time.sleep(ms_delay-(et - st) if ms_delay-(et - st) > 0 else 0)
        run += 1

for bstick in blinkstick.find_all():
    try:
        pulse(bstick, '#ce3385', 1000, 15, loop=1)
        led_on = [
            [1, 0, 0, 0, 1, 0, 0, 0],
            [0, 1, 0, 0, 0, 1, 0, 0],
            [0, 0, 1, 0, 0, 0, 1, 0],
            [0, 0, 0, 1, 0, 0, 0, 1]
        ]
        led_on_2 = [
            [1, 1, 0, 0, 1, 1, 0, 0],
            [0, 1, 1, 0, 0, 1, 1, 0],
            [0, 0, 1, 1, 0, 0, 1, 1],
            [1, 0, 0, 1, 1, 0, 0, 1]
        ]
        #animate_led(blink=bstick, animation=led_on, delay=0.350, color_hex='#ce3385', loop=10)
        animate_led(blink=bstick, animation=led_on, delay=0.100, decay=0.8, color_hex='#ce3385', loop=10)
        animate_led(blink=bstick, animation=led_on_2, delay=0.350, decay=0.8, color_hex='#ce3385', loop=10)
        for i in range(8):
            bstick.set_color(index=i, red=0, green=0, blue=0)
    except KeyboardInterrupt as e:
        for i in range(8):
            bstick.set_color(index=i, red=0, green=0, blue=0)

    