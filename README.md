# 손 제스처 발표 컨트롤러

웹캠으로 한 손을 인식해 PowerPoint 슬라이드 쇼를 넘기고 검지로 레이저 포인터를 움직이는 Python 프로그램이다. 최종 제안서의 핵심 기능 세 가지를 구현한 초기 버전이다. 웹캠 영상과 랜드마크를 자동 저장하지 않는다.

**현재 검증 범위:** Windows의 Python 3.12.14에서 패키지 설치, 모델 로딩과 검은 영상 추론, 모의 제스처, 자동 테스트를 확인했다. 실제 손 인식률과 PowerPoint 연동은 웹캠이 있는 팀원의 확인이 필요하다. 사용자 제스처 학습과 판서는 포함하지 않았다.

## 지금 카메라 없이 실행하기

모의 실행은 추가 패키지 없이 Python만으로 실행할 수 있다. 새로 내려받은 PC에서는 다음 명령을 사용한다.

```powershell
py -3.12 main.py --demo
```

아래 설치 과정을 마쳐 `.venv`가 있는 PC에서는 PowerShell에서 실행 스크립트를 사용할 수 있다.

```powershell
.\run.ps1 -Mode demo
```

스크립트 실행이 제한되어 있으면 가상환경 Python을 직접 실행할 수 있다.

```powershell
.\.venv\Scripts\python.exe -X utf8 main.py --demo
```

예상 출력은 `next → previous → pointer_on → pointer_off → PASS`다. 이 모드는 카메라를 열거나 키보드·마우스를 제어하지 않는다. 일반 Python만 있는 다른 PC에서도 `python main.py --demo`로 실행할 수 있다.

## 팀원 PC 설치

Windows 11, **Python 3.12 64비트**, 웹캠, 데스크톱 PowerPoint를 기준으로 한다. 단일 기본 모니터의 전체 화면 슬라이드 쇼가 대상이다. Python 설치는 [공식 배포처](https://www.python.org/downloads/windows/)에서 진행한다.

1. 저장소 파일을 내려받거나 복제한 뒤 이 폴더에서 PowerShell을 연다.
2. 아래 설치 명령으로 `.venv`를 만들고 검증한 패키지 버전과 공식 모델을 준비한다. 처음 한 번은 인터넷 연결이 필요하다.
3. 설치 확인과 모의 실행을 진행한다.

```powershell
.\setup.ps1
.\run.ps1 -Mode check
.\run.ps1 -Mode demo
```

Python 경로를 직접 지정하려면 `setup.ps1 -PythonPath 'C:\경로\python.exe'`를 사용한다. 시스템의 실행 정책 때문에 스크립트를 사용할 수 없으면 다음 명령을 순서대로 실행한다. 가상환경 활성화는 필요 없다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 main.py --download-model
.\.venv\Scripts\python.exe -X utf8 main.py --check-model
```

`requirements.txt`는 직접 사용하는 패키지, `requirements.lock.txt`는 이 PC에서 설치·검사한 전체 버전이다. MediaPipe가 요구하는 `opencv-contrib-python`에 카메라·화면 표시 기능도 있으므로 OpenCV 배포판은 이것 하나만 사용한다.

## 웹캠 인식 확인

```powershell
.\run.ps1 -Mode preview
# 다른 카메라 번호를 사용한다면
.\run.ps1 -Mode preview -Camera 1
```

반전 미리보기에 관절 21개와 연결선, 좌우 손, 손가락 수, 손 모양, 유지 프레임과 FPS가 표시된다. 화면 글자는 OpenCV 기본 폰트가 지원하는 영문을 사용했다. 이 단계에서는 실제 PPT 입력을 보내지 않는다.

| 표시 | 뜻 |
| --- | --- |
| FIST | 주먹 |
| OPEN | 손가락 다섯 개를 편 손 |
| POINT | 검지만 편 손 |
| OTHER | 그 밖의 손 모양 |
| NO HAND | 손 미검출, 제어 정지 |
| TWO HANDS | 두 손 검출, 제어 정지 |
| armed | 스와이프를 다시 받을 수 있는 상태 |

`Q` 또는 `Esc`는 미리보기 창에 포커스가 있을 때 종료한다. 창 닫기와 터미널 `Ctrl+C`로도 종료할 수 있다. `P`는 미리보기에서 일시정지/재개다. 손 전체를 밝은 곳에서 카메라에 보여주고 [팀원 체크리스트](docs/camera_test_checklist.md)를 따라 시험한다.

## PowerPoint 실제 조작

1. 먼저 미리보기에서 모양과 방향을 확인한다.
2. PPT를 기본 모니터에서 전체 화면 슬라이드 쇼로 연다.
3. 아래 명령으로 실행하고 5초 동안 PowerPoint 슬라이드 쇼 창을 선택한다.

```powershell
.\run.ps1 -Mode present
# 또는
.\.venv\Scripts\python.exe -X utf8 main.py --enable-input
```

| 손동작 | 동작 |
| --- | --- |
| 편 손을 5프레임 유지한 뒤 미리보기 기준 오른쪽으로 빠르게 이동 | 다음 장, 방향키 Right |
| 같은 준비 후 왼쪽으로 이동 | 이전 장, 방향키 Left |
| 검지만 펴고 5프레임 유지 | Ctrl+L로 레이저 포인터 시작 |
| 포인터 모드에서 검지 이동 | 검지 끝을 기본 모니터 좌표로 변환하고 보정하여 이동 |
| 주먹을 5프레임 유지 | Ctrl+A로 포인터 종료, 스와이프 다시 준비 |
| 손 미검출 또는 두 손 검출 | 입력 정지, 추적 초기화, 포인터 종료 |

슬라이드 입력 뒤에는 **1초 쿨다운과 주먹 자세 복귀가 모두 필요**하다. 손을 계속 편 채 왕복해도 다시 넘기지 않는다. PowerPoint 슬라이드 쇼가 활성 창일 때만 입력한다. 미리보기를 클릭하면 입력이 멈추므로 PPT 창을 다시 선택하고 손 모양을 새로 유지한다. 활성 창 판별은 Windows의 `POWERPNT.EXE`와 슬라이드 쇼 창 클래스 `screenClass`를 기준으로 하며, 팀원 PC에서 확인해야 한다. 브라우저 PowerPoint와 다른 발표 앱은 지원 대상이 아니다.

마우스를 직접 화면 모서리로 옮기면 PyAutoGUI 비상 중단이 작동한다. 자동 포인터 이동은 모서리를 피한다. 종료할 때 PPT 창이 활성 상태라면 포인터를 화살표로 돌린다. 다른 창이 활성 상태라면 그 창에 단축키를 보내지 않으므로 필요 시 PPT에서 직접 `Ctrl+A`를 누른다.

## 규칙과 조정

- 손가락: 관절 각도와 손목에서 손끝까지의 상대 거리로 판단한다. 엄지는 별도 각도와 검지 뿌리로부터 벌어진 거리를 쓴다. 각도는 world 좌표를 우선 사용하므로 단순히 손끝의 y좌표만 비교하지 않는다.
- 스와이프: 안정된 편 손의 손바닥 중심이 0.5초 이내에 영상 너비의 20% 이상 이동해야 한다. 수평 이동은 그 구간의 세로 흔들림 범위보다 2배 이상 커야 한다.
- 포인터: 영상 가장자리 10%를 제외한 영역을 화면 전체에 대응시킨다. 이전 위치 70%와 현재 위치 30%를 섞으며, 재검출 시 과거 좌표를 버린다.
- 추적: 손이 사라지거나 좌우 손이 바뀌거나 프레임 사이가 0.5초보다 벌어지면 유지 프레임과 좌표 이력을 초기화한다. 슬라이드 쿨다운과 주먹 복귀 조건은 유지한다.

초기 수치는 실제 촬영으로 검증되지 않았다. 한 번에 하나씩 바꾸고 FPS와 실패 조건을 기록한다.

```powershell
.\.venv\Scripts\python.exe main.py --hold-frames 7 --cooldown 1.2 --swipe-distance 0.25 --smoothing 0.2
```

이 명령도 기본값은 실제 입력 없는 카메라 미리보기다. 실제 입력을 사용하려면 `--enable-input`을 추가한다.

## 자동 테스트와 좌표 재생

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 main.py --replay 'data\team_test.jsonl'
```

테스트는 합성 좌표로 0~5개 손가락 조합, 회전·반전, 스와이프 방향, 쿨다운과 반복 차단, 포인터 전환, 손 미검출, 스무딩 등을 확인한다. 합성 좌표 통과는 실제 손 인식률을 뜻하지 않는다.

재생 파일은 UTF-8 JSONL이며 한 줄이 한 프레임이다. 프로그램이 이 파일을 자동 수집하지는 않는다. 팀원이 별도로 좌표를 제공할 경우 아래 형식으로 준비한다. `time`은 초 단위의 엄격히 증가하는 시간, `landmarks`는 **반전 미리보기 기준**의 `[x,y,z]` 21개다. `world`는 선택 사항인 미터 단위 좌표 21개, `aspect_ratio`는 영상 가로/세로 비율, `hand`는 `Left` 또는 `Right`다. 미검출은 `{"time": 1.0, "landmarks": null}`로 기록한다. 두 손이 보인 프레임도 제어 중지를 재현하려면 미검출로 기록한다. 재생과 `--enable-input`은 함께 사용할 수 없다.

## 문제 해결

| 문제 | 확인 방법 |
| --- | --- |
| Python 또는 py를 찾지 못함 | Python 3.12 64비트 설치 또는 설치 스크립트에 실행 파일 경로 지정 |
| 카메라 열기 실패 | 카메라 연결, Windows 설정의 데스크톱 앱 카메라 접근, 다른 앱 점유, `--camera 1` 확인 |
| 모델 없음 | `main.py --download-model` 실행. 프록시·방화벽은 공식 Google Storage 접근 확인 |
| imshow 오류 또는 OpenCV 중복 | 가상환경에서 OpenCV 네 종류를 제거한 뒤 lock 파일로 재설치 |
| PPT를 넘기지 못함 | 실제 입력 모드인지, 전체 화면 슬라이드 쇼가 기본 모니터에서 활성 상태인지, 주먹 복귀와 쿨다운을 마쳤는지 확인 |
| 손가락 수가 잘못 나옴 | 손 전체가 보이게 하고 조명·거리·손 각도와 FPS 기록. 가려진 손가락의 정확도는 보장되지 않음 |

```powershell
.\.venv\Scripts\python.exe -m pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python opencv-contrib-python-headless
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
```

## 코드와 개발 기록

| 파일 | 역할 |
| --- | --- |
| `main.py` | 명령행 옵션과 실행 모드 선택 |
| `presenter/core.py` | 관절 각도, 손 모양, 제스처 상태와 시간 처리 |
| `presenter/camera.py` | 카메라, MediaPipe 추론, 반전 미리보기 |
| `presenter/output.py` | 모의 출력, 활성 PPT 창 검사와 실제 입력 |
| `presenter/model.py` | 공식 모델 다운로드와 검사 |
| `presenter/demo.py`, `presenter/replay.py` | 모의 동작과 제공된 좌표 재생 |

[개발 기록](docs/dev_log.md)과 [현재 구현 계획](docs/implementation_plan.md)에 검증 결과와 남은 작업을 구분해 두었다. 공개 공유 시 제안서의 실명·학번, 수업 안내, 촬영 영상과 개인 데이터, 가상환경, 임시 문서는 제외한다. 모델은 설치 시 공식 서버에서 받는다.

## 참고 자료

- [MediaPipe Hand Landmarker 공식 문서](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker?tab=Python): Tasks API와 영상 추론
- [OpenCV 패키지 공식 안내](https://pypi.org/project/opencv-python/): GUI 배포판 하나만 설치하는 원칙
- [PyAutoGUI 공식 문서](https://pyautogui.readthedocs.io/en/latest/): 키보드·마우스 제어와 비상 중단
- [Microsoft PowerPoint 단축키](https://support.microsoft.com/en-us/accessibility/powerpoint/use-keyboard-shortcuts-to-deliver-powerpoint-presentations): Ctrl+L, Ctrl+A, 슬라이드 이동
