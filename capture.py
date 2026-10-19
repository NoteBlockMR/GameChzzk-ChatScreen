"""Windows Graphics Capture. UI가 늦어도 최신 프레임 한 장만 보관합니다."""
import ctypes
from ctypes import wintypes
import os
import threading

from PySide6.QtGui import QImage
from windows_capture import WindowsCapture


def window_api():
    api = ctypes.WinDLL('user32', use_last_error=True)
    api.IsWindow.argtypes = [wintypes.HWND]
    api.IsIconic.argtypes = [wintypes.HWND]
    api.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    api.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    api.GetForegroundWindow.restype = wintypes.HWND
    return api


def window_state(hwnd):
    api = window_api()
    if not api.IsWindow(hwnd):
        return '게임 창이 종료되었습니다. 목록을 새로고침하고 다시 선택하세요.'
    if api.IsIconic(hwnd):
        return '게임 창이 최소화되어 있습니다. 원래 게임 창을 다시 여세요.'
    return ''


def focus_game(hwnd):
    api = window_api()
    if not hwnd or not api.IsWindow(hwnd):
        return False
    api.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    api.SetForegroundWindow.argtypes = [wintypes.HWND]
    if api.IsIconic(hwnd):
        api.ShowWindow(hwnd, 9)
    return bool(api.SetForegroundWindow(hwnd))


def list_windows() -> list[tuple[int, str]]:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    result = []

    @callback_type
    def visit(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        length = user32.GetWindowTextLengthW(hwnd)
        if length and user32.IsWindowVisible(hwnd) and pid.value != os.getpid():
            text = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, text, length + 1)
            result.append((int(hwnd), text.value))
        return True

    user32.EnumWindows(visit, 0)
    return sorted(result, key=lambda item: item[1].lower())


class GameCapture:
    def __init__(self, hwnd: int):
        self.lock = threading.Lock()
        self.image = None
        self.closed = False
        self.error = ""
        self.control = None
        self.capture = WindowsCapture(window_hwnd=hwnd, cursor_capture=False,
                                      minimum_update_interval=33)

        @self.capture.event
        def on_frame_arrived(frame, control):
            try:
                # The mapped native frame is only valid inside this callback.
                # GPU row pitch can include padding; QImage's Python buffer
                # adapter requires a contiguous memoryview.
                data = frame.frame_buffer.copy(order="C")
                image = QImage(data.data, frame.width, frame.height, data.strides[0],
                               QImage.Format.Format_RGB32).copy()
                with self.lock:
                    self.image = image
            except Exception as exc:
                self.error = str(exc)
                self.closed = True
                control.stop()

        @self.capture.event
        def on_closed():
            self.closed = True

    def start(self):
        self.control = self.capture.start_free_threaded()

    def take_frame(self):
        with self.lock:
            image, self.image = self.image, None
            return image

    def stop(self):
        if self.control is not None:
            control, self.control = self.control, None
            control.stop()
        self.closed = True


class DesktopRegionCapture:
    """호환 모드: 실제 모니터에서 선택한 게임의 클라이언트 영역만 캡처."""
    def __init__(self, hwnd, output_hwnd=None):
        self.hwnd = hwnd
        self.output_hwnd = output_hwnd
        self.lock = threading.Lock()
        self.image = None
        self.closed = False
        self.error = ''
        self.waiting = ''
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run, name='game-region-capture', daemon=True)
        self.thread.start()

    def run(self):
        import mss
        api = window_api()
        try:
            with mss.mss() as desktop:
                while not self.stop_event.is_set():
                    if not api.IsWindow(self.hwnd):
                        self.error = '게임 창이 종료되었습니다.'
                        break
                    self.waiting = window_state(self.hwnd)
                    if self.output_hwnd and api.GetForegroundWindow() == self.output_hwnd:
                        self.waiting = '호환 모드: 원래 게임 창으로 돌아가세요. 녹화용 창은 게임 뒤에 두세요.'
                    if self.waiting:
                        with self.lock:
                            self.image = None
                        self.stop_event.wait(.1)
                        continue
                    rect = wintypes.RECT()
                    point = wintypes.POINT()
                    if not api.GetClientRect(self.hwnd, ctypes.byref(rect)) or not api.ClientToScreen(self.hwnd, ctypes.byref(point)):
                        raise RuntimeError('게임 영역 좌표를 가져올 수 없습니다.')
                    bounds = desktop.monitors[0]
                    left = max(point.x, bounds['left'])
                    top = max(point.y, bounds['top'])
                    right = min(point.x + rect.right, bounds['left'] + bounds['width'])
                    bottom = min(point.y + rect.bottom, bounds['top'] + bounds['height'])
                    if right <= left or bottom <= top:
                        self.waiting = '게임 창이 모니터 밖에 있습니다. 화면 안으로 이동하세요.'
                        self.stop_event.wait(.1)
                        continue
                    shot = desktop.grab({'left':left, 'top':top, 'width':right-left, 'height':bottom-top})
                    image = QImage(shot.bgra, shot.width, shot.height, shot.width * 4, QImage.Format.Format_RGB32).copy()
                    with self.lock:
                        self.image = image
                    self.stop_event.wait(.033)
        except Exception as exc:
            self.error = f'호환 캡처 실패: {exc}'
        finally:
            self.closed = True

    def take_frame(self):
        with self.lock:
            result, self.image = self.image, None
            return result

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=3)
        self.closed = True
