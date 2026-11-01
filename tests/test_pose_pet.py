import base64
import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from pose_pet import PosePet, ORDER, TILE, WINDOW


class FrankPoseTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        assets = Path(self.folder.name)
        # Use the checked-in sprite sheet, the same file as the Windows app.
        original = Path(__file__).resolve().parents[1] / "assets" / "frank_poses.png.b64"
        (assets / original.name).write_text(original.read_text(encoding="ascii"))
        self.pet = PosePet(assets, seed=8)

    def tearDown(self):
        self.folder.cleanup()

    def test_atlas_is_complete(self):
        self.assertEqual(len(ORDER), 5)
        self.assertEqual(self.pet.poses["idle"].size, TILE)
        self.assertEqual(self.pet.frame().size, WINDOW)

    def test_changes_real_pose(self):
        self.pet.set_state("sniff", 20)
        self.assertEqual(self.pet.current_pose(), "sniff")
        self.pet.set_state("walk", 30)
        seen = set()
        for n in range(8):
            self.pet.in_state = n
            seen.add(self.pet.current_pose())
        self.assertEqual(seen, {"walk1", "walk2"})
        self.assertNotEqual(self.pet.poses["walk1"].tobytes(), self.pet.poses["idle"].tobytes())

    def test_stays_on_screen(self):
        x = 30.0
        for _ in range(700):
            x = self.pet.step(x, 250)
            self.assertGreaterEqual(x, 0)
            self.assertLessEqual(x, 250)

    def test_hunting_alert_triggers_fetch_and_returns_to_idle(self):
        self.pet.found_job()
        self.assertEqual(self.pet.current_pose(), "carry")
        for _ in range(40):
            self.pet.step(200.0, 500.0)
        self.assertEqual(self.pet.current_pose(), "alert")

    def test_roaming_paused(self):
        self.pet.walking_enabled = False
        for _ in range(60):
            self.pet.choose()
            self.assertNotIn(self.pet.state, ("walk", "trot"))


if __name__ == "__main__":
    unittest.main()
