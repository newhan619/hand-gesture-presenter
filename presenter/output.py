"""모의 출력과 Windows PowerPoint 입력을 분리한다."""

import ctypes
from ctypes import wintypes
import os


class DryRunOutput:
    def emit(self, events):
        for event in events:
            if event.kind != "move":
                print(f"[MOCK] {event.kind}")

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
                # 모서리 2px는 PyAutoGUI 비상 중단 구역이므로 자동 이동에서 제외.
                x, y = event.position
                self.gui.moveTo(max(2, min(self.width-3, round(x*(self.width-1)))),
                                max(2, min(self.height-3, round(y*(self.height-1)))))

    def close(self):
        if self.pointer_active and self.ready():
            self.gui.hotkey("ctrl", "a")
            self.pointer_active = False
