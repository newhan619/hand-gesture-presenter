import itertools
import math
import unittest

from presenter.core import (Config, GestureController, Observation, Point, Shape,
                            angle, classify_hand)


def synthetic_hand(fingers):
    """실제 인식률을 의미하지 않는, 관절 계산 검증용 합성 좌표."""
    points = [Point(0.5, 0.8)] * 21
    if fingers[0]:
        points[1:5] = [Point(.48,.72), Point(.40,.65), Point(.32,.58), Point(.24,.51)]
    else:
        points[1:5] = [Point(.48,.72), Point(.40,.65), Point(.46,.61), Point(.51,.68)]
    for mcp, x, extended in zip((5,9,13,17), (.40,.48,.56,.64), fingers[1:]):
        points[mcp] = Point(x, .55)
        if extended:
            points[mcp+1:mcp+4] = [Point(x,.41), Point(x,.31), Point(x,.21)]
        else:
            points[mcp+1:mcp+4] = [Point(x,.43), Point(x+.04,.51), Point(x,.62)]
    return points


class HandClassifierTests(unittest.TestCase):
    def test_all_32_finger_combinations_under_mirror_and_rotation(self):
        for fingers in itertools.product((False,True), repeat=5):
            for rotation in (0, .5, 1.57, 3.14):
                for mirror in (-1,1):
                    with self.subTest(fingers=fingers, rotation=rotation, mirror=mirror):
                        points = [Point(mirror*(p.x*math.cos(rotation)-p.y*math.sin(rotation)),
                                        p.x*math.sin(rotation)+p.y*math.cos(rotation))
                                  for p in synthetic_hand(fingers)]
                        pose = classify_hand(points)
                        self.assertEqual(pose.fingers, fingers)
                        self.assertEqual(pose.count, sum(fingers))

    def test_world_coordinates_handle_out_of_plane_rotation(self):
        points = synthetic_hand((True,True,True,True,True))
        world = [Point(p.x*math.cos(1.2), p.y, p.x*math.sin(1.2)) for p in points]
        self.assertEqual(classify_hand(points, world=world).shape, Shape.OPEN)

    def test_aspect_ratio_correction(self):
        points = synthetic_hand((False,True,False,False,False))
        normalized = [Point(p.x/2, p.y) for p in points]
        self.assertEqual(classify_hand(normalized, aspect_ratio=2).shape, Shape.POINT)

    def test_shapes(self):
        for bits, shape in [((False,)*5, Shape.FIST), ((True,)*5, Shape.OPEN),
                            ((False,True,False,False,False), Shape.POINT),
                            ((False,True,True,False,False), Shape.OTHER)]:
            self.assertEqual(classify_hand(synthetic_hand(bits)).shape, shape)

    def test_invalid_and_collapsed_points(self):
        self.assertEqual(angle(Point(0,0), Point(0,0), Point(0,0)), 0)
        self.assertEqual(classify_hand([Point(0,0)]*21).count, 0)
        with self.assertRaises(ValueError):
            classify_hand([Point(0,0)]*20)
        with self.assertRaises(ValueError):
            classify_hand([Point(math.nan,0)]*21)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller = GestureController()
        self.time = 0.0

    def feed(self, shape, frames=1, start=.4, end=None, y=.5, step=1/30, hand="Right"):
        events = []
        end = start if end is None else end
        for index in range(frames):
            self.time += step
            x = start + (end-start)*index/max(1,frames-1)
            events.extend(self.controller.update(Observation(self.time, shape, (x,y), (x,y), hand)))
        return events

    def kinds(self, events):
        return [e.kind for e in events]

    def swipe(self, direction=1):
        self.feed(Shape.OPEN, 5, start=.5)
        return self.feed(Shape.OPEN, 8, start=.5, end=.5+.3*direction)

    def test_directions(self):
        for direction, expected in ((1,"next"),(-1,"previous")):
            self.setUp()
            self.assertEqual(self.kinds(self.swipe(direction)), [expected])

    def test_ten_swipes_each_direction(self):
        for direction in (1,-1):
            for _ in range(10):
                self.feed(Shape.FIST, 35)
                self.assertEqual(self.kinds(self.swipe(direction)),
                                 ["next" if direction == 1 else "previous"])

    def test_swipe_requires_five_open_frames(self):
        events = self.feed(Shape.OPEN, 4, start=.2, end=.8)
        self.assertEqual(events, [])

    def test_continuous_hand_does_not_repeat_even_after_cooldown(self):
        self.swipe()
        self.assertEqual(self.feed(Shape.OPEN, 100, start=.2, end=.9), [])

    def test_rearm_requires_stable_fist(self):
        self.swipe()
        self.feed(Shape.FIST, 4)
        self.feed(Shape.OTHER, 40)
        self.assertEqual(self.swipe(), [])
        self.feed(Shape.FIST, 5)
        self.assertEqual(self.kinds(self.swipe()), ["next"])

    def test_cooldown_blocks_even_after_fist(self):
        self.swipe()
        self.feed(Shape.FIST, 5)
        self.assertEqual(self.swipe(-1), [])
        self.feed(Shape.FIST, 35)
        self.assertEqual(self.kinds(self.swipe(-1)), ["previous"])

    def test_vertical_movement_is_rejected(self):
        self.feed(Shape.OPEN, 5)
        events = []
        for i in range(8):
            events += self.feed(Shape.OPEN, start=.4+.04*i, y=.3+.07*i)
        self.assertEqual(events, [])

    def test_slow_movement_does_not_swipe(self):
        self.feed(Shape.OPEN, 5, start=.2)
        self.assertEqual(self.feed(Shape.OPEN, 60, start=.2, end=.5), [])

    def test_stationary_jitter_does_not_swipe(self):
        self.feed(Shape.OPEN, 5)
        events = []
        for i in range(150):
            events += self.feed(Shape.OPEN, start=.5+.02*math.sin(i))
        self.assertEqual(events, [])

    def test_point_requires_five_frames(self):
        self.assertEqual(self.feed(Shape.POINT, 4), [])
        self.assertEqual(self.kinds(self.feed(Shape.POINT)), ["pointer_on","move"])

    def test_pointer_never_swipes_and_requires_fist_to_exit(self):
        self.feed(Shape.POINT, 5)
        self.assertEqual(self.feed(Shape.OPEN, 40, start=.2, end=.9), [])
        self.assertEqual(self.controller.mode, "POINTER")
        self.assertEqual(self.feed(Shape.FIST, 3, step=.1), [])
        self.assertEqual(self.kinds(self.feed(Shape.FIST, step=.1)), ["pointer_off"])
        self.assertEqual(self.controller.mode, "SLIDES")

    def test_brief_or_interrupted_fist_does_not_turn_pointer_off_at_high_sensitivity(self):
        self.controller = GestureController(Config(hold_frames=2, smoothing=1.0))
        self.assertEqual(self.kinds(self.feed(Shape.POINT, 2)), ["pointer_on", "move"])
        self.assertEqual(self.feed(Shape.FIST, 2, step=.1), [])
        self.assertEqual(self.kinds(self.feed(Shape.POINT)), ["move"])
        self.assertEqual(self.feed(Shape.FIST, 2, step=.1), [])
        self.assertEqual(self.feed(None, step=.1), [])
        self.assertEqual(self.feed(Shape.FIST, 3, step=.1), [])
        self.assertEqual(self.kinds(self.feed(Shape.FIST, step=.1)), ["pointer_off"])

    def test_smoothing(self):
        initial = self.feed(Shape.POINT, 5, start=.3)[-1].position[0]
        updated = self.feed(Shape.POINT, start=.7)[-1].position[0]
        self.assertAlmostEqual(initial, .25)
        self.assertAlmostEqual(updated, .7*.25 + .3*.75)

    def test_clamping(self):
        events = self.feed(Shape.POINT, 5, start=2, y=-2)
        self.assertEqual(events[-1].position, (1.0,0.0))

    def test_short_hand_loss_freezes_and_resumes_without_old_coordinates(self):
        self.feed(Shape.POINT, 5, start=.3)
        self.assertEqual(self.feed(None, 3, step=.1), [])
        events = self.feed(Shape.POINT, start=.8)
        self.assertEqual(self.kinds(events), ["move"])
        self.assertAlmostEqual(events[0].position[0], .875)

    def test_long_hand_loss_turns_pointer_off_and_requires_new_hold(self):
        self.feed(Shape.POINT, 5)
        self.assertEqual(self.feed(None, 4, step=.1), [])
        self.assertEqual(self.kinds(self.feed(None, step=.15)), ["pointer_off"])
        self.assertEqual(self.feed(None, 300), [])  # 미검출 10초
        self.assertEqual(self.feed(Shape.POINT, 4, start=.8), [])
        events = self.feed(Shape.POINT, start=.8)
        self.assertEqual(self.kinds(events), ["pointer_on","move"])
        self.assertAlmostEqual(events[-1].position[0], .875)

    def test_hand_returning_after_timeout_does_not_resume_existing_pointer(self):
        self.feed(Shape.POINT, 5)
        self.assertEqual(self.feed(None, 4, step=.1), [])
        self.assertEqual(self.kinds(self.feed(Shape.POINT, step=.15)), ["pointer_off"])
        self.assertEqual(self.controller.hold_count, 1)

    def test_tracking_loss_does_not_bypass_slide_lock(self):
        self.swipe()
        self.feed(None, 40)
        self.assertEqual(self.swipe(-1), [])

    def test_hand_change_resets_stability(self):
        self.feed(Shape.POINT, 4, hand="Right")
        self.assertEqual(self.feed(Shape.POINT, hand="Left"), [])
        self.assertEqual(self.controller.hold_count, 1)

    def test_long_frame_gap_resets_pointer(self):
        self.feed(Shape.POINT, 5)
        self.assertEqual(self.kinds(self.feed(Shape.POINT, step=1)), ["pointer_off"])
        self.assertEqual(self.controller.hold_count, 1)

    def test_invalid_time_is_rejected(self):
        self.feed(Shape.OPEN)
        for timestamp in (self.time, self.time-1, math.nan, math.inf):
            with self.assertRaises(ValueError):
                self.controller.update(Observation(timestamp, Shape.OPEN))

    def test_invalid_configuration(self):
        for values in (dict(hold_frames=0), dict(cooldown=-1), dict(smoothing=0),
                       dict(pointer_margin=.5), dict(swipe_distance=math.nan),
                       dict(pointer_fist_hold=0), dict(pointer_loss_grace=math.nan)):
            with self.assertRaises(ValueError):
                Config(**values)


if __name__ == "__main__":
    unittest.main()
