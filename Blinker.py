from blinkstick import blinkstick
from random import random
import re
import time
from lib.blink.blinker import Blinker, BlinkerTypes

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

max_brightnes = 0.3

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
        for i in [0,1,2,3,4,5,6,7]:
            led_color[i] = [grad_r, grad_g, grad_b]
            bstick.set_color(index=i, red=grad_r, green=grad_g, blue=grad_b)
        et = time.time()
        print("Morphtime: " + str(et - st))
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
    nleds = [led.copy() for led in led_color]
    while run < loop:
        for i in range(len(animation)):
            leds = animation[i]
            nleds[0] = [r, g, b] if leds[0] == 1 else [nleds[0][0]*(1.0-decay), nleds[0][1]*(1.0-decay), nleds[0][2]*(1.0-decay)]
            nleds[1] = [r, g, b] if leds[1] == 1 else [nleds[1][0]*(1.0-decay), nleds[1][1]*(1.0-decay), nleds[1][2]*(1.0-decay)]
            nleds[2] = [r, g, b] if leds[2] == 1 else [nleds[2][0]*(1.0-decay), nleds[2][1]*(1.0-decay), nleds[2][2]*(1.0-decay)]
            nleds[3] = [r, g, b] if leds[3] == 1 else [nleds[3][0]*(1.0-decay), nleds[3][1]*(1.0-decay), nleds[3][2]*(1.0-decay)]
            nleds[4] = [r, g, b] if leds[4] == 1 else [nleds[4][0]*(1.0-decay), nleds[4][1]*(1.0-decay), nleds[4][2]*(1.0-decay)]
            nleds[5] = [r, g, b] if leds[5] == 1 else [nleds[5][0]*(1.0-decay), nleds[5][1]*(1.0-decay), nleds[5][2]*(1.0-decay)]
            nleds[6] = [r, g, b] if leds[6] == 1 else [nleds[5][0]*(1.0-decay), nleds[6][1]*(1.0-decay), nleds[6][2]*(1.0-decay)]
            nleds[7] = [r, g, b] if leds[7] == 1 else [nleds[5][0]*(1.0-decay), nleds[7][1]*(1.0-decay), nleds[7][2]*(1.0-decay)]
            gradient.append(nleds.copy())
            #time.sleep(ms_delay-(et - st) if ms_delay-(et - st) > 0 else 0)
        run += 1
    for i in range(3):
        nleds[0] = [nleds[0][0]*(1.0-decay), nleds[0][1]*(1.0-decay), nleds[0][2]*(1.0-decay)]
        nleds[1] = [nleds[1][0]*(1.0-decay), nleds[1][1]*(1.0-decay), nleds[1][2]*(1.0-decay)]
        nleds[2] = [nleds[2][0]*(1.0-decay), nleds[2][1]*(1.0-decay), nleds[2][2]*(1.0-decay)]
        nleds[3] = [nleds[3][0]*(1.0-decay), nleds[3][1]*(1.0-decay), nleds[3][2]*(1.0-decay)]
        nleds[4] = [nleds[4][0]*(1.0-decay), nleds[4][1]*(1.0-decay), nleds[4][2]*(1.0-decay)]
        nleds[5] = [nleds[5][0]*(1.0-decay), nleds[5][1]*(1.0-decay), nleds[5][2]*(1.0-decay)]
        nleds[6] = [nleds[5][0]*(1.0-decay), nleds[6][1]*(1.0-decay), nleds[6][2]*(1.0-decay)]
        nleds[7] = [nleds[5][0]*(1.0-decay), nleds[7][1]*(1.0-decay), nleds[7][2]*(1.0-decay)]
        gradient.append(nleds.copy())
    ms_delay = delay
    for grad in gradient:
        st = time.time()
        #for i in range(8):
        bstick.set_color(index=0, red=grad[0][0], green=grad[0][1], blue=grad[0][2])
        bstick.set_color(index=1, red=grad[1][0], green=grad[1][1], blue=grad[1][2])
        bstick.set_color(index=2, red=grad[2][0], green=grad[2][1], blue=grad[2][2])
        bstick.set_color(index=3, red=grad[3][0], green=grad[3][1], blue=grad[3][2])
        bstick.set_color(index=4, red=grad[4][0], green=grad[4][1], blue=grad[4][2])
        bstick.set_color(index=5, red=grad[5][0], green=grad[5][1], blue=grad[5][2])
        bstick.set_color(index=6, red=grad[6][0], green=grad[6][1], blue=grad[6][2])
        bstick.set_color(index=7, red=grad[7][0], green=grad[7][1], blue=grad[7][2])
        et = time.time()
        print("Animate: " + str(et - st))
        time.sleep(ms_delay-(et - st) if ms_delay-(et - st) > 0 else 0)

b = Blinker(type=BlinkerTypes.PULSE, color_target='#ce3385', duration_ms=3000, brightnes=0.5)
b.generate()
for bstick in blinkstick.find_all():
    try:
        b.animate(bstick)
        print("time.sleep()")
        time.sleep(5)
        pulse(bstick, '#ce3385', 1000, 15, loop=1)
        time.sleep(2)
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
        animate_led(blink=bstick, animation=led_on_2, delay=0.200, decay=0.8, color_hex='#ce3385', loop=10)
        for i in range(8):
            bstick.set_color(index=i, red=0, green=0, blue=0)
    except KeyboardInterrupt as e:
        for i in range(8):
            bstick.set_color(index=i, red=0, green=0, blue=0)

    