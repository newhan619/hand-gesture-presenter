"""공식 Hand Landmarker 모델 준비. 웹캠 영상은 저장하지 않는다."""

import hashlib
from pathlib import Path
import ssl
import urllib.request
import zipfile


MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/1/hand_landmarker.task")
DEFAULT_MODEL = Path(__file__).resolve().parents[1] / "models" / "hand_landmarker.task"
MODEL_SHA256 = "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1"


def validate_model(path):
    path = Path(path)
    if not path.is_file():
        raise RuntimeError("손 모델이 없습니다. 먼저 python main.py --download-model 을 실행하세요.")
    if not zipfile.is_zipfile(path):
        raise RuntimeError("모델 파일 형식이 잘못됐습니다. 파일을 옮기고 다시 다운로드하세요.")
    with zipfile.ZipFile(path) as archive:
        if not {"hand_detector.tflite", "hand_landmarks_detector.tflite"}.issubset(archive.namelist()):
            raise RuntimeError("Hand Landmarker 모델 구성을 확인할 수 없습니다.")
        if archive.testzip() is not None:
            raise RuntimeError("모델 파일이 손상되었습니다.")
    return path


def download_model(path=DEFAULT_MODEL):
    path = Path(path)
    if path.exists():
        validate_model(path)
    else:
        import certifi
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".part")
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(MODEL_URL, timeout=60, context=context) as response:
                with temporary.open("wb") as target:
                    while chunk := response.read(1024*1024):
                        target.write(chunk)
            validate_model(temporary)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != MODEL_SHA256:
                raise RuntimeError("다운로드한 공식 모델의 SHA256이 예상값과 다릅니다.")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != MODEL_SHA256:
        raise RuntimeError("기존 모델이 다운로드 대상 공식 모델과 다릅니다. --model 경로를 확인하세요.")
    print(f"모델 준비 완료: {path}\nSHA256: {digest}")


def create_landmarker(path):
    import mediapipe as mp
    path = validate_model(path)
    options = mp.tasks.vision.HandLandmarkerOptions(
        # 모델 바이트를 넘겨 한글 Windows 경로의 네이티브 파일 열기 문제를 피한다.
        base_options=mp.tasks.BaseOptions(model_asset_buffer=path.read_bytes()),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_hands=2,  # 두 손이 보이면 제어를 정지하기 위해 둘까지 검출한다.
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )
    return mp.tasks.vision.HandLandmarker.create_from_options(options)
