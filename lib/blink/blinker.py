import re, time
from enum import Enum
from blinkstick import blinkstick

class BlinkerTypes(Enum):
    PULSE = 1
    ANIMATION = 2
    MORPH = 3

class Blinker:
    def _hex_to_rgb(self, color_hex):
        HEX_COLOR_RE = re.compile(r'^#([a-fA-F0-9]{3}|[a-fA-F0-9]{6})$')
        try:
            hex_digits = HEX_COLOR_RE.match(color_hex).groups()[0]
        except AttributeError:
            raise ValueError("'%s' is not a valid hexadecimal color value." % color_hex)
        if len(hex_digits) == 3:
            hex_digits = ''.join([2 * s for s in hex_digits])
        hex_digits = '#%s' % hex_digits.lower()
        return tuple([int(s, 16) for s in (hex_digits[1:3], hex_digits[3:5], hex_digits[5:7])])
        
    def __init__(self, type, color_target, duration_ms, color_source='#000000', blinker_leds=8, decay=0.9, loop=1, brightnes=0.9):
        if not isinstance(color_target, str) and not isinstance(color_target, list):
            raise ValueError('A color_target must be a list of hexcolors or a string with a hexcolor.')
        if not isinstance(color_source, str) and not isinstance(color_source, list):
            raise ValueError('A color_target must be a list of hexcolors or a string with a hexcolor.')
        if isinstance(color_source, str):
            color_source_n = [color_source for i in range(blinker_leds)]
            color_source = color_source_n
        if isinstance(color_target, str):
            color_target_n = [color_target for i in range(blinker_leds)]
            color_target = color_target_n
        self.type = type
        self.color_target = color_target
        self.color_source = color_source
        self.duration_ms = duration_ms
        self.decay = decay
        self.loop = loop
        self.FPS = 30
        self.brightnes = brightnes
        self.blinker_leds = blinker_leds
        self.led_range = range(blinker_leds)
        self.frames = []
    
    def animate(self, bstick):
        frame_time = 1.0/self.FPS
        for frame in self.frames:
            st = time.time()
            for i in self.led_range:
                bstick.set_color(index=i, red=frame[i][0], green=frame[i][1], blue=frame[i][2])
            et = time.time()
            print("Animate: " + str(et - st))
            time.sleep(frame_time-(et - st) if frame_time-(et - st) > 0 else 0)

    def generate(self):
        '''
        This will generate the frames for the given animation
        '''
        print("Generating")
        if self.type == BlinkerTypes.PULSE:
            self.frames = self._generate_pulse()
        elif self.type == BlinkerTypes.MORPH:
            self.frames = self._generate_morph()
        elif self.type == BlinkerTypes.ANIMATION:
            self.frames = self._generate_animation()

    def _generate_animation(self):
        print("nolp")
        return []

    def _generate_pulse(self):
        duration = self.duration_ms
        self.duration_ms = self.duration_ms/2
        g1 = self._generate_morph()
        g2 = self._generate_morph(reverse = True)
        self.duration_ms = duration
        return [*g1, *g2]

    def _generate_morph(self, reverse = False):
        target = self.color_target if not reverse else self.color_source
        source = self.color_source if not reverse else self.color_target
        print(source)
        target_colors = [ self._hex_to_rgb(c) for c in target]
        source_colors = [ self._hex_to_rgb(c) for c in source]
        gradient = []
        steps = int(self.duration_ms / (1000/self.FPS))
        for n in range(1, steps):
            leds = []
            d = 1.0 * n / steps
            for i in range(self.blinker_leds):
                r_start, g_start, b_start = source_colors[i]
                r_end, g_end, b_end = target_colors[i]
                r = ((r_start * (1 - d)) + (r_end * d)) * self.brightnes
                g = ((g_start * (1 - d)) + (g_end * d)) * self.brightnes
                b = ((b_start * (1 - d)) + (b_end * d)) * self.brightnes
                leds.append((r, g, b))
            gradient.append(leds)
        return gradient