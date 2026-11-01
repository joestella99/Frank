"""Headless regression tests for Frank's miniature companion."""
import unittest

try:
    from PIL import Image
    from pet_motion import MotionController
except ImportError:
    Image = None
    MotionController = None


@unittest.skipIf(Image is None, "Pillow is not installed")
class MotionTests(unittest.TestCase):
    def make_dog(self):
        image = Image.new("RGBA", (130, 180), (0, 0, 0, 0))
        for x in range(30, 100):
            for y in range(30, 170):
                image.putpixel((x, y), (45, 36, 32, 255))
        return MotionController(image, seed=10)

    def test_tiny_transparent_keyed_frame(self):
        dog = self.make_dog()
        self.assertEqual(dog.frame().size, (90, 98))
        self.assertEqual(dog.frame().getpixel((0, 0)), (254, 0, 254))

    def test_moves_within_screen_and_changes_states(self):
        dog = self.make_dog()
        x = 120.0
        observed = set()
        for _ in range(500):
            x = dog.step(x, 600)
            self.assertLessEqual(x, 600)
            self.assertGreaterEqual(x, 0)
            observed.add(dog.state)
            dog.frame()
        self.assertGreaterEqual(len(observed), 3)

    def test_alert_and_pause(self):
        dog = self.make_dog()
        dog.found_job()
        self.assertEqual(dog.state, "alert")
        for _ in range(5):
            dog.step(10, 200)
            self.assertEqual(dog.state, "alert")
        dog.walking_enabled = False
        dog.alert_left = 0
        dog.choose()
        self.assertNotIn(dog.state, ("stroll", "trot"))


if __name__ == "__main__":
    unittest.main()
