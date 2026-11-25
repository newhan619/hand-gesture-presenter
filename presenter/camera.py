"""웹캠 입출력. 반전 전 영상을 추론하고 표시 좌표만 반전한다."""

import time

from .core import GestureController, Observation, Point, classify_hand
from .desktop import DesktopController, measure_desktop_hand
from .model import create_landmarker
from .output import DesktopOutput, DryRunOutput, PowerPointOutput


CONNECTIONS = ((0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
               (5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),
               (13,17),(0,17),(17,18),(18,19),(19,20))
WINDOW = "Hand Gesture Presenter"


def draw_hand(cv2, image, points):
    height, width = image.shape[:2]
    pixels = [(round(p.x*(width-1)), round(p.y*(height-1))) for p in points]
    for first, second in CONNECTIONS:
        cv2.line(image, pixels[first], pixels[second], (70, 210, 100), 2)
    for point in pixels:
        cv2.circle(image, point, 4, (30, 180, 255), -1)


def run_camera(args, config, *, desktop=False):
    import cv2
    import mediapipe as mp
    controller = DesktopController() if desktop else GestureController(config)
    if args.enable_input:
        output = DesktopOutput() if desktop else PowerPointOutput()
    else:
        output = DryRunOutput()
    capture = None
    paused = False
    was_ready = False
    timestamp_ms = -1
    previous = time.monotonic()
    fps = 0.0
    try:
        with create_landmarker(args.model) as landmarker:
            capture = cv2.VideoCapture(args.camera)
            if not capture.isOpened():
                raise RuntimeError(
                    f"카메라 {args.camera}를 열 수 없습니다. 연결·Windows 카메라 권한·"
                    "다른 앱의 카메라 사용을 확인하세요. 카메라 없는 PC는 --demo 로 실행하세요.")
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
            print("Q/ESC: 미리보기에서 종료 | P: 일시정지 | 터미널 Ctrl+C: 종료")
            if args.enable_input:
                if desktop:
                    print("데스크톱 입력을 시작합니다. 주먹을 쥐고 있는 동안 입력이 멈춥니다.")
                else:
                    print("5초 뒤 준비됩니다. PowerPoint 슬라이드 쇼 창을 선택하세요.")
                    time.sleep(5)
            else:
                print("모의 입력 모드: 카메라만 사용하며 키보드·마우스는 제어하지 않습니다.")
            while True:
                ok, frame = capture.read()
                if not ok or frame is None:
                    raise RuntimeError("카메라 영상을 읽지 못했습니다. 연결과 다른 앱 사용을 확인하세요.")
                now = time.monotonic()
                delta = now-previous
                previous = now
                fps = 0.9*fps + 0.1/max(delta, 1e-6)
                timestamp_ms = max(timestamp_ms+1, int(now*1000))
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = landmarker.detect_for_video(
                    mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms)
                display = cv2.flip(frame, 1)
                pose = None
                hand = "unknown"
                desktop_hand = None
                for index, raw in enumerate(result.hand_landmarks):
                    mirrored = [Point(1-p.x, p.y, p.z) for p in raw]
                    draw_hand(cv2, display, mirrored)
                    if len(result.hand_landmarks) == 1:
                        # world 좌표는 실제 웹캠에서 편 손가락도 굽게 추정해 화면 좌표로 판별한다.
                        aspect_ratio = frame.shape[1]/frame.shape[0]
                        pose = classify_hand(mirrored, aspect_ratio=aspect_ratio)
                        hand = result.handedness[index][0].category_name
                        if desktop:
                            desktop_hand = measure_desktop_hand(mirrored, pose, aspect_ratio, hand)

                ready = not paused and (not args.enable_input or output.ready())
                if not ready:
                    events = controller.reset_tracking()
                    if was_ready:
                        output.emit(events)
                else:
                    if not was_ready:
                        # 다른 창에 있는 동안 보류한 포인터 종료를 PPT 복귀 시 처리한다.
                        output.close()
                        controller.reset_tracking()
                    if desktop:
                        events = controller.update(now, desktop_hand)
                    else:
                        observation = Observation(now, None) if pose is None else Observation(
                            now, pose.shape, pose.palm, pose.tip, hand)
                        events = controller.update(observation)
                    output.emit(events)
                was_ready = ready
                status = ("PAUSED" if paused else
                          "WAIT: select PowerPoint slide show" if not ready else
                          "LIVE INPUT" if args.enable_input else "DRY RUN - no keyboard/mouse input")
                detection = ("TWO HANDS - control stopped" if len(result.hand_landmarks) > 1 else
                             "NO HAND" if pose is None else
                             f"{hand} | {pose.shape.value} | fingers: {pose.count}")
                if desktop:
                    gesture = detection if pose is None else (
                        f"{hand} | {controller.gesture if ready else pose.shape.value} | fingers: {pose.count}")
                    action = "PAUSED" if paused else controller.action
                    lines = [f"Mode: DESKTOP | {status}", f"Shape: {gesture}",
                             f"Action: {action} | FPS {fps:.1f}",
                             "Fist: pause | Q/ESC: quit | P: pause/resume"]
                else:
                    lines = [f"Mode: PPT | {status}", detection,
                             f"{controller.mode} | hold {controller.hold_count}/{config.hold_frames}"
                             f" | armed: {controller.armed} | FPS {fps:.1f}",
                             "Open hand: swipe | Index: pointer | Fist: reset | Q: quit | P: pause"]
                cv2.rectangle(display, (0, 0), (display.shape[1], 112), (24, 24, 24), -1)
                for line_index, line in enumerate(lines):
                    cv2.putText(display, line, (10, 24+line_index*25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (240,240,240), 1, cv2.LINE_AA)
                cv2.imshow(WINDOW, display)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):
                    break
                if key in (ord("p"), ord("P")):
                    paused = not paused
                if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                    break
    finally:
        try:
            output.close()
        finally:
            if capture is not None:
                capture.release()
            cv2.destroyAllWindows()
