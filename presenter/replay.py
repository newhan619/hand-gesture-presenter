"""팀원이 별도 제공한 랜드마크 JSONL 재생. 재생에서는 실제 입력을 보내지 않는다."""

import json
from pathlib import Path

from .core import GestureController, Observation, Point, classify_hand
from .desktop import DesktopController, measure_desktop_hand


def run_replay(path, config, *, desktop=False):
    controller = DesktopController() if desktop else GestureController(config)
    frames = actions = 0
    with Path(path).open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                timestamp = float(record["time"])
                landmarks = record.get("landmarks")
                hand_name = record.get("hand", "unknown")
                pose = None
                if landmarks is not None:
                    points = [Point(*xyz) for xyz in landmarks]
                    world = None if desktop else record.get("world")
                    aspect_ratio = float(record.get("aspect_ratio", 1.0))
                    pose = classify_hand(points,
                        world=None if world is None else [Point(*xyz) for xyz in world],
                        aspect_ratio=aspect_ratio)
                if desktop:
                    hand = None if pose is None else measure_desktop_hand(points, pose, aspect_ratio, hand_name)
                    events = controller.update(timestamp, hand)
                else:
                    observation = Observation(timestamp, None) if pose is None else Observation(
                        timestamp, pose.shape, pose.palm, pose.tip, hand_name)
                    events = controller.update(observation)
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError(f"재생 파일 {line_number}행 오류: {exc}") from exc
            frames += 1
            for event in events:
                if event.kind not in ("move", "cursor_move", "drag_move"):
                    actions += 1
                    detail = f" {event.steps:+d}" if event.kind == "scroll" else ""
                    print(f"{timestamp:.3f}s  {event.kind}{detail}")
    print(f"재생 완료: {frames}프레임, 동작 이벤트 {actions}회, 실제 입력 0회")
