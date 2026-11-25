from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from main import main
from presenter.core import Config, Event
from presenter.demo import run_demo
from presenter.output import PowerPointOutput
from presenter.replay import run_replay
from tests.test_core import synthetic_hand


class IntegrationTests(unittest.TestCase):
    def test_demo_never_imports_camera_or_input(self):
        with patch.dict("sys.modules", {"cv2": None, "mediapipe": None, "pyautogui": None}):
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(["--demo"]), 0)
            self.assertIn("PASS", output.getvalue())

    def test_replay_uses_raw_landmarks_and_detects_pointer_loss(self):
        points = synthetic_hand((False,True,False,False,False))
        records = [dict(time=i/30, hand="Right",
                        landmarks=[[p.x,p.y,p.z] for p in points]) for i in range(5)]
        records.extend(dict(time=i/30, landmarks=None) for i in range(5, 21))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"synthetic.jsonl"
            path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
            with redirect_stdout(io.StringIO()) as output:
                run_replay(path, Config())
            self.assertIn("pointer_on", output.getvalue())
            self.assertIn("pointer_off", output.getvalue())

    def test_live_input_rejected_for_replay_or_demo(self):
        for mode in (["--demo"], ["--replay","unused.jsonl"], ["--check-env"]):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main(mode+["--enable-input"])
            self.assertEqual(error.exception.code, 2)

    def test_output_is_blocked_when_powerpoint_not_foreground(self):
        # __init__를 건너뛰고 가짜 GUI를 넣어 OS 입력이 발생하지 않게 한다.
        output = PowerPointOutput.__new__(PowerPointOutput)
        output.gui = Mock()
        output.ready = Mock(return_value=False)
        output.pointer_active = False
        output.emit([Event("next"), Event("pointer_on"), Event("move", (.5,.5))])
        self.assertEqual(output.gui.mock_calls, [])

    def test_output_maps_events_without_real_input(self):
        output = PowerPointOutput.__new__(PowerPointOutput)
        output.gui = Mock()
        output.ready = Mock(return_value=True)
        output.width, output.height = 1920,1080
        output.pointer_active = False
        output.emit([Event("next"), Event("previous"), Event("pointer_on"),
                     Event("move", (0,1)), Event("pointer_off")])
        output.gui.press.assert_any_call("right")
        output.gui.press.assert_any_call("left")
        output.gui.hotkey.assert_any_call("ctrl","l")
        output.gui.hotkey.assert_any_call("ctrl","a")
        output.gui.moveTo.assert_called_once_with(2,1077)
        self.assertFalse(output.pointer_active)


if __name__ == "__main__":
    unittest.main()
