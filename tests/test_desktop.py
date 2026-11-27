import io
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

from main import main
from presenter.core import Event, Shape, classify_hand
from presenter.desktop import DesktopController, measure_desktop_hand
from presenter.desktop_demo import demo_landmarks
from presenter.output import DesktopOutput


def hand(shape, x=.5, y=.5, name="Right"):
    points = demo_landmarks(shape, x, y)
    return measure_desktop_hand(points, classify_hand(points), 1.0, name)


def four_fingers(x=.5, y=.5, name="Right"):
    """빠른 스와이프 중 엄지만 접힌 것처럼 보이는 프레임(OTHER, 손가락 4개)."""
    points = demo_landmarks("OPEN", x, y)
    points[1:5] = demo_landmarks("POINT", x, y)[1:5]
    return measure_desktop_hand(points, classify_hand(points), 1.0, name)


def bent_index_pinch(x=.5, y=.5):
    """엄지·검지는 붙어 있지만 검지가 굽어 펴짐·뻗음 조건을 모두 놓친 프레임."""
    pinch = hand("PINCH", x, y)
    pose = replace(pinch.pose, shape=Shape.OTHER, fingers=(False, False, True, True, True))
    return replace(pinch, pose=pose, index_extension=0.0)


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

    def test_drag_continues_when_index_bends_while_pinched(self):
        # 실제 웹캠: 집은 채 움직이는 중 검지가 굽어 drag_end 후 바로 drag_start가 됐다.
        self.controller.update(0, hand("POINT"))
        self.controller.update(.07, hand("PINCH"))
        self.assertEqual(kinds(self.controller.update(.16, hand("PINCH", x=.65))),
                         ["drag_start", "drag_move"])
        self.assertEqual(kinds(self.controller.update(.2, bent_index_pinch(x=.7))), ["drag_move"])
        self.assertEqual(kinds(self.controller.update(.24, hand("PINCH", x=.75))), ["drag_move"])
        self.assertEqual(kinds(self.controller.update(.3, hand("POINT"))), ["drag_end"])

    def test_new_pinch_still_requires_index(self):
        self.controller.update(0, hand("POINT"))
        self.assertEqual(self.controller.update(.07, bent_index_pinch()), [])
        self.assertNotEqual(self.controller.gesture, "PINCH")
        self.assertEqual(kinds(self.controller.update(.17, hand("POINT"))), ["cursor_move"])

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

    def test_brief_non_open_frame_during_swipe_keeps_history(self):
        # 실제 웹캠: 편 손을 빠르게 옮기는 중 한 프레임이 손가락 4개(OTHER)로 나와 전환이 안 됐다.
        flicker = four_fingers(x=.42)
        self.assertEqual(flicker.pose.count, 4)
        self.controller.update(0, hand("OPEN", x=.3))
        self.controller.update(.033, hand("OPEN", x=.36))
        self.assertEqual(self.controller.update(.067, flicker), [])
        self.assertEqual(kinds(self.controller.update(.1, hand("OPEN", x=.5))), ["switch_next"])

    def test_long_non_open_gap_still_clears_swipe_history(self):
        self.controller.update(0, hand("OPEN", x=.3))
        for t in (.05, .12, .21):  # 0.15초보다 길게 OPEN이 아님
            self.controller.update(t, four_fingers(x=.4))
        self.assertEqual(self.controller.update(.25, hand("OPEN", x=.5)), [])

    def test_swipe_grace_is_checked_when_open_returns(self):
        for delay, expected in ((.15, ["switch_next"]), (.20, [])):
            with self.subTest(delay=delay):
                controller = DesktopController()
                controller.update(0, hand("OPEN", x=.3))
                controller.update(.05, four_fingers(x=.35))
                self.assertEqual(kinds(controller.update(.05 + delay, hand("OPEN", x=.55))), expected)
                if delay > controller.config.swipe_grace:
                    self.assertEqual(kinds(controller.update(.05 + delay + .06, hand("OPEN", x=.80))),
                                     ["switch_next"])

    def test_short_shape_flicker_does_not_rearm_swipe_after_cooldown(self):
        self.controller.update(0, hand("OPEN", x=.30))
        self.assertEqual(kinds(self.controller.update(.10, hand("OPEN", x=.60))), ["switch_next"])
        for t, x in ((.39, .60), (.68, .40), (.90, .30)):
            self.assertEqual(self.controller.update(t, hand("OPEN", x=x)), [])
        self.assertEqual(self.controller.update(.95, four_fingers(x=.30)), [])
        self.assertEqual(self.controller.update(.99, hand("OPEN", x=.30)), [])
        self.assertEqual(self.controller.update(1.08, hand("OPEN", x=.58)), [])
        self.controller.update(1.15, hand("POINT"))
        self.controller.update(1.20, hand("OPEN", x=.60))
        self.assertEqual(kinds(self.controller.update(1.28, hand("OPEN", x=.30))), ["switch_previous"])

    def test_other_intentional_gestures_break_swipe_history(self):
        for shape in ("POINT", "TWO FINGERS", "PINCH", "FIST"):
            with self.subTest(shape=shape):
                controller = DesktopController()
                controller.update(0, hand("OPEN", x=.30))
                controller.update(.05, hand(shape, x=.35))
                self.assertNotIn("switch_next", kinds(controller.update(.10, hand("OPEN", x=.60))))


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
        gui = Mock()
        gui.size.return_value = (1920, 1080)
        with patch("presenter.output.sys.platform", "win32"), patch.dict("sys.modules", {"pyautogui": gui}):
            output = DesktopOutput()
        output.emit([Event("click", (.5, .5)), Event("drag_start", (.5, .5)),
                     Event("drag_move", (1, 0)), Event("pause"), Event("scroll", steps=-2),
                     Event("switch_next"), Event("switch_previous")])
        output.close()
        output.gui.click.assert_called_once_with(960, 540, button="left")
        output.gui.mouseDown.assert_called_once_with(960, 540, button="left")
        output.gui.mouseUp.assert_called_once_with(button="left")
        output.gui.moveTo.assert_called_with(1917, 2)
        output.gui.scroll.assert_called_once_with(-2)
        output.gui.hotkey.assert_any_call("alt", "tab")
        output.gui.hotkey.assert_any_call("alt", "shift", "tab")
        self.assertTrue(output.gui.FAILSAFE)
        self.assertFalse(output.dragging)

    def test_macos_drag_stays_pressed_and_swipes_use_command_without_real_input(self):
        gui = Mock()
        quartz = Mock()
        quartz.CGPreflightPostEventAccess.return_value = True
        quartz.CGDisplayBounds.return_value = SimpleNamespace(size=SimpleNamespace(width=1440, height=900))
        with patch("presenter.output.sys.platform", "darwin"), patch.dict(
                "sys.modules", {"Quartz": quartz, "pyautogui": gui}):
            output = DesktopOutput()
        output.emit([Event("cursor_move", (0, 0)), Event("click", (.5, .5)),
                     Event("drag_start", (.5, .5)), Event("drag_move", (1, 0)),
                     Event("drag_move", (0, 1)), Event("drag_end"), Event("scroll", steps=2),
                     Event("switch_next"), Event("switch_previous")])
        output.close()
        self.assertEqual(gui.method_calls, [
            call.moveTo(2, 2), call.click(720, 450, button="left"),
            call.mouseDown(720, 450, button="left"),
            call.dragTo(1437, 2, button="left", mouseDownUp=False),
            call.dragTo(2, 897, button="left", mouseDownUp=False), call.mouseUp(button="left"),
            call.scroll(2), call.hotkey("command", "tab"), call.hotkey("command", "shift", "tab"),
        ])
        self.assertTrue(gui.FAILSAFE)

    def test_macos_permission_error_explains_where_to_allow_input(self):
        quartz = Mock()
        quartz.CGPreflightPostEventAccess.return_value = False
        with patch("presenter.output.sys.platform", "darwin"), patch.dict(
                "sys.modules", {"Quartz": quartz, "pyautogui": None}):
            with self.assertRaisesRegex(RuntimeError, "손쉬운 사용"):
                DesktopOutput()
