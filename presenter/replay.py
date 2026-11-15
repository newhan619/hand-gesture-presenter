"""팀원이 별도 제공한 랜드마크 JSONL 재생. 재생에서는 실제 입력을 보내지 않는다."""

import json
from pathlib import Path

from .core import GestureController, Observation, Point, classify_hand


def run_replay(path, config):
    controller = GestureController(config)
    frames = actions = 0
    with Path(path).open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                timestamp = float(record["time"])
                landmarks = record.get("landmarks")
                if landmarks is None:
                    observation = Observation(timestamp, None)
                else:
                    points = [Point(*xyz) for xyz in landmarks]
                    world = record.get("world")
                    pose = classify_hand(points,
                        world=None if world is None else [Point(*xyz) for xyz in world],
                        aspect_ratio=float(record.get("aspect_ratio", 1.0)))
                    observation = Observation(timestamp, pose.shape, pose.palm, pose.tip,
                                              record.get("hand", "unknown"))
                events = controller.update(observation)
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError(f"재생 파일 {line_number}행 오류: {exc}") from exc
            frames += 1
            for event in events:
                if event.kind != "move":
                    actions += 1
                    print(f"{timestamp:.3f}s  {event.kind}")
    print(f"재생 완료: {frames}프레임, 상태/슬라이드 이벤트 {actions}회, 실제 입력 0회")
