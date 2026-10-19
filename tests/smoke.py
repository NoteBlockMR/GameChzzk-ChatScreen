"""실제 OS 마우스 입력/전역 단축키로 오버레이 동작을 검사합니다."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication, QPushButton

if '--fixture' in sys.argv:
    app = QApplication([])
    counter_file = Path(sys.argv[-1])
    counter_file.write_text('0')
    window = QPushButton('GAME WINDOW — CLICK TARGET')
    window.setWindowTitle('Overlay Test Game')
    window.setStyleSheet('background:#087f8c;color:white;font-size:24px')
    window.setGeometry(120, 120, 700, 650)
    count = [0]
    def clicked():
        count[0] += 1
        counter_file.write_text(str(count[0]))
    window.clicked.connect(clicked)
    window.show()
    counter_file.with_suffix('.hwnd').write_text(str(int(window.winId())))
    sys.exit(app.exec())

import ctypes
from ctypes import wintypes
import subprocess
import tempfile
import time
import shiboken6
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWebEngineCore import QWebEngineProfile
from main import Controller, STYLE

u32 = ctypes.WinDLL('user32', use_last_error=True)
u32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
u32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
u32.SetForegroundWindow.argtypes = [wintypes.HWND]
u32.GetForegroundWindow.restype = wintypes.HWND
u32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
u32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]


def wait_until(predicate, timeout=10):
    end = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > end:
            raise AssertionError('Timed out waiting for condition')
        QTest.qWait(50)


def hotkey(vk):
    for key in [0x11, 0x12, vk]:
        u32.keybd_event(key, 0, 0, 0)
    for key in [vk, 0x12, 0x11]:
        u32.keybd_event(key, 0, 2, 0)


def test():
    app = QApplication([])
    app.setStyleSheet(STYLE)
    profile = QWebEngineProfile(app)
    controller = fixture = None
    cursor = wintypes.POINT()
    u32.GetCursorPos(ctypes.byref(cursor))
    with tempfile.TemporaryDirectory(prefix='chzzk-overlay-test-') as temp:
        try:
            counter = Path(temp) / 'clicks.txt'
            fixture = subprocess.Popen([sys.executable, __file__, '--fixture', str(counter)])
            wait_until(lambda: counter.with_suffix('.hwnd').exists())
            game_hwnd = int(counter.with_suffix('.hwnd').read_text())
            settings = QSettings(str(Path(temp) / 'settings.ini'), QSettings.Format.IniFormat)
            controller = Controller(profile, settings)
            controller.move(850, 120)
            controller.show()
            overlay = controller.overlay
            overlay.setGeometry(220, 220, 380, 420)
            controller.channel.setText('https://evil.test/invalid')
            controller.connect_chat()
            assert '입력하세요' in controller.status.text()
            loaded = []
            overlay.chat.loadFinished.connect(loaded.append)
            overlay.chat.setHtml('<html><body style="background:#14171c;color:#00e8a4;font:22px sans-serif;padding:24px">CHZZK TEST CHAT<br><br>게임 화면 위에 표시</body></html>')
            wait_until(lambda: bool(loaded))
            assert loaded[-1]
            assert not controller.hotkeys.failed, 'Hotkey collision'
            u32.SetForegroundWindow(game_hwnd)
            QTest.qWait(300)
            hotkey(0x77)
            wait_until(lambda: overlay.locked)
            assert not overlay.bar.isVisible()
            style = u32.GetWindowLongW(int(overlay.winId()), -20)
            assert style & 0x8, 'Overlay is not topmost'
            assert style & 0x20, 'Click-through flag missing'
            assert style & 0x08000000, 'No-activate flag missing'
            rect = wintypes.RECT()
            u32.GetWindowRect(int(overlay.winId()), ctypes.byref(rect))
            u32.SetCursorPos((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
            u32.mouse_event(0x0002, 0, 0, 0, 0)
            u32.mouse_event(0x0004, 0, 0, 0, 0)
            wait_until(lambda: counter.read_text() == '1')
            assert u32.GetForegroundWindow() == game_hwnd, 'Overlay stole game focus'
            hotkey(0x78)
            wait_until(lambda: not overlay.isVisible())
            hotkey(0x78)
            wait_until(overlay.isVisible)
            hotkey(0x77)
            wait_until(lambda: not overlay.locked)
            assert overlay.bar.isVisible()
            assert not u32.GetWindowLongW(int(overlay.winId()), -20) & 0x20
            controller.opacity.setValue(65)
            assert abs(overlay.windowOpacity() - .65) < .01
            controller.showMinimized()
            QTest.qWait(200)
            assert overlay.isVisible(), 'Minimizing settings hid the overlay'
            Path('artifacts').mkdir(exist_ok=True)
            app.primaryScreen().grabWindow(0, 120, 120, 710, 670).save('artifacts/overlay-smoke.png')
            controller.close()
            assert settings.contains('geometry')
            assert not overlay.isVisible()
            print('PASS: game receives real clicks through overlay, topmost/no-activate, global hotkeys while game focused, show/hide, unlock, opacity, settings minimize, persistence, web panel')
        finally:
            u32.SetCursorPos(cursor.x, cursor.y)
            if controller:
                controller.close()
                shiboken6.delete(controller.overlay)
                shiboken6.delete(controller.recording)
                shiboken6.delete(controller)
            if fixture and fixture.poll() is None:
                fixture.terminate()
                fixture.wait(timeout=5)
            shiboken6.delete(profile)


if __name__ == '__main__':
    test()
