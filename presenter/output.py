"""모의 출력과 PowerPoint·데스크톱 입력을 분리한다."""

import ctypes
from ctypes import wintypes
import os
import sys


class DryRunOutput:
    def emit(self, events):
        for event in events:
            if event.kind not in ("move", "cursor_move", "drag_move"):
                detail = f" {event.steps:+d}" if event.kind == "scroll" else ""
                print(f"[MOCK] {event.kind}{detail}")

    def close(self):
        pass


def powerpoint_is_foreground():
    """PowerPoint 슬라이드 쇼 창에서만 입력 허용. 편집 창/미리보기는 제외."""
    if os.name != "nt":
        return False
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetClassNameW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = (
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    window = user32.GetForegroundWindow()
    class_name = ctypes.create_unicode_buffer(256)
    if not user32.GetClassNameW(window, class_name, 256):
        return False
    if class_name.value.lower() != "screenclass":
        return False
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(window, ctypes.byref(pid))
    process = kernel32.OpenProcess(0x1000, False, pid.value)  # QUERY_LIMITED_INFORMATION
    if not process:
        return False
    try:
        path = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(path))
        return bool(kernel32.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size))
                    and os.path.basename(path.value).lower() == "powerpnt.exe")
    finally:
        kernel32.CloseHandle(process)


def cursor_pixels(width, height, position):
    # 모서리 2px는 PyAutoGUI 비상 중단 구역이므로 자동 이동에서 제외한다.
    x, y = position
    return (max(2, min(width-3, round(x*(width-1)))),
            max(2, min(height-3, round(y*(height-1)))))


class PowerPointOutput:
    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("실제 PPT 입력은 Windows에서 지원합니다.")
        import pyautogui
        self.gui = pyautogui
        self.gui.FAILSAFE = True
        # 프레임마다 기본 PAUSE(0.1초)가 발생하지 않도록 하되 비상 중단은 유지.
        self.gui.PAUSE = 0.01
        self.pointer_active = False
        self.width, self.height = self.gui.size()

    def ready(self):
        return powerpoint_is_foreground()

    def emit(self, events):
        if not self.ready():
            return
        for event in events:
            if not self.ready():
                break
            if event.kind == "next":
                self.gui.press("right")
            elif event.kind == "previous":
                self.gui.press("left")
            elif event.kind == "pointer_on":
                self.gui.hotkey("ctrl", "l")
                self.pointer_active = True
            elif event.kind == "pointer_off":
                self.gui.hotkey("ctrl", "a")
                self.pointer_active = False
            elif event.kind == "move":
                self.gui.moveTo(*cursor_pixels(self.width, self.height, event.position))

    def close(self):
        if self.pointer_active and self.ready():
            self.gui.hotkey("ctrl", "a")
            self.pointer_active = False


class DesktopOutput:
    def __init__(self):
        if sys.platform not in ("win32", "darwin"):
            raise RuntimeError("실제 데스크톱 입력은 Windows와 macOS에서 지원합니다.")
        self.is_macos = sys.platform == "darwin"
        if self.is_macos:
            from Quartz import CGDisplayBounds, CGMainDisplayID, CGPreflightPostEventAccess
            if not CGPreflightPostEventAccess():
                raise RuntimeError("macOS 실제 입력에 손쉬운 사용 권한이 필요합니다. "
                                   "시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용에서 "
                                   "실행에 쓰는 터미널을 허용한 뒤 다시 실행하세요.")
            # Retina 화면에서도 Quartz가 사용하는 화면 좌표 크기로 변환한다.
            size = CGDisplayBounds(CGMainDisplayID()).size
            self.width, self.height = int(size.width), int(size.height)
        import pyautogui
        self.gui = pyautogui
        self.gui.FAILSAFE = True
        self.gui.PAUSE = 0.01
        if not self.is_macos:
            self.width, self.height = self.gui.size()
        self.dragging = False

    def ready(self):
        return True  # 데스크톱 모드는 현재 활성 앱에 입력한다.

    def emit(self, events):
        for event in events:
            kind = event.kind
            if kind == "drag_move":
                if self.dragging:
                    pixels = cursor_pixels(self.width, self.height, event.position)
                    if self.is_macos:
                        # macOS에서는 버튼을 유지한 이동도 별도의 드래그 이벤트로 보낸다.
                        self.gui.dragTo(*pixels, button="left", mouseDownUp=False)
                    else:
                        self.gui.moveTo(*pixels)
                continue
            if kind == "cursor_move":
                self.gui.moveTo(*cursor_pixels(self.width, self.height, event.position))
            elif kind == "click":
                self.gui.click(*cursor_pixels(self.width, self.height, event.position), button="left")
            elif kind == "drag_start" and not self.dragging:
                self.dragging = True
                self.gui.mouseDown(*cursor_pixels(self.width, self.height, event.position), button="left")
            elif kind in ("drag_end", "pause"):
                self.close()
            elif kind == "scroll":
                self.gui.scroll(event.steps)
            elif kind == "switch_next":
                self.gui.hotkey("command" if self.is_macos else "alt", "tab")
            elif kind == "switch_previous":
                self.gui.hotkey("command" if self.is_macos else "alt", "shift", "tab")

    def close(self):
        if self.dragging:
            # 모서리 비상 중단으로 빠져나오더라도 이미 누른 버튼은 놓는다.
            failsafe = self.gui.FAILSAFE
            try:
                self.gui.FAILSAFE = False
                self.gui.mouseUp(button="left")
                self.dragging = False
            finally:
                self.gui.FAILSAFE = failsafe
