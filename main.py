"""실행 진입점. 예: python main.py --demo"""

import argparse
from importlib import metadata
from pathlib import Path
import platform
import sys

from presenter.core import Config
from presenter.model import DEFAULT_MODEL


def check_environment(model, check_model=False):
    print(f"Python {platform.python_version()} ({platform.architecture()[0]})")
    for package in ("mediapipe", "opencv-contrib-python", "numpy", "PyAutoGUI"):
        print(f"{package} {metadata.version(package)}")
    conflicts = []
    for package in ("opencv-python", "opencv-python-headless", "opencv-contrib-python-headless"):
        try:
            metadata.version(package)
            conflicts.append(package)
        except metadata.PackageNotFoundError:
            pass
    if conflicts:
        raise RuntimeError(f"OpenCV 중복 설치: {conflicts}. README의 복구 방법을 확인하세요.")
    import cv2
    import mediapipe
    import numpy as np
    import pyautogui
    print(f"import OK | OpenCV GUI: {'YES' if 'GUI:                           NONE' not in cv2.getBuildInformation() else 'NO'}")
    if check_model:
        from presenter.model import create_landmarker
        with create_landmarker(model) as landmarker:
            image = mediapipe.Image(image_format=mediapipe.ImageFormat.SRGB,
                                    data=np.zeros((480,640,3), dtype=np.uint8))
            result = landmarker.detect_for_video(image, 0)
            print(f"모델 추론 OK: 검은 영상에서 손 {len(result.hand_landmarks)}개")
    print("카메라와 PowerPoint 실제 동작은 이 검사에 포함되지 않습니다.")


def build_parser():
    parser = argparse.ArgumentParser(description="손 제스처 발표 컨트롤러 (기본: 카메라 + 모의 입력)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true", help="카메라 없이 모의 제스처 검증")
    mode.add_argument("--replay", type=Path, help="랜드마크 JSONL을 실제 입력 없이 재생")
    mode.add_argument("--download-model", action="store_true", help="Google 공식 손 모델 다운로드")
    mode.add_argument("--check-env", action="store_true", help="설치와 import 검사")
    mode.add_argument("--check-model", action="store_true", help="설치와 검은 영상 모델 추론 검사")
    parser.add_argument("--desktop", action="store_true", help="PPT 대신 데스크톱 모드 사용")
    parser.add_argument("--enable-input", action="store_true",
                        help="실제 입력 활성화 (데스크톱: Windows/macOS, PPT: Windows)")
    parser.add_argument("--camera", type=int, default=0, help="웹캠 번호 (기본 0)")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="손 모델 경로")
    parser.add_argument("--hold-frames", type=int, default=5)
    parser.add_argument("--cooldown", type=float, default=1.0)
    parser.add_argument("--swipe-distance", type=float, default=0.2)
    parser.add_argument("--smoothing", type=float, default=0.3)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.enable_input and any((args.demo, args.replay is not None, args.download_model,
                                 args.check_env, args.check_model)):
        parser.error("--enable-input은 실시간 카메라 실행에서만 사용할 수 있습니다.")
    try:
        config = Config(hold_frames=args.hold_frames, cooldown=args.cooldown,
                        swipe_distance=args.swipe_distance, smoothing=args.smoothing)
        if args.demo:
            if args.desktop:
                from presenter.desktop_demo import run_desktop_demo
                run_desktop_demo()
            else:
                from presenter.demo import run_demo
                run_demo()
        elif args.replay is not None:
            from presenter.replay import run_replay
            run_replay(args.replay, config, desktop=args.desktop)
        elif args.download_model:
            from presenter.model import download_model
            download_model(args.model)
        elif args.check_env or args.check_model:
            check_environment(args.model, args.check_model)
        else:
            from presenter.camera import run_camera
            run_camera(args, config, desktop=args.desktop)
    except KeyboardInterrupt:
        print("\n사용자가 실행을 종료했습니다.")
        return 130
    except Exception as exc:
        # 오류를 성공으로 숨기지 않고 팀원이 공유할 수 있는 메시지로 출력한다.
        print(f"오류 ({type(exc).__name__}): {exc}", file=sys.stderr)
        if isinstance(exc, (ImportError, metadata.PackageNotFoundError)):
            print("가상환경에서 python -m pip install -r requirements.txt 를 실행하세요.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
