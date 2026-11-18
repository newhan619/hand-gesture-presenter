"""가짜 카메라 프레임으로 종료와 오류 처리 경로를 검사한다."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from presenter.camera import run_camera
from presenter.core import Config
from tests.test_core import synthetic_hand


class CameraLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.cv2 = Mock()
        for name, value in dict(WINDOW_NORMAL=0, CAP_PROP_FRAME_WIDTH=3,
                                CAP_PROP_FRAME_HEIGHT=4, COLOR_BGR2RGB=4,
                                FONT_HERSHEY_SIMPLEX=0, LINE_AA=16).items():
            setattr(self.cv2, name, value)
        self.mp = Mock()
        self.capture = self.cv2.VideoCapture.return_value
        self.capture.isOpened.return_value = True
        self.frame = Mock()
        self.frame.shape = (480,640,3)
        self.capture.read.return_value = (True,self.frame)
        self.cv2.flip.return_value = self.frame
        self.cv2.waitKey.return_value = ord("q")
        self.landmarker = Mock()
        self.landmarker.detect_for_video.return_value = SimpleNamespace(hand_landmarks=[])
        self.context = Mock()
        self.context.__enter__ = Mock(return_value=self.landmarker)
        self.context.__exit__ = Mock(return_value=False)
        self.args = SimpleNamespace(enable_input=False, model="unused.task", camera=0)

    def run_with_fakes(self):
        with patch.dict("sys.modules", {"cv2":self.cv2,"mediapipe":self.mp}), \
             patch("presenter.camera.create_landmarker", return_value=self.context), \
             patch("builtins.print"):
            run_camera(self.args, Config())

    def test_quit_releases_camera_and_windows(self):
        self.run_with_fakes()
        self.capture.release.assert_called_once()
        self.cv2.destroyAllWindows.assert_called_once()
        self.context.__exit__.assert_called_once()

    def test_camera_open_failure_has_message_and_cleanup(self):
        self.capture.isOpened.return_value = False
        with self.assertRaisesRegex(RuntimeError, "--demo"):
            self.run_with_fakes()
        self.capture.release.assert_called_once()
        self.cv2.imshow.assert_not_called()

    def test_camera_read_failure_closes_model_and_camera(self):
        self.capture.read.return_value = (False,None)
        with self.assertRaisesRegex(RuntimeError, "읽지 못"):
            self.run_with_fakes()
        self.capture.release.assert_called_once()
        self.context.__exit__.assert_called_once()

    def test_single_hand_detection_draws_all_landmarks(self):
        points = synthetic_hand((True,)*5)
        self.landmarker.detect_for_video.return_value = SimpleNamespace(
            hand_landmarks=[points], hand_world_landmarks=[points],
            handedness=[[SimpleNamespace(category_name="Right")]])
        self.run_with_fakes()
        self.assertEqual(self.cv2.circle.call_count, 21)

    def test_shape_uses_image_landmarks_not_curled_world_estimate(self):
        # 실제 웹캠에서 편 손의 world 추정 좌표가 굽은 손가락처럼 나와 FIST/OTHER로 판정됐다.
        # 화면 좌표는 편 손, world는 주먹인 프레임으로 같은 상황을 만든다.
        self.landmarker.detect_for_video.return_value = SimpleNamespace(
            hand_landmarks=[synthetic_hand((True,)*5)],
            hand_world_landmarks=[synthetic_hand((False,)*5)],
            handedness=[[SimpleNamespace(category_name="Left")]])
        self.run_with_fakes()
        texts = [call.args[1] for call in self.cv2.putText.call_args_list]
        self.assertIn("Left | OPEN | fingers: 5", texts)

    def test_two_hands_draw_but_do_not_control(self):
        points = synthetic_hand((True,)*5)
        self.landmarker.detect_for_video.return_value = SimpleNamespace(
            hand_landmarks=[points,points])
        self.run_with_fakes()
        self.assertEqual(self.cv2.circle.call_count, 42)
