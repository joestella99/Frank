"""Frank's pose-based miniature desktop animation.

Real distinct silhouettes (walk, sit, sniff, sleep, carry) rather than a
sitting PNG which is stretched to imitate movement.
"""
import base64
from io import BytesIO
from pathlib import Path
import random

from PIL import Image, ImageOps

FRAME_MS = 110
TILE = (88, 92)
ORDER = ("idle", "walk1", "walk2", "sniff", "alert", "rest", "sleep", "carry")
WINDOW = (90, 98)


class PosePet:
    def __init__(self, asset_dir, seed=None):
        data_path = Path(asset_dir) / "frank_poses.png.b64"
        if not data_path.is_file():
            raise FileNotFoundError(
                "Frank's poses are missing. Re-download the complete Frank repo, "
                "including assets/frank_poses.png.b64."
            )
        raw = base64.b64decode(data_path.read_text(encoding="ascii").strip())
        sheet = Image.open(BytesIO(raw)).convert("RGBA")
        if sheet.size != (TILE[0] * len(ORDER), TILE[1]):
            raise ValueError("Unexpected Frank sprite-sheet dimensions")
        self.poses = {
            state: sheet.crop((i * TILE[0], 0, (i + 1) * TILE[0], TILE[1]))
            for i, state in enumerate(ORDER)
        }
        self.random = random.Random(seed)
        self.width, self.height = WINDOW
        self.direction = -1
        self.walking_enabled = True
        self.t = 0
        self.state = "idle"
        self.duration = 45
        self.in_state = 0
        self.velocity = 0.0
        self.fetch_frames = 0

    def set_state(self, state, duration):
        self.state = state
        self.duration = duration
        self.in_state = 0

    def choose(self):
        states = (
            ("idle", 40),
            ("look", 18),
            ("sniff", 15),
            ("walk", 18),
            ("trot", 4),
            ("rest", 4),
            ("sleep", 1),
        )
        if not self.walking_enabled:
            states = [(name, weight) for name, weight in states if name not in ("walk", "trot")]
        name = self.random.choices(
            [n for n, _ in states], [w for _, w in states], k=1
        )[0]
        ranges = {
            "idle": (22, 50),
            "look": (12, 28),
            "sniff": (18, 30),
            "walk": (35, 72),
            "trot": (18, 33),
            "rest": (30, 66),
            "sleep": (65, 120),
        }
        self.set_state(name, self.random.randint(*ranges[name]))
        if name in ("walk", "trot") and self.random.random() < 0.25:
            self.direction *= -1

    def found_job(self):
        self.fetch_frames = 40
        self.velocity = 0
        self.set_state("carry", self.fetch_frames)

    def step(self, x, limit):
        self.t += 1
        self.in_state += 1
        if self.fetch_frames > 0:
            self.fetch_frames -= 1
            if self.fetch_frames == 0:
                self.set_state("alert", 32)
        elif self.in_state >= self.duration:
            self.choose()

        walking = self.walking_enabled and self.state in ("walk", "trot", "carry")
        speed = 1.4 if self.state == "walk" else 2.6
        if self.state == "carry":
            speed = 1.15
        target = speed * self.direction if walking else 0.0
        self.velocity = self.velocity * 0.72 + target * 0.28
        x = min(max(0.0, x + self.velocity), float(limit))
        if walking and (x <= 0.0 or x >= float(limit)):
            self.direction *= -1
            self.velocity = 0
            if self.state != "carry":
                self.set_state("look", self.random.randint(15, 25))
        return x

    def current_pose(self):
        if self.state in ("idle", "look"):
            return "idle"
        if self.state == "walk":
            return "walk1" if (self.in_state // 3) % 2 == 0 else "walk2"
        if self.state == "trot":
            return "walk1" if (self.in_state // 2) % 2 == 0 else "walk2"
        if self.state == "sniff":
            return "sniff"
        if self.state == "sleep":
            return "sleep"
        if self.state == "rest":
            return "rest"
        if self.state == "carry":
            return "carry"
        return "alert"

    def frame(self):
        """Transparent-looking keyed image; no stretching or spinning portraits."""
        pose = self.poses[self.current_pose()].copy()
        # Drawn artwork faces right. Walk in the actual direction of travel.
        if self.direction < 0:
            pose = ImageOps.mirror(pose)
        page = Image.new("RGBA", WINDOW, (0, 0, 0, 0))
        page.alpha_composite(pose, ((self.width - pose.width) // 2, 2))
        # Transparent-color key matches the existing Tkinter desktop window.
        background = Image.new("RGB", WINDOW, (254, 0, 254))
        background.paste(page, (0, 0), page)
        return background
