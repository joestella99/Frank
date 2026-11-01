"""Frank's miniature desktop-pet motion engine.

All animations are generated from the user's original Frank illustration.
Timings are intentionally irregular: Frank rests, watches, sniffs and explores,
rather than endlessly skating across the taskbar.
"""
import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageOps

FRAME_MS = 75
SCALE = (61, 79)
CANVAS = (90, 98)

# Behaviour, weighted probability. Duration in 75 ms frames.
BEHAVIOURS = (
    ("idle", 36, (34, 78)),
    ("look", 17, (18, 38)),
    ("sniff", 16, (15, 34)),
    ("stroll", 22, (28, 66)),
    ("trot", 6, (13, 30)),
    ("nap", 3, (70, 150)),
)


class MotionController:
    def __init__(self, sprite, background="#fe00fe", seed=None):
        self.random = random.Random(seed)
        self.source = sprite.convert("RGBA").copy()
        self.source.thumbnail(SCALE, Image.Resampling.LANCZOS)
        self.background = background
        self.width, self.height = CANVAS
        self.state = "idle"
        self.t = 0
        self.in_state = 0
        self.state_duration = 44
        self.direction = -1
        self.walking_enabled = True
        self.alert_left = 0
        self.blink_left = 0
        self.next_blink = self.random.randint(32, 75)
        self.velocity = 0.0
        self.easing = 0.0
        self.pause_before_turn = 0

    def choose(self):
        options = BEHAVIOURS
        if not self.walking_enabled:
            options = tuple(b for b in BEHAVIOURS if b[0] not in ("stroll", "trot"))
        choice = self.random.choices(
            options, weights=[item[1] for item in options], k=1
        )[0]
        self.state = choice[0]
        self.state_duration = self.random.randint(*choice[2])
        self.in_state = 0
        if self.state in ("stroll", "trot") and self.random.random() < 0.3:
            self.direction *= -1
        self.easing = 0.0

    def found_job(self):
        self.alert_left = 42
        self.state = "alert"
        self.in_state = 0
        self.state_duration = 42
        self.velocity = 0.0

    def step(self, current_x, max_x):
        """Advance by one 75 ms frame; returns a safe horizontal position."""
        self.t += 1
        self.in_state += 1
        if self.alert_left:
            self.alert_left -= 1
            self.state = "alert"
            self.velocity *= 0.7
        elif self.in_state >= self.state_duration:
            self.choose()

        if self.blink_left:
            self.blink_left -= 1
        elif self.t >= self.next_blink:
            self.blink_left = 2
            self.next_blink = self.t + self.random.randint(30, 82)

        walking = self.walking_enabled and self.state in ("stroll", "trot")
        pace = (0.85 if self.state == "stroll" else 1.6) * self.direction if walking else 0
        if self.state == "sniff" and self.walking_enabled:
            pace = self.direction * 0.16
        self.velocity = self.velocity * 0.70 + pace * 0.30
        next_x = current_x + self.velocity
        if next_x <= 1 or next_x >= max_x - 1:
            next_x = max(0.0, min(float(max_x), next_x))
            if walking:
                self.direction *= -1
                self.state = "look"
                self.in_state = 0
                self.state_duration = self.random.randint(16, 35)
                self.velocity = 0
        return next_x

    def frame(self):
        """Render one portrait frame with breathing, ears/head angle, gait and shadow.

        Retains the original image rather than replacing Frank with new graphics.
        A true articulated walk will ultimately need separate standing/leg artwork.
        """
        age = self.in_state
        t = self.t
        breathing = math.sin(t * 0.19)
        sx, sy, angle = 1.0, 1.0, 0.0
        dx, lift = 0, 0
        shadow_w = 19
        tail_offset = 0

        if self.state == "idle":
            sy = 1.0 + 0.014 * breathing
            sx = 1.0 - 0.008 * breathing
            angle = 1.0 * math.sin(t * 0.09)
            tail_offset = math.sin(t * 0.36) * 2
        elif self.state == "look":
            # Curious head turns: a short glance and slower return.
            angle = 4.2 * math.sin(age * 0.18)
            lift = 1.3 * math.sin(age * 0.13)
            sy = 1.0 + 0.012 * breathing
        elif self.state == "sniff":
            sy = 0.965 + 0.01 * breathing
            sx = 1.025
            angle = -4.0 + 2.0 * math.sin(age * 0.23)
            lift = -2.4 - 1.2 * math.sin(age * 0.35)
        elif self.state in ("stroll", "trot"):
            pace = 0.61 if self.state == "stroll" else 0.89
            stride = math.sin(age * pace)
            bounce = abs(stride)
            # Weight transfer is synchronized to horizontal travel.
            lift = 2.2 * bounce if self.state == "stroll" else 4.1 * bounce
            sx = 1.0 + (0.027 if self.state == "stroll" else 0.050) * bounce
            sy = 1.0 - (0.021 if self.state == "stroll" else 0.035) * bounce
            angle = self.direction * (2.0 + 1.35 * stride)
            dx = self.direction * 0.9 * stride
            shadow_w += 3
            tail_offset = stride * 2
        elif self.state == "nap":
            sy = 0.93 + 0.012 * breathing
            sx = 1.03
            angle = -3.0
            lift = -3
        elif self.state == "alert":
            bounce = abs(math.sin(age * 0.34))
            sy = 1.0 + 0.038 * bounce
            sx = 1.0 - 0.015 * bounce
            angle = self.direction * 4.0 * math.sin(age * 0.25)
            lift = 2.8 * bounce
            shadow_w += 4

        animal = self.source.resize((
            max(10, round(self.source.width * sx)),
            max(10, round(self.source.height * sy))
        ), Image.Resampling.LANCZOS)
        if self.direction > 0:
            animal = ImageOps.mirror(animal)
        if abs(angle) > 0.05:
            animal = animal.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)

        page = Image.new("RGBA", CANVAS)
        x = (self.width - animal.width) // 2 + round(dx)
        y = self.height - animal.height - 8 - round(lift)
        # The shadow belongs behind Frank's paws, never on top of him.
        shadow = Image.new("RGBA", (self.width, 14))
        d = ImageDraw.Draw(shadow)
        radius = 15 + shadow_w
        d.ellipse(((self.width - radius)//2, 4, (self.width + radius)//2, 11), fill=(0, 0, 0, 74))
        shadow = shadow.filter(ImageFilter.GaussianBlur(3.5))
        page.alpha_composite(shadow, (0, self.height - 14))
        page.alpha_composite(animal, (x, y))

        # Tiny non-invasive blink: alpha-tinted eyelid line over portrait eyes.
        # Avoid drawing over the eyes during walking/turning as they may shift.
        if self.blink_left and self.state in ("idle", "nap") and abs(angle) < 1.6:
            pen = ImageDraw.Draw(page)
            eye_y = y + int(animal.height * 0.34)
            face_x = x + int(animal.width * 0.56)
            pen.line((face_x - 6, eye_y, face_x - 2, eye_y + 1), fill=(31, 25, 24, 220), width=2)
            pen.line((face_x + 4, eye_y, face_x + 8, eye_y + 1), fill=(31, 25, 24, 220), width=2)

        # Preserve window chromakey for transparent Windows desktop pet.
        canvas = Image.new("RGB", CANVAS, self.background)
        canvas.paste(page, (0, 0), page)
        return canvas
