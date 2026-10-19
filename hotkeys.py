"""Windows 전역 단축키: 게임에 포커스가 있어도 전달됩니다."""
import ctypes
from ctypes import wintypes
from PySide6.QtCore import QAbstractNativeEventFilter, QTimer


class GlobalHotkeys(QAbstractNativeEventFilter):
    def __init__(self, app, callbacks):
        super().__init__()
        self.app = app
        self.callbacks = callbacks
        self.registered = []
        self.failed = []
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        app.installNativeEventFilter(self)
        for key_id, (vk, callback) in callbacks.items():
            # MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
            if self.user32.RegisterHotKey(None, key_id, 0x4003, vk):
                self.registered.append(key_id)
            else:
                self.failed.append(key_id)

    def nativeEventFilter(self, event_type, message):
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == 0x0312 and msg.wParam in self.registered:
            QTimer.singleShot(0, self.callbacks[msg.wParam][1])
            return True, 0
        return False, 0

    def close(self):
        for key_id in self.registered:
            self.user32.UnregisterHotKey(None, key_id)
        self.registered.clear()
        self.app.removeNativeEventFilter(self)
