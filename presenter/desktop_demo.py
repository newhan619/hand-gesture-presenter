"""카메라와 입력 장치 없이 21개 합성 좌표로 데스크톱 동작을 시험한다."""

from .core import Point, classify_hand
from .desktop import DesktopController, measure_desktop_hand


def demo_landmarks(shape, x=0.5, y=0.5):
    points = [Point(.5, .8)] * 21
    points[1:5] = [Point(.48, .72), Point(.4, .65), Point(.46, .61), Point(.51, .68)]
    if shape == "OPEN":
        points[1:5] = [Point(.48, .72), Point(.4, .65), Point(.32, .58), Point(.24, .51)]
    for base, finger_x in zip((5, 9, 13, 17), (.4, .48, .56, .64)):
        points[base] = Point(finger_x, .55)
        extended = (shape == "OPEN" or (base == 5 and shape in ("POINT", "TWO FINGERS"))
                    or (base == 9 and shape == "TWO FINGERS"))
        if extended:
            points[base+1:base+4] = [Point(finger_x, .41), Point(finger_x, .31), Point(finger_x, .21)]
        else:
            points[base+1:base+4] = [Point(finger_x, .43), Point(finger_x+.04, .51), Point(finger_x, .62)]
    if shape == "PINCH":
        points[6:9] = [Point(.4, .41), Point(.4, .31), Point(.445, .3)]
        points[4] = Point(.45, .305)
    elif shape == "FIST":
        # 가까운 두 손끝만으로 주먹이 클릭으로 오인되지 않는지도 확인한다.
        points[4] = Point(.405, .622)
    return [Point(p.x + x - .5, p.y + y - .5) for p in points]


def run_desktop_demo():
    controller = DesktopController()
    frames = [
        (0.00, "POINT", .5, .5),
        (0.07, "PINCH", .5, .5),
        (0.17, "POINT", .5, .5),
        (0.24, "PINCH", .5, .5),
        (0.33, "PINCH", .64, .5),
        (0.41, "PINCH", .68, .5),
        (0.49, "POINT", .68, .5),
        (0.56, "FIST", .68, .5),
        (0.65, "FIST", .42, .5),
        (0.73, "TWO FINGERS", .5, .5),
        (0.82, "TWO FINGERS", .5, .39),
        (0.90, "OPEN", .35, .5),
        (1.05, "OPEN", .64, .5),
    ]
    expected = [
        ["cursor_move"], [], ["click"], [], ["drag_start", "drag_move"],
        ["drag_move"], ["drag_end"], ["pause"], [], ["resume"], ["scroll"], [], ["switch_next"],
    ]
    for (now, shape, x, y), expected_events in zip(frames, expected):
        points = demo_landmarks(shape, x, y)
        pose = classify_hand(points)
        hand = measure_desktop_hand(points, pose, 1.0, "Right")
        events = [event.kind for event in controller.update(now, hand)]
        print(f"{now:4.2f}s | {controller.gesture:11} | {controller.action:14} | {', '.join(events) or '-'}")
        if events != expected_events:
            raise RuntimeError(f"데스크톱 모의 실행 실패: {events} != {expected_events}")
    print("PASS: 커서·클릭·드래그·일시정지·스크롤·창 전환 / 실제 입력 0회")
