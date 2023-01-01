import re, time, json
from enum import Enum
from blinkstick import blinkstick

class BlinkTypes(int, Enum):
    PULSE = 1
    MORPH = 2
    DECAY = 3

class Blink:
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
        
    def __init__(self, type, color_target, duration_ms, color_source='#000000', fps=30, led_count=8, decay=0.9, loop=1, brightnes=0.9):
        # Test color target
        if not isinstance(color_target, str) and not isinstance(color_target, list):
            raise ValueError('A color_target must be a list of hexcolors or a string with a hexcolor.')
        if isinstance(color_target, str) and not re.match(r'^#([a-fA-F0-9]{3}|[a-fA-F0-9]{6})$', color_target):
            raise ValueError('A color_target must be a list of hexcolors or a string with a hexcolor.')
        if isinstance(color_target, list) and (len(color_target) == 0 or not re.match(r'^#([a-fA-F0-9]{3}|[a-fA-F0-9]{6})$', color_target[0])):
            raise ValueError('A color_target must be a list of hexcolors or a string with a hexcolor.')
        # Test color source
        if not isinstance(color_source, str) and not isinstance(color_source, list):
            raise ValueError('A color_source must be a list of hexcolors or a string with a hexcolor.')
        if isinstance(color_source, str) and not re.match(r'^#([a-fA-F0-9]{3}|[a-fA-F0-9]{6})$', color_source):
            raise ValueError('A color_source must be a list of hexcolors or a string with a hexcolor.')
        if isinstance(color_source, list) and (len(color_source) == 0 or not re.match(r'^#([a-fA-F0-9]{3}|[a-fA-F0-9]{6})$', color_source[0])):
            raise ValueError('A color_source must be a list of hexcolors or a string with a hexcolor.')
        # Make colors a list if their're not
        if isinstance(color_source, str):
            color_source = [color_source for i in range(led_count)]
        if isinstance(color_target, str):
            color_target = [color_target for i in range(led_count)]
        self.type = type if type in (1,2,3) else 0
        if self.type == 0:
            raise ValueError('Type must be one of the following: 1, 2, 3')
        self.color_target = color_target
        self.color_source = color_source
        self.duration_ms = max(duration_ms, 120)
        self.decay = max(min(decay, 1.0), 0.1)
        self.interrupt = False
        self.loop = max(min(loop,10),1)
        self.FPS = max(min(fps, 30),5)
        self.brightnes = max(min(brightnes, 1.0), 0.1)
        self.led_count = max(led_count, 1)
        self.led_range = range(led_count)
        self.frames = []
        self.filter_frames = [[ 1 for i in range(led_count) ]]
        self.current_filter_frame = 0
        self.led_current = [ [0,0,0] for i in range(led_count) ]
        self.generated = False

    def add_filter_frames(self, filter_frames, backfill=0):
        for frame in filter_frames:
            f_led_count = len(frame)
            if f_led_count < self.led_count:
                for i in range(self.led_count-f_led_count):
                    frame.append(backfill)
        self.filter_frames = filter_frames.copy()

   
    def _get_filter_frame(self):
        if self.current_filter_frame+1 >= len(self.filter_frames):
            self.current_filter_frame = 0
        else:
            self.current_filter_frame += 1
        return self.filter_frames[self.current_filter_frame]
    
    def animate(self, device, current_led_state=None):
        # Make sure interrupt is not set
        self.interrupt = False
        if current_led_state is not None:
            led_current = current_led_state
        else:
            led_current = self.led_current
        # Set colour source to current led values for Decay animation
        if self.type == BlinkTypes.DECAY:
            self.color_source = [ '#%02x%02x%02x' % (int(current_led_state[i][0]), int(current_led_state[i][1]), int(current_led_state[i][2])) for i in range(self.led_count)]
            self.color_target = [ '#000000' for i in range(self.led_count)]
        # Generate animation frames if not generated or type = DECAY
        if not self.generated or self.type == BlinkTypes.DECAY:
            self.generate()
        frame_time = 1.0/self.FPS
        for frame in self.frames:
            # Stop animation
            if self.interrupt:
                self.interrupt = False
                break
            st = time.time()
            filter_frame = self._get_filter_frame()
            if current_led_state is not None and len(current_led_state) < len(self.led_range):
                ccal = len(current_led_state)
                for i in range(len(self.led_range)-ccal):
                    current_led_state.append([0,0,0])
            for i in self.led_range:
                a = filter_frame[i]
                color = frame[i] if filter_frame[i] == 1 else [led_current[i][0]*(1.0-self.decay), led_current[i][1]*(1.0-self.decay), led_current[i][2]*(1.0-self.decay)]
                if current_led_state is not None:
                    current_led_state[i] = [*color]
                device.set_color(index=i, red=color[0], green=color[1], blue=color[2])
                led_current[i] = color
            et = time.time()
            #print("Animate: " + str(et - st))
            time.sleep(frame_time-(et - st) if frame_time-(et - st) > 0 else 0)

    def stop_animation(self):
        self.interrupt = True

    def generate(self):
        '''
        This will generate the frames for the given animation
        '''
        #print("Generating")
        if self.type == BlinkTypes.PULSE:
            self.frames = self._generate_pulse()
        elif self.type == BlinkTypes.MORPH or self.type == BlinkTypes.DECAY:
            self.frames = self._generate_morph()
        self.generated = True

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
        #print(source)
        target_colors = [ self._hex_to_rgb(c) for c in target]
        source_colors = [ self._hex_to_rgb(c) for c in source]
        gradient = []
        steps = int(self.duration_ms / (1000/self.FPS))
        for i in range(loop_count):
            for n in range(1, steps):
                leds = []
                d = 1.0 * n / steps
                for i in range(self.led_count):
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

    def to_json(self):
        json_o = {}
        json_o['type'] = self.type
        json_o['color_target'] = self.color_target
        json_o['color_source'] = self.color_source
        json_o['duration_ms'] = self.duration_ms
        json_o['decay'] = self.decay
        json_o['FPS'] = self.FPS
        json_o['brightnes'] = self.brightnes
        json_o['led_count'] = self.led_count
        json_o['filter_frames'] = self.filter_frames
        json_o['loop'] = self.loop
        return json.dumps(json_o, indent=4)

    @staticmethod
    def from_json(json_text):
        json_o = json.loads(json_text)
        b = Blink(
            type = json_o['type'],
            color_target = json_o['color_target'],
            color_source = json_o['color_source'],
            fps = json_o['FPS'],
            duration_ms = int(json_o['duration_ms']),
            led_count = int(json_o['led_count']),
            decay = float(json_o['decay']),
            loop = int(json_o['loop']),
            brightnes = float(json_o['brightnes'])
        )
        b.add_filter_frames(json_o['filter_frames'])
        b.generate()
        return b