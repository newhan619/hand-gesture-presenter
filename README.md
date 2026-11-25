# 손 제스처 발표 컨트롤러

웹캠으로 한 손을 인식해 PowerPoint 슬라이드 쇼를 넘기고 검지로 레이저 포인터를 움직이는 Python 프로그램이다. 최종 제안서의 핵심 기능 세 가지를 구현한 초기 버전이다. 웹캠 영상과 랜드마크를 자동 저장하지 않는다.

**현재 검증 범위:** Windows에서 모델 추론과 자동 테스트를 확인했다. 팀원은 Apple Silicon Mac의 실제 웹캠으로 손 모양, 스와이프, 포인터 모드 전환을 미리보기에서 시험했다. Windows에서 실제 PowerPoint 조작은 검증이 남아 있다. 자세한 시험 결과는 [개발 기록](docs/dev_log.md)에 있다.

## 팀원이 처음 테스트하는 방법

**ZIP으로 내려받아 실행하면 된다. Git 프로그램을 설치하거나 켤 필요는 없다.** 테스트만 할 때는 GitHub 초대도 필요 없다.

준비물은 Windows 11 PC, **Python 3.12 64비트**, 웹캠이다. PPT 조작까지 시험하려면 데스크톱 PowerPoint도 필요하다.

1. Python이 없다면 [Python 공식 다운로드](https://www.python.org/downloads/windows/)에서 **3.12 버전의 64비트 Python**을 설치한다.
2. [프로그램 ZIP 다운로드](https://github.com/newhan619/hand-gesture-presenter/archive/refs/heads/main.zip)를 누르고 **압축을 푼다**. GitHub에서는 초록색 **Code → Download ZIP**으로도 받을 수 있다.
3. 압축을 푼 폴더 안에서 **`main.py`와 `setup.ps1`이 보이는 폴더**로 들어간다.
4. 폴더의 빈 공간을 우클릭하고 **터미널에서 열기**를 누른다. PowerShell 창에서 아래 명령을 한 줄씩 실행한다.

먼저 필요한 프로그램과 손 인식 모델을 설치한다. **이 폴더에서 처음 한 번만 실행**하며 인터넷 연결이 필요하다. `Setup complete`가 나오면 설치가 끝난 것이다.

```powershell
.\setup.ps1
```

이어서 웹캠 테스트를 실행한다.

```powershell
.\run.ps1 -Mode preview
```

카메라 화면에 손을 보여주면 관절의 점과 선, 손가락 수가 나타난다. 이 단계에서는 키보드나 마우스를 움직이지 않는다. 다른 카메라를 선택하려면 다음 명령을 사용한다.

```powershell
.\run.ps1 -Mode preview -Camera 1
```

창을 선택한 상태에서 **Q**를 누르거나 창을 닫으면 종료한다. 터미널에서 **Ctrl+C**로도 종료할 수 있다. 실행이 안 되면 아래의 **설치 문제 해결과 코드 설명**을 펼쳐 직접 실행 방법을 확인한다.

세부 시험 항목은 [팀원 테스트 체크리스트](docs/camera_test_checklist.md)에 있다.

## macOS에서 실행하기

웹캠 확인은 **Apple Silicon Mac**에서 진행했다. **Python 3.12**(예: `brew install python@3.12`)를 설치하고 ZIP을 푼 뒤, 터미널에서 `main.py`가 있는 폴더로 이동한다. 설치 스크립트가 macOS용 의존성을 준비한다.

```bash
bash setup.sh         # 처음 한 번: 가상환경, 패키지, 모델 설치
bash run.sh demo      # 카메라 없이 모의 실행
bash run.sh preview   # 웹캠 미리보기
```

iPhone 연속성 카메라가 먼저 잡히면 `bash run.sh preview 1`로 다른 카메라를 선택한다. 미리보기 창에서 **Esc**, 또는 터미널에서 **Ctrl+C**를 누르면 종료된다. **Q**로 종료하거나 **P**로 일시정지할 때는 영문 입력 상태를 사용한다. 카메라 접근이 차단되어 있다면 **시스템 설정 → 개인정보 보호 및 보안 → 카메라**에서 터미널 앱을 허용한다. 실제 PPT 조작(`--enable-input`)은 Windows에서 시험한다.

## PowerPoint까지 조작해 보기

1. 위의 웹캠 테스트에서 손이 잘 인식되는지 확인한다.
2. PowerPoint를 열고 **기본 모니터에서 전체 화면 슬라이드 쇼**를 시작한다.
3. 터미널에서 아래 명령을 실행하고 **5초 안에 PPT 슬라이드 쇼 창을 클릭**한다.

```powershell
.\run.ps1 -Mode present
```

| 손동작 | 동작 |
| --- | --- |
| 편 손을 5프레임 유지한 뒤 미리보기 기준 오른쪽으로 빠르게 이동 | 다음 장, 방향키 Right |
| 같은 준비 후 왼쪽으로 이동 | 이전 장, 방향키 Left |
| 검지만 펴고 필요한 프레임 수만큼 유지 (기본 5) | Ctrl+L로 레이저 포인터 시작 |
| 포인터 모드에서 검지 이동 | 검지 끝을 기본 모니터 좌표로 변환하고 보정하여 이동 |
| 주먹을 0.25초 이상 연속으로 유지 | Ctrl+A로 포인터 종료, 스와이프 다시 준비 |
| 손 미검출 또는 두 손 검출 | 포인터 이동은 즉시 정지. 0.4초 안에 같은 손의 검지를 다시 잡으면 재개하고, 이 시간이 지나면 포인터 종료 |

슬라이드를 한 번 넘겼다면 **주먹을 쥐고, 마지막 입력에서 1초 이상 지난 뒤** 다시 스와이프한다. 미리보기를 클릭하면 PPT 조작이 멈추므로 PPT 창을 다시 선택한다. 데스크톱 PowerPoint의 전체 화면 슬라이드 쇼에서 사용한다.

마우스를 직접 화면 모서리로 옮기면 PyAutoGUI 비상 중단이 작동한다. 자동 포인터 이동은 모서리를 피한다. 종료할 때 PPT 창이 활성 상태라면 포인터를 화살표로 돌린다. 다른 창이 활성 상태라면 그 창에 단축키를 보내지 않으므로 필요 시 PPT에서 직접 `Ctrl+A`를 누른다.

## 데스크톱 모드

Windows에서 기본 모니터의 커서와 현재 사용 중인 앱을 제어한다. 먼저 모의 실행으로 동작을 확인한다.

```powershell
py -3.12 main.py --desktop --demo  # 합성 손 좌표, 웹캠·실제 입력 없이 실행
.\run.ps1 -Mode desktop-preview  # 실제 웹캠으로 인식만 확인
.\run.ps1 -Mode desktop          # Windows 마우스·키보드 실제 입력
```

Python 가상환경을 설치했다면 `.\run.ps1 -Mode desktop-demo`로도 모의 실행할 수 있다. `main.py --desktop`은 웹캠 미리보기이며, 실제 입력을 사용하려면 `--enable-input`을 추가한다.

| 손동작 | 데스크톱 동작 |
| --- | --- |
| 주먹을 쥔 채 유지 | 입력 일시정지. 주먹을 풀면 재개 |
| 엄지와 검지를 붙였다 짧게 떼기 | 왼쪽 클릭. 먼저 손가락을 뗀 상태를 보여 준 뒤 붙인다 |
| 엄지와 검지를 붙인 채 이동 | 드래그. 손가락을 떼면 버튼을 놓는다 |
| 검지와 중지만 펴고 위아래로 이동 | 위아래로 스크롤 |
| 편 손을 좌우로 빠르게 이동 | 오른쪽은 `Alt+Tab`, 왼쪽은 `Alt+Shift+Tab`으로 창 전환 |
| 검지만 펴서 이동 | 마우스 커서 이동 |

표의 위쪽 동작을 먼저 판단한다. 손이 사라지거나 두 손이 들어오면 입력을 멈추고 진행 중인 드래그 버튼도 놓는다. OpenCV 미리보기에는 `Mode`, `Shape`, `Action`을 표시한다. 미리보기 창에서 `P`를 눌러 직접 일시정지할 수 있다. 마우스를 화면 모서리로 옮기는 PyAutoGUI 비상 중단도 사용할 수 있다.

데스크톱의 시간·거리 기준은 [DesktopConfig](presenter/desktop.py)에 모아 두었다. 기본값은 클릭 유지 0.04~0.28초, 드래그 이동 영상 크기의 4%, 스크롤 한 칸 영상 높이의 3.5%다. 실제 웹캠을 쓰는 팀원은 [테스트 체크리스트](docs/camera_test_checklist.md)에서 반응을 확인한다.

## 저장소 소유자가 팀원을 초대하는 방법

팀원이 코드를 수정해서 같은 저장소에 올리려면 소유자가 한 번만 초대하면 된다.

1. 팀원의 **GitHub 아이디**를 받는다.
2. [저장소](https://github.com/newhan619/hand-gesture-presenter)에서 **Settings → Collaborators → Add people**을 누른다.
3. 팀원 아이디를 검색해서 초대한다.
4. 팀원이 초대를 수락하면 수정 내용을 저장소에 올릴 수 있다.

[GitHub 공식 초대 안내](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository)

## 팀원이 수정한 코드를 올리는 방법

초대를 수락한 팀원은 **GitHub 웹사이트에서 파일을 편집하고 저장**하면 된다. 작은 수정은 아래 순서로 진행한다.

1. GitHub에 로그인하고 이 저장소에서 수정할 `.py` 파일을 클릭한다. 폴더 안의 파일이면 해당 폴더를 먼저 연다.
2. 파일 위쪽의 **연필 버튼**을 누른다.
3. 코드를 수정한다. PC에서 이미 수정했다면 **같은 경로의 파일**을 열어 수정한 내용을 복사하고 웹 편집기에 붙여넣어도 된다.
4. **Commit changes…**를 누르고 `카메라 인식 수정`처럼 무엇을 바꿨는지 짧게 적는다.
5. 현재 `main` 브랜치에 저장하는 항목을 선택하고 **Commit changes**를 눌러 저장한다. 파일을 여러 개 수정했다면 각 파일에서 이 과정을 반복한다.

이렇게 저장하면 별도의 push 명령 없이 GitHub에 반영된다. 저장소의 **Actions** 탭에서 자동 테스트 결과를 볼 수 있다. 실제 웹캠과 PPT 동작도 팀원 PC에서 별도로 확인한다.

**GitHub에 저장한 수정 내용은 PC의 ZIP 폴더에 자동 반영되지 않는다.** 다음 테스트 때 최신 ZIP을 다시 받아 압축을 풀고 위 설치·실행 순서를 따르면 된다. PC에서 수정하던 내용은 GitHub에 올린 뒤 최신 ZIP을 받는다.

테스트 중 문제가 생기면 [Issues](https://github.com/newhan619/hand-gesture-presenter/issues)에 실행 명령, 오류 메시지, 어떤 손동작에서 문제가 생겼는지를 적는다.

[GitHub 공식 웹 편집 안내](https://docs.github.com/en/repositories/working-with-files/managing-files/editing-files)

<details>
<summary>설치 문제 해결과 코드 설명 자세히 보기</summary>

## 스크립트가 실행되지 않을 때

PowerShell에서 스크립트 실행이 차단되면 `main.py`가 있는 폴더에서 아래 명령을 한 줄씩 실행한다. 가상환경 활성화는 필요 없다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 main.py --download-model
.\.venv\Scripts\python.exe -X utf8 main.py --check-model
```

설치 후 웹캠 테스트와 PPT 조작은 각각 다음 명령으로 실행한다.

```powershell
.\.venv\Scripts\python.exe -X utf8 main.py
.\.venv\Scripts\python.exe -X utf8 main.py --enable-input
```

Python 경로를 직접 지정하려면 `setup.ps1 -PythonPath 'C:\경로\python.exe'`를 사용한다. `requirements.txt`는 직접 사용하는 패키지, `requirements.lock.txt`는 설치·검사한 전체 버전이다. MediaPipe의 의존성인 GUI OpenCV는 `opencv-contrib-python` 하나만 사용한다.

## 카메라 없이 확인하기

Python만 설치되어 있다면 다음 명령으로 모의 실행할 수 있다.

```powershell
py -3.12 main.py --demo
```

설치가 끝난 폴더에서는 다음 명령으로 실행해도 된다.

```powershell
.\run.ps1 -Mode demo
```

예상 출력은 `next → previous → pointer_on → pointer_off → PASS`다. 카메라를 열거나 키보드·마우스를 제어하지 않는다.

## 카메라 화면의 표시

| 표시 | 뜻 |
| --- | --- |
| FIST | 주먹 |
| OPEN | 손가락 다섯 개를 편 손 |
| POINT | 검지만 편 손 |
| OTHER | 그 밖의 손 모양 |
| NO HAND | 손 미검출, 제어 정지 |
| TWO HANDS | 두 손 검출, 제어 정지 |
| armed | 스와이프를 다시 받을 수 있는 상태 |

화면 글자는 OpenCV 기본 폰트가 지원하는 영문을 사용했다. `P`는 미리보기 창에서 일시정지/재개다.

실제 PPT 입력은 Windows의 `POWERPNT.EXE`와 슬라이드 쇼 창 클래스 `screenClass`로 활성 창을 확인한다. 이 판별은 팀원 PC에서 검증해야 한다. 브라우저 PowerPoint와 다른 발표 앱은 지원 대상이 아니다.

## 규칙과 조정

- 손가락: 관절 각도와 손목에서 손끝까지의 상대 거리로 판단한다. 엄지는 별도 각도와 검지 뿌리로부터 벌어진 거리를 쓴다. 웹캠에서는 화면 비율을 보정한 영상 기준 좌표를 사용한다. 팀원 시험에서는 MediaPipe의 미터 단위 world 좌표가 편 손가락도 굽은 것으로 추정하는 사례가 있었다.
- 스와이프: 안정된 편 손의 손바닥 중심이 0.5초 이내에 영상 너비의 20% 이상 이동해야 한다. 수평 이동은 그 구간의 세로 흔들림 범위보다 2배 이상 커야 한다.
- 포인터: 영상 가장자리 10%를 제외한 영역을 화면 전체에 대응시킨다. 기본값은 이전 위치 70%와 현재 위치 30%를 섞는다. `--smoothing 1.0`은 현재 위치를 바로 사용한다. `--hold-frames`는 켜는 데 필요한 프레임 수이고, 주먹으로 끄는 기준은 별도로 0.25초다.
- 추적: 잠깐 손이 사라지면 포인터 이동을 멈추고 이전 좌표를 비운다. 좌우 손이 바뀌거나 새 프레임이 0.5초 넘게 들어오지 않으면 기존 포인터를 종료하고 추적을 다시 시작한다. 슬라이드 쿨다운과 주먹 복귀 조건은 유지한다.

팀원이 시연에 사용한 민감도 설정으로 PowerPoint를 조작하려면 다음 명령을 사용한다. 환경에 맞춰 조정할 때는 한 번에 한 값씩 바꾸고 FPS와 인식 결과를 확인한다.

```powershell
.\.venv\Scripts\python.exe -X utf8 main.py --hold-frames 2 --cooldown 1.2 --swipe-distance 0.12 --smoothing 1.0 --enable-input
```

같은 설정으로 미리보기만 사용하려면 `--enable-input`을 뺀다.

## 자동 테스트와 좌표 재생

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 main.py --replay 'data\team_test.jsonl'
.\.venv\Scripts\python.exe -X utf8 main.py --desktop --replay 'data\team_test.jsonl'
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

</details>
