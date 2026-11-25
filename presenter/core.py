"""관절 판별과 시간 기반 제스처 처리. 외부 장치에는 접근하지 않는다."""

from collections import deque
from dataclasses import dataclass
from enum import Enum
import math


class Shape(str, Enum):
    FIST = "FIST"
    OPEN = "OPEN"
    POINT = "POINT"
    OTHER = "OTHER"


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True)
class HandPose:
    fingers: tuple[bool, bool, bool, bool, bool]  # 엄지부터 소지까지
    shape: Shape
    palm: tuple[float, float]
    tip: tuple[float, float]

    @property
    def count(self):
        return sum(self.fingers)


def distance(a: Point, b: Point) -> float:
    return math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))


def angle(a: Point, b: Point, c: Point) -> float:
    """관절 b의 각도. 겹친 점은 펴진 손가락으로 인정하지 않는다."""
    u = (a.x - b.x, a.y - b.y, a.z - b.z)
    v = (c.x - b.x, c.y - b.y, c.z - b.z)
    denominator = math.sqrt(sum(x*x for x in u) * sum(x*x for x in v))
    if denominator < 1e-12:
        return 0.0
    cosine = sum(x*y for x, y in zip(u, v)) / denominator
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def classify_hand(landmarks, *, world=None, aspect_ratio=1.0) -> HandPose:
    """21개 점으로 손 모양을 판별한다. 좌우/화면 회전과 무관한 각도를 쓴다.

    가능하면 MediaPipe의 미터 단위 world 좌표로 관절 각도를 계산한다.
    world가 없으면 영상 가로/세로 비율을 보정한 좌표를 사용한다.
    이동과 포인터에는 반전 미리보기의 정규화 영상 좌표를 사용한다.
    """
    if len(landmarks) != 21 or (world is not None and len(world) != 21):
        raise ValueError("손 하나에는 21개 랜드마크가 필요합니다.")
    if not math.isfinite(aspect_ratio) or aspect_ratio <= 0:
        raise ValueError("영상 비율은 양수여야 합니다.")
    for p in list(landmarks) + ([] if world is None else list(world)):
        if not all(math.isfinite(v) for v in (p.x, p.y, p.z)):
            raise ValueError("좌표에 유한한 숫자가 필요합니다.")
    points = world if world is not None else [
        Point(p.x * aspect_ratio, p.y, p.z * aspect_ratio) for p in landmarks
    ]
    # 엄지는 MCP와 IP 각도에 더해 검지 뿌리로부터 벌어진 거리를 확인한다.
    thumb = (angle(points[1], points[2], points[3]) >= 150
             and angle(points[2], points[3], points[4]) >= 150
             and distance(points[4], points[5]) > distance(points[3], points[5]) * 1.1)
    fingers = [thumb]
    for mcp in (5, 9, 13, 17):
        pip, dip, tip = mcp + 1, mcp + 2, mcp + 3
        fingers.append(
            angle(points[mcp], points[pip], points[dip]) >= 155
            and angle(points[pip], points[dip], points[tip]) >= 150
            and distance(points[tip], points[0]) > distance(points[pip], points[0]) * 1.1
        )
    bits = tuple(fingers)
    shape = (Shape.FIST if not any(bits) else
             Shape.OPEN if all(bits) else
             Shape.POINT if bits == (False, True, False, False, False) else Shape.OTHER)
    palm_indices = (0, 5, 9, 13, 17)
    palm = tuple(sum(getattr(landmarks[i], axis) for i in palm_indices) / 5
                 for axis in ("x", "y"))
    return HandPose(bits, shape, palm, (landmarks[8].x, landmarks[8].y))


@dataclass(frozen=True)
class Config:
    hold_frames: int = 5
    swipe_window: float = 0.5
    swipe_distance: float = 0.2
    horizontal_ratio: float = 2.0
    cooldown: float = 1.0
    smoothing: float = 0.3  # 현재 좌표의 비중
    max_gap: float = 0.5
    pointer_margin: float = 0.1
    pointer_fist_hold: float = 0.25  # 주먹으로 포인터를 끄기까지 걸리는 시간
    pointer_loss_grace: float = 0.4  # 검출이 끊겨도 포인터 모드를 유지하는 시간

    def __post_init__(self):
        if not isinstance(self.hold_frames, int) or self.hold_frames < 1:
            raise ValueError("hold_frames는 1 이상의 정수여야 합니다.")
        values = (self.swipe_window, self.swipe_distance, self.horizontal_ratio,
                  self.cooldown, self.smoothing, self.max_gap, self.pointer_margin,
                  self.pointer_fist_hold, self.pointer_loss_grace)
        if not all(math.isfinite(x) for x in values):
            raise ValueError("설정값에는 유한한 숫자가 필요합니다.")
        if (self.swipe_window <= 0 or not 0 < self.swipe_distance <= 1
                or self.horizontal_ratio < 1 or self.cooldown < 0
                or not 0 < self.smoothing <= 1 or self.max_gap <= 0
                or not 0 <= self.pointer_margin < 0.5
                or self.pointer_fist_hold <= 0 or self.pointer_loss_grace <= 0):
            raise ValueError("설정값 범위를 확인하세요.")


@dataclass(frozen=True)
class Observation:
    time: float
    shape: Shape | None
    palm: tuple[float, float] = (0.5, 0.5)
    tip: tuple[float, float] = (0.5, 0.5)
    hand: str = "unknown"


@dataclass(frozen=True)
class Event:
    kind: str
    position: tuple[float, float] | None = None
    steps: int = 0


def screen_position(tip, margin):
    return tuple(max(0.0, min(1.0, (value - margin) / (1 - 2*margin))) for value in tip)


def horizontal_swipe(history, timestamp, palm, window, distance, ratio):
    """동일한 손 모양을 유지한 동안의 손바닥 경로에서 좌우 스와이프를 찾는다."""
    history.append((timestamp, *palm))
    while timestamp - history[0][0] > window:
        history.popleft()
    dx = palm[0] - history[0][1]
    vertical = max(p[2] for p in history) - min(p[2] for p in history)
    if abs(dx) >= distance and abs(dx) >= ratio * vertical:
        return 1 if dx > 0 else -1
    return 0


class GestureController:
    def __init__(self, config=None):
        self.config = config or Config()
        self.mode = "SLIDES"
        self.candidate = None
        self.candidate_since = None
        self.hold_count = 0
        self.armed = True
        self.last_slide = -math.inf
        self.last_time = None
        self.hand = None
        self.history = deque()
        self.smoothed = None
        self.pointer_missing_since = None

    def reset_tracking(self):
        """포인터를 끄고 추적을 초기화한다. 슬라이드 재입력 잠금은 유지한다."""
        events = [Event("pointer_off")] if self.mode == "POINTER" else []
        self.mode = "SLIDES"
        self.candidate = None
        self.candidate_since = None
        self.hold_count = 0
        self.history.clear()
        self.smoothed = None
        self.hand = None
        self.pointer_missing_since = None
        return events

    def update(self, observation: Observation) -> list[Event]:
        o, c = observation, self.config
        if not math.isfinite(o.time):
            raise ValueError("시간은 유한한 숫자여야 합니다.")
        if self.last_time is not None and o.time <= self.last_time:
            raise ValueError("입력 시간은 이전 시간보다 커야 합니다.")
        if o.shape is not None and not isinstance(o.shape, Shape):
            raise ValueError("알 수 없는 손 모양입니다.")
        if not all(math.isfinite(v) for v in (*o.palm, *o.tip)):
            raise ValueError("손 좌표는 유한한 숫자여야 합니다.")
        events = []
        if self.last_time is not None and o.time - self.last_time > c.max_gap:
            events += self.reset_tracking()
        self.last_time = o.time
        if (self.pointer_missing_since is not None
                and o.time - self.pointer_missing_since >= c.pointer_loss_grace):
            events += self.reset_tracking()
        if o.shape is None:
            if self.mode == "POINTER":
                if self.pointer_missing_since is None:
                    self.pointer_missing_since = o.time
                    self.candidate, self.candidate_since, self.hold_count = None, None, 0
                    self.smoothed = None
                return events  # 위치는 즉시 멈추고, 짧은 미검출 동안에는 모드를 유지한다.
            return events + self.reset_tracking()
        if self.hand is not None and self.hand != o.hand:
            events += self.reset_tracking()
        self.hand = o.hand
        self.pointer_missing_since = None
        if self.candidate == o.shape:
            self.hold_count = min(c.hold_frames, self.hold_count + 1)
        else:
            self.candidate, self.hold_count = o.shape, 1
            self.candidate_since = o.time
            self.history.clear()
            self.smoothed = None
        if self.mode == "POINTER":
            # 포인터 모드에서는 어떤 움직임도 슬라이드 이벤트를 만들지 않는다.
            if o.shape == Shape.FIST and o.time - self.candidate_since >= c.pointer_fist_hold:
                events += self.reset_tracking()
                self.armed = True
            elif o.shape == Shape.POINT:
                events.append(self._pointer(o.tip))
            return events

        stable = self.hold_count >= c.hold_frames
        if stable and o.shape == Shape.POINT:
            self.mode = "POINTER"
            self.history.clear()
            events.extend((Event("pointer_on"), self._pointer(o.tip)))
            return events
        if stable and o.shape == Shape.FIST:
            self.armed = True

        if not stable or o.shape != Shape.OPEN or not self.armed:
            self.history.clear()
            return events
        if o.time - self.last_slide < c.cooldown:
            self.history.clear()
            return events
        direction = horizontal_swipe(self.history, o.time, o.palm, c.swipe_window,
                                     c.swipe_distance, c.horizontal_ratio)
        if direction:
            events.append(Event("next" if direction > 0 else "previous"))
            self.last_slide, self.armed = o.time, False
            self.history.clear()
        return events

    def _pointer(self, tip):
        # 영상 가장자리 10%를 제외한 영역을 기본 모니터 전체에 대응시킨다.
        target = screen_position(tip, self.config.pointer_margin)
        if self.smoothed is None:
            self.smoothed = target
        else:
            alpha = self.config.smoothing
            self.smoothed = tuple((1-alpha)*old + alpha*new
                                  for old, new in zip(self.smoothed, target))
        return Event("move", self.smoothed)
