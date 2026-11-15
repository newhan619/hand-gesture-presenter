"""장치나 추가 패키지가 필요 없는 모의 제스처 시나리오."""

from .core import GestureController, Observation, Shape


def demo_observations():
    t = 0.0
    steps = [
        (Shape.OPEN, 5, 0.3, 0.3),
        (Shape.OPEN, 6, 0.3, 0.6),   # 다음 장
        (Shape.OPEN, 40, 0.6, 0.9),  # 길게 움직여도 재입력 없음
        (Shape.FIST, 5, 0.5, 0.5),
        (Shape.OPEN, 5, 0.7, 0.7),
        (Shape.OPEN, 6, 0.7, 0.4),   # 이전 장
        (Shape.POINT, 5, 0.4, 0.4),  # 포인터 켜기
        (Shape.POINT, 6, 0.4, 0.8),  # 슬라이드는 넘기지 않음
        (None, 10, 0.5, 0.5),        # 미검출 즉시 정지와 이력 초기화
    ]
    for shape, frames, start, end in steps:
        for frame in range(frames):
            t += 1 / 30
            x = start + (end-start) * frame / max(1, frames-1)
            yield Observation(t, shape, (x, 0.5), (x, 0.4))


def run_demo():
    controller = GestureController()
    sequence = []
    for observation in demo_observations():
        for event in controller.update(observation):
            if event.kind != "move":
                sequence.append(event.kind)
                print(f"{observation.time:5.2f}s  {event.kind}")
    expected = ["next", "previous", "pointer_on", "pointer_off"]
    if sequence != expected:
        raise RuntimeError(f"모의 실행 실패: {sequence} != {expected}")
    print("PASS: 다음 장 1회, 이전 장 1회, 포인터 진입/종료, 반복 입력 차단")
