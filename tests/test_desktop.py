import io
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
import unittest
from unittest.mock import Mock, patch

from main import main
from presenter.core import Event, classify_hand
from presenter.desktop import DesktopController, measure_desktop_hand
from presenter.desktop_demo import demo_landmarks
from presenter.output import DesktopOutput


def hand(shape, x=.5, y=.5, name="Right"):
    points = demo_landmarks(shape, x, y)
    return measure_desktop_hand(points, classify_hand(points), 1.0, name)


def kinds(events):
    return [event.kind for event in events]


class DesktopControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller = DesktopController()

    def test_short_pinching_clicks_once_on_release_without_drag(self):
        hover = self.controller.update(0, hand("POINT"))[0]
        self.assertEqual(self.controller.update(.07, hand("PINCH")), [])
        self.assertEqual(self.controller.update(.17, hand("POINT")), [Event("click", hover.position)])
        self.assertEqual(kinds(self.controller.update(.20, hand("POINT"))), ["cursor_move"])

    def test_drag_releases_on_open_without_also_clicking(self):
        self.controller.update(0, hand("POINT"))
        self.controller.update(.07, hand("PINCH"))
        self.assertEqual(kinds(self.controller.update(.16, hand("PINCH", x=.65))),
                         ["drag_start", "drag_move"])
        self.assertEqual(kinds(self.controller.update(.26, hand("PINCH", x=.7))), ["drag_move"])
        self.assertEqual(kinds(self.controller.update(.30, hand("POINT"))), ["drag_end"])

    def test_fist_with_touching_fingers_pauses_and_drops_drag(self):
        self.controller.update(0, hand("POINT"))
        self.controller.update(.07, hand("PINCH"))
        self.controller.update(.17, hand("PINCH", x=.65))
        fist = hand("FIST")
        self.assertLess(fist.pinch_gap, self.controller.config.pinch_close)
        self.assertEqual(kinds(self.controller.update(.23, fist)), ["drag_end", "pause"])
        self.assertEqual(self.controller.update(.33, hand("FIST", x=.7)), [])
        self.assertEqual(self.controller.action, "PAUSED")
        self.assertEqual(kinds(self.controller.update(.40, hand("POINT"))), ["resume", "cursor_move"])

    def test_pinch_beats_overlapping_scroll_swipe_and_cursor(self):
        for shape in ("TWO FINGERS", "OPEN", "POINT"):
            with self.subTest(shape=shape):
                controller = DesktopController()
                controller.update(0, hand(shape, x=.3, y=.5))
                overlapping = replace(hand(shape, x=.65, y=.3), pinch_gap=0.1)
                self.assertEqual(controller.update(.07, overlapping), [])
                self.assertEqual(controller.gesture, "PINCH")
                self.assertEqual(kinds(controller.update(.17, hand(shape, x=.65, y=.3))), ["click"])

    def test_interruption_prevents_phantom_click_and_releases_button(self):
        for interruption in ("loss", "long gap", "hand switch", "manual reset"):
            with self.subTest(interruption=interruption):
                controller = DesktopController()
                controller.update(0, hand("POINT"))
                controller.update(.07, hand("PINCH"))
                controller.update(.17, hand("PINCH", x=.65))
                if interruption == "manual reset":
                    events = controller.reset_tracking()
                elif interruption == "long gap":
                    events = controller.update(.9, hand("PINCH", x=.65))
                elif interruption == "hand switch":
                    events = controller.update(.23, hand("PINCH", x=.65, name="Left"))
                else:
                    events = controller.update(.23, None)
                self.assertEqual(kinds(events), ["drag_end"])
                self.assertEqual(controller.update(1.0, hand("PINCH", x=.7)), [])
                self.assertEqual(kinds(controller.update(1.07, hand("POINT"))), ["cursor_move"])

    def test_scroll_in_both_directions_and_switch_once_per_open_hand(self):
        self.controller.update(0, hand("TWO FINGERS"))
        self.assertGreater(self.controller.update(.1, hand("TWO FINGERS", y=.4))[0].steps, 0)
        self.assertLess(self.controller.update(.2, hand("TWO FINGERS", y=.55))[0].steps, 0)
        self.controller.update(.3, hand("OPEN", x=.3))
        self.assertEqual(kinds(self.controller.update(.45, hand("OPEN", x=.6))), ["switch_next"])
        for t in (.6, .9, 1.2, 1.4):
            self.assertEqual(self.controller.update(t, hand("OPEN", x=.25)), [])
        self.controller.update(1.5, hand("POINT"))
        self.controller.update(1.6, hand("OPEN", x=.65))
        self.assertEqual(kinds(self.controller.update(1.75, hand("OPEN", x=.3))), ["switch_previous"])


class DesktopIntegrationTests(unittest.TestCase):
    def test_demo_runs_on_landmarks_without_importing_camera_or_input(self):
        with patch.dict("sys.modules", {"cv2": None, "mediapipe": None, "pyautogui": None}):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(["--desktop", "--demo"]), 0)
        for message in ("click", "drag_start", "drag_end", "pause", "PASS", "실제 입력 0회"):
            self.assertIn(message, output.getvalue())
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["--desktop", "--demo", "--enable-input"])

    def test_windows_event_mapping_and_cleanup_without_real_input(self):
        output = DesktopOutput.__new__(DesktopOutput)
        output.gui = Mock(FAILSAFE=True)
        output.width, output.height, output.dragging = 1920, 1080, False
        output.emit([Event("click", (.5, .5)), Event("drag_start", (.5, .5)),
                     Event("drag_move", (1, 0)), Event("pause"), Event("scroll", steps=-2),
                     Event("switch_next"), Event("switch_previous")])
        output.close()
        output.gui.click.assert_called_once_with(button="left")
        output.gui.mouseDown.assert_called_once_with(button="left")
        output.gui.mouseUp.assert_called_once_with(button="left")
        output.gui.moveTo.assert_called_with(1917, 2)
        output.gui.scroll.assert_called_once_with(-2)
        output.gui.hotkey.assert_any_call("alt", "tab")
        output.gui.hotkey.assert_any_call("alt", "shift", "tab")
        self.assertTrue(output.gui.FAILSAFE)
        self.assertFalse(output.dragging)
