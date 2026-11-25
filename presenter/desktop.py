"""데스크톱 손동작 판별. 이벤트만 만들고 OS에는 입력하지 않는다."""

from collections import deque
from dataclasses import dataclass
import math

from .core import Event, HandPose, Point, Shape, distance, horizontal_swipe, screen_position


@dataclass(frozen=True)
class DesktopConfig:
    # 길이는 정규화 영상 좌표, 핀치 간격은 손바닥 길이의 비율, 시간은 초.
    pinch_close: float = 0.24
    pinch_open: float = 0.36
    index_reach: float = 0.15  # 손목→검지 뿌리 방향으로 이만큼 더 뻗으면 주먹과 구분
    pinch_min_time: float = 0.04
    click_max_time: float = 0.28
    drag_distance: float = 0.04
    scroll_step: float = 0.035
    swipe_distance: float = 0.19
    swipe_window: float = 0.5
    swipe_horizontal_ratio: float = 2.0
    switch_cooldown: float = 0.8
    cursor_margin: float = 0.1
    cursor_smoothing: float = 0.5  # 현재 좌표의 비중
    max_frame_gap: float = 0.4
    feedback_time: float = 0.5


@dataclass(frozen=True)
class DesktopHand:
    name: str
    pose: HandPose
    pinch_gap: float
    pinch_position: tuple[float, float]
    index_extension: float


def measure_desktop_hand(points, pose, aspect_ratio, name):
    """엄지·검지 끝 사이 거리와 검지가 손바닥보다 앞으로 나온 정도를 구한다."""
    selected = (points[i] for i in (0, 4, 5, 8, 9))
    wrist, thumb, index_base, index, middle_base = (
        Point(p.x * aspect_ratio, p.y, p.z * aspect_ratio) for p in selected)
    palm_size = distance(wrist, middle_base)
    palm_axis = (index_base.x - wrist.x, index_base.y - wrist.y, index_base.z - wrist.z)
    index_axis = (index.x - index_base.x, index.y - index_base.y, index.z - index_base.z)
    axis_length_sq = sum(component**2 for component in palm_axis)
    extension = (sum(a*b for a, b in zip(palm_axis, index_axis)) / axis_length_sq
                 if axis_length_sq > 1e-10 else 0.0)
    gap = distance(thumb, index) / palm_size if palm_size > 1e-5 else math.inf
    center = ((points[4].x + points[8].x)/2, (points[4].y + points[8].y)/2)
    return DesktopHand(name, pose, gap, center, extension)


class DesktopController:
    def __init__(self, config=None):
        self.config = config or DesktopConfig()
        self.last_time = None
        self.last_switch = -math.inf
        self.hand = None
        self.paused = False
        self.gesture = "NO HAND"
        self.action = "IDLE"
        self.cursor = None
        self.scroll_anchor = None
        self.swipe_history = deque()
        self.swipe_used = False
        self.pinch_ready = False  # 처음 잡히거나 끊긴 손은 손가락을 뗀 뒤 시작한다.
        self.pinch_since = None
        self.pinch_origin = None
        self.press_position = None
        self.pinch_travel = 0.0
        self.dragging = False
        self.feedback = "IDLE"
        self.feedback_until = -math.inf

    def reset_tracking(self):
        """손을 잃거나 입력을 정지하면 클릭을 취소하고 유지 중인 드래그를 놓는다."""
        events = self._finish_pinch()
        self.hand = None
        self.cursor = None
        self.scroll_anchor = None
        self.swipe_history.clear()
        self.swipe_used = False
        self.pinch_ready = False
        self.feedback_until = -math.inf
        self.gesture = "NO HAND"
        self.action = "PAUSED" if self.paused else "IDLE"
        return events

    def update(self, now, hand: DesktopHand | None):
        if not math.isfinite(now) or (self.last_time is not None and now <= self.last_time):
            raise ValueError("입력 시간은 유한하고 이전 시간보다 커야 합니다.")
        events = []
        if self.last_time is not None and now - self.last_time > self.config.max_frame_gap:
            events.extend(self.reset_tracking())
        self.last_time = now

        if hand is None:
            return events + self.reset_tracking()
        if self.hand is not None and self.hand != hand.name:
            events.extend(self.reset_tracking())
        self.hand = hand.name

        # 1. 일시정지는 진행 중인 드래그나 클릭 후보보다 먼저 처리한다.
        index_reaches = hand.index_extension >= self.config.index_reach
        if hand.pose.shape == Shape.FIST and not index_reaches:
            first_fist = not self.paused
            self.paused = True
            events.extend(self.reset_tracking())
            self.gesture = "FIST"
            return events + ([Event("pause")] if first_fist else [])
        if self.paused:
            self.paused = False
            events.append(Event("resume"))

        c = self.config
        was_pinching = self.pinch_since is not None
        close_enough = hand.pinch_gap < c.pinch_open if was_pinching else hand.pinch_gap <= c.pinch_close
        pinched = close_enough and (index_reaches or hand.pose.fingers[1])
        if hand.pinch_gap >= c.pinch_open:
            self.pinch_ready = True

        # 2–3. 같은 핀치는 클릭 또는 드래그 둘 중 하나로 끝난다.
        if (pinched and self.pinch_ready) or was_pinching:
            self.gesture = "PINCH" if pinched else hand.pose.shape.value
            self.scroll_anchor = None
            self.swipe_history.clear()
            self.swipe_used = False
            return events + self._update_pinch(now, hand, pinched)
        if pinched:
            # 손이 돌아왔을 때 이미 붙어 있으면 떼기 전까지 모든 하위 동작을 차단한다.
            self.gesture, self.action = "PINCH", "RELEASE TO START"
            return events

        pose = hand.pose
        fingers = pose.fingers
        two_fingers = fingers == (False, True, True, False, False)
        self.gesture = "TWO FINGERS" if two_fingers else (
            "OTHER" if pose.shape == Shape.FIST else pose.shape.value)
        if not two_fingers:
            self.scroll_anchor = None
        if pose.shape != Shape.OPEN:
            self.swipe_history.clear()
            self.swipe_used = False

        # 4. 두 손가락 스크롤, 5. 편 손 스와이프, 6. 검지 커서 이동.
        if two_fingers:
            self.cursor = None
            return events + self._scroll(now, pose.palm[1])
        if pose.shape == Shape.OPEN:
            self.cursor = None
            return events + self._switch(now, pose.palm)
        if pose.shape == Shape.POINT:
            target = screen_position(pose.tip, c.cursor_margin)
            if self.cursor is None:
                self.cursor = target
            else:
                alpha = c.cursor_smoothing
                self.cursor = tuple(old + alpha*(new-old) for old, new in zip(self.cursor, target))
            self.action = self.feedback if now < self.feedback_until else "MOVE CURSOR"
            return events + [Event("cursor_move", self.cursor)]

        self.cursor = None
        self.action = self.feedback if now < self.feedback_until else "IDLE"
        return events

    def _update_pinch(self, now, hand, pinched):
        c = self.config
        target = screen_position(hand.pinch_position, c.cursor_margin)
        if not pinched:
            click = (not self.dragging and c.pinch_min_time <= now - self.pinch_since <= c.click_max_time
                     and self.pinch_travel < c.drag_distance and hand.pinch_gap >= c.pinch_open)
            position = self.press_position
            events = self._finish_pinch()
            if click:
                self.feedback = self.action = "LEFT CLICK"
                self.feedback_until = now + c.feedback_time
                return [Event("click", position)]
            self.action = "DROP" if events else "IDLE"
            return events

        if self.pinch_since is None:
            self.pinch_since = now
            self.pinch_origin = hand.pinch_position
            self.press_position = self.cursor if self.cursor is not None else target
        travel = math.dist(self.pinch_origin, hand.pinch_position)
        self.pinch_travel = max(self.pinch_travel, travel)
        if self.dragging:
            self.action = "DRAG"
            self.cursor = target
            return [Event("drag_move", target)]
        if now - self.pinch_since >= c.pinch_min_time and travel >= c.drag_distance:
            self.action = "DRAG"
            self.dragging = True
            self.cursor = target
            return [Event("drag_start", self.press_position), Event("drag_move", target)]
        self.action = "PINCH HELD"
        return []

    def _finish_pinch(self):
        events = [Event("drag_end")] if self.dragging else []
        self.pinch_since = None
        self.pinch_origin = None
        self.press_position = None
        self.pinch_travel = 0.0
        self.dragging = False
        return events

    def _scroll(self, now, y):
        step = self.config.scroll_step
        if self.scroll_anchor is None:
            self.scroll_anchor = y
            self.feedback_until = -math.inf
        steps = math.trunc((self.scroll_anchor - y) / step)
        if not steps:
            self.action = self.feedback if now < self.feedback_until else "SCROLL READY"
            return []
        self.scroll_anchor -= steps * step
        self.feedback = self.action = "SCROLL UP" if steps > 0 else "SCROLL DOWN"
        self.feedback_until = now + self.config.feedback_time
        return [Event("scroll", steps=steps)]

    def _switch(self, now, palm):
        c = self.config
        if self.swipe_used or now - self.last_switch < c.switch_cooldown:
            self.action = self.feedback if now < self.feedback_until else "SWIPE READY"
            return []
        direction = horizontal_swipe(self.swipe_history, now, palm, c.swipe_window,
                                     c.swipe_distance, c.swipe_horizontal_ratio)
        if not direction:
            self.action = "SWIPE READY"
            return []
        self.last_switch = now
        self.swipe_used = True
        self.swipe_history.clear()
        self.feedback = self.action = "NEXT WINDOW" if direction > 0 else "PREVIOUS WINDOW"
        self.feedback_until = now + c.feedback_time
        return [Event("switch_next" if direction > 0 else "switch_previous")]
