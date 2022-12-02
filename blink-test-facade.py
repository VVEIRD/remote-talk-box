import lib.blink.BlinkFacade as BlinkFacade
from lib.blink.blinker import Blinker, BlinkerTypes
import time
from blinkstick import blinkstick
import atexit

color_source = ['#00967d', '#ce3385', '#00967d', '#ce3385', '#00967d', '#ce3385', '#00967d', '#ce3385']
color_target = ['#ce3385', '#00967d', '#ce3385', '#00967d', '#ce3385', '#00967d', '#ce3385', '#00967d']
filter_frames = [
            [1, 0, 0, 0, 1, 0, 0, 0],
            [1, 0, 0, 0, 1, 0, 0, 0],
            [1, 1, 0, 0, 1, 1, 0, 0],
            [0, 1, 0, 0, 0, 1, 0, 0],
            [0, 1, 0, 0, 0, 1, 0, 0],
            [0, 1, 1, 0, 0, 1, 1, 0],
            [0, 0, 1, 0, 0, 0, 1, 0],
            [0, 0, 1, 0, 0, 0, 1, 0],
            [0, 0, 1, 1, 0, 0, 1, 1],
            [0, 0, 0, 1, 0, 0, 0, 1],
            [0, 0, 0, 1, 0, 0, 0, 1],
            [1, 0, 0, 1, 1, 0, 0, 1]
        ]
b_pulse_2 = Blinker(type=BlinkerTypes.PULSE, color_target=color_target, duration_ms=3000, brightnes=0.3, loop=4, decay=0.3)
b_pulse_2.generate()
BlinkFacade.save_blinker(name='pulse-3s-4loops-dright-0-3', blinker=b_pulse_2)
BlinkFacade.play_blink(name='2-lights-rotating-3-times')
BlinkFacade.play_blink(name='pulse-3s-4loops-dright-0-3', endless=True)

def exit_handler():
    BlinkFacade.stop()

atexit.register(exit_handler)

time.sleep(30)
    