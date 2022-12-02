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
        self.filter_frames = [[ 1 for i in range(blinker_leds) ]]
        self.current_filter_frame = 0
        self.led_current = [ [0,0,0] for i in range(blinker_leds) ]
        self.generated = False

    def add_filter_frames(self, filter_frames, backfill=0):
        for frame in filter_frames:
            f_led_count = len(frame)
            if f_led_count < self.blinker_leds:
                for i in range(self.blinker_leds-f_led_count):
                    frame.append(backfill)
        self.filter_frames = filter_frames.copy()

   
    def _get_filter_frame(self):
        if self.current_filter_frame+1 >= len(self.filter_frames):
            self.current_filter_frame = 0
        else:
            self.current_filter_frame += 1
        return self.filter_frames[self.current_filter_frame]
    
    def animate(self, bstick):
        if not self.generated:
            self.generate()
        frame_time = 1.0/self.FPS
        for frame in self.frames:
            st = time.time()
            filter_frame = self._get_filter_frame()
            for i in self.led_range:
                a = filter_frame[i]
                color = frame[i] if filter_frame[i] == 1 else [self.led_current[i][0]*(1.0-self.decay), self.led_current[i][1]*(1.0-self.decay), self.led_current[i][2]*(1.0-self.decay)]
                bstick.set_color(index=i, red=color[0], green=color[1], blue=color[2])
                self.led_current[i] = color
            et = time.time()
            #print("Animate: " + str(et - st))
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
        self.generated = True

    def _generate_animation(self):
        print("nolp")
        return []

    def _generate_pulse(self):
        frames = []
        for i in range(self.loop):
            duration = self.duration_ms
            self.duration_ms = self.duration_ms/2
            g1 = self._generate_morph(loop = False)
            g2 = self._generate_morph(reverse = True, loop = False)
            self.duration_ms = duration
            frames = [*frames, *g1, *g2]
        return frames

    def _generate_morph(self, reverse = False, loop=True):
        loop_count = self.loop if loop else 1
        target = self.color_target if not reverse else self.color_source
        source = self.color_source if not reverse else self.color_target
        print(source)
        target_colors = [ self._hex_to_rgb(c) for c in target]
        source_colors = [ self._hex_to_rgb(c) for c in source]
        gradient = []
        steps = int(self.duration_ms / (1000/self.FPS))
        for i in range(loop_count):
            for n in range(1, steps):
                leds = []
                d = 1.0 * n / steps
                for i in range(self.blinker_leds):
                    r_start, g_start, b_start = source_colors[i]
                    r_end, g_end, b_end = target_colors[i]
                    if n == steps-1:
                        r = r_end* self.brightnes
                        g = g_end * self.brightnes
                        b = b_end * self.brightnes
                    else:
                        r = ((r_start * (1 - d)) + (r_end * d)) * self.brightnes
                        g = ((g_start * (1 - d)) + (g_end * d)) * self.brightnes
                        b = ((b_start * (1 - d)) + (b_end * d)) * self.brightnes
                    leds.append((r, g, b))
                gradient.append(leds)
        return gradient