"""실제 외부 창 → 합성 창 → Windows 캡처로 게임과 웹 채팅이 함께 나오는지 확인."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import subprocess
import tempfile
import time
import shiboken6
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWebEngineCore import QWebEngineProfile
from main import Controller, STYLE
from capture import GameCapture


def wait_until(predicate, timeout=15):
    end = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > end:
            raise AssertionError('Timed out')
        QTest.qWait(50)


app = QApplication([])
app.setStyleSheet(STYLE)
profile = QWebEngineProfile(app)
controller = fixture = output_capture = None
with tempfile.TemporaryDirectory(prefix='chzzk-recording-') as temp:
    try:
        counter = Path(temp) / 'fixture.txt'
        fixture = subprocess.Popen([sys.executable, 'tests/smoke.py', '--fixture', str(counter)])
        wait_until(lambda: counter.with_suffix('.hwnd').exists())
        hwnd = int(counter.with_suffix('.hwnd').read_text())
        controller = Controller(profile, QSettings(str(Path(temp) / 'settings.ini'), QSettings.Format.IniFormat), register_hotkeys=False)
        controller.overlay.hide()
        controller.game_windows.setCurrentIndex(controller.game_windows.findData(hwnd))
        assert controller.game_windows.currentData() == hwnd
        assert controller.game_windows.findData(int(controller.recording.winId())) < 0
        controller.open_recording()
        output = controller.recording
        wait_until(lambda: output.frame_count > 0 or output.capture is None)
        assert output.capture is not None, controller.status.text()
        assert output.preview.image is not None
        loaded = []
        output.chat.loadFinished.connect(loaded.append)
        output.chat.setHtml('''<html lang="ko"><head></head><body style="margin:0;color:white">
        <div style="padding:12px;color:#8f98b5;font:11px sans-serif">디자인 미리보기 · 예시 메시지</div>
        <div class="chatting_message_test"><span class="nickname">달빛산책</span><br><span class="message_text">방금 플레이 진짜 멋있었어요 ✨</span></div>
        <div class="chatting_message_test"><span class="nickname">민트초코</span><br><span class="message_text">다음 스테이지도 가보자!</span></div>
        <div class="chatting_message_test"><span class="nickname">구름고래</span><br><span class="message_text">오늘 처음 왔는데 분위기 좋네요 👋</span></div>
        </body></html>''', QUrl('https://chzzk.naver.com/'))
        wait_until(lambda: bool(loaded))
        output.chat.page().runJavaScript("""
          document.querySelectorAll('.chatting_message_test').forEach((row,i)=>{
            row.__reactFiber$test={memoizedProps:{chatMessage:{user:'fixture-'+i,time:Date.now()+i,status:'NORMAL',
              profile:{nickname:row.querySelector('.nickname').textContent},content:row.querySelector('.message_text').textContent}}};
          });
        """)
        wait_until(lambda: len(output.chat.messages) == 3)
        controller.chat_font.setValue(20)
        assert output.chat.font_size == 20
        output.chat.page().runJavaScript("""
          const item=document.createElement('div');item.className='chatting_message_test';
          item.__reactFiber$test={memoizedProps:{chatMessage:{user:'fresh',time:Date.now(),status:'NORMAL',profile:{nickname:'새 시청자'},content:'새 메시지도 전용 카드로 표시됩니다'}}};
          document.body.appendChild(item);
        """)
        wait_until(lambda: len(output.chat.messages) == 4)
        controller.chat_width.setValue(380)
        assert output.panel.width() == 380
        # Capture the composed output through the same Windows API OBS can use.
        output_capture = GameCapture(int(output.winId()))
        output_capture.start()
        QTest.qWait(1000)
        frames = []
        def received():
            image = output_capture.take_frame()
            if image is not None:
                frames.append(image)
            return bool(frames)
        wait_until(received)
        frame = frames[-1]
        left = frame.pixelColor(100, frame.height() // 2)
        right = frame.pixelColor(frame.width() - 40, frame.height() // 2)
        assert left.green() > left.red() + 30, left.name()
        assert right.blue() > right.red() and right.green() < 70, right.name()
        Path('artifacts').mkdir(exist_ok=True)
        frame.save('artifacts/recording-window.png')
        output_capture.stop()
        output_capture = None
        controller.overlay.hide()
        assert output.isVisible()
        output.close()
        assert output.capture is None
        controller.open_recording()
        wait_until(lambda: output.frame_count > 0 or output.capture is None)
        assert output.capture is not None
        # Exercise the compatibility path with the real target in front.
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        from unittest.mock import patch
        controller.capture_mode.setCurrentIndex(controller.capture_mode.findData('auto'))
        with patch('recording.GameCapture', side_effect=RuntimeError('Failed to convert item to GraphicsCaptureItem')):
            controller.open_recording()
        assert output.capture_mode == 'desktop'
        assert '화면 영역' in controller.capture_method_label.text()
        user32.SetForegroundWindow(hwnd)
        wait_until(lambda: output.frame_count > 0 or output.capture.closed)
        assert output.frame_count > 0, output.capture.error
        # Wait for a frame captured after foreground activation, not a queued prior frame.
        wait_until(lambda: output.preview.image is not None and output.preview.image.pixelColor(20, 100).green() > output.preview.image.pixelColor(20, 100).red() + 30)
        user32.ShowWindow(hwnd, 6)
        wait_until(lambda: bool(output.capture.waiting))
        wait_until(lambda: output.preview.image is None)
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        wait_until(lambda: output.preview.image is not None)
        fixture.terminate()
        fixture.wait(timeout=5)
        wait_until(lambda: output.capture is None)
        assert output.preview.image is None
        from types import SimpleNamespace
        output.capture = SimpleNamespace(closed=False, waiting='', take_frame=lambda: None, stop=lambda: None)
        output.capture_hwnd = int(output.winId())
        output.capture_started = time.monotonic() - 6
        output.frame_count = 0
        output.timeout_reported = False
        output.update_frame()
        assert '게임 화면을 받지 못했습니다' in output.preview.message
        output.stop_capture()
        print('PASS: native and compatibility captures, minimize/restore, native custom chat, combined output capture, close/reopen, game exit')
    finally:
        if output_capture:
            output_capture.stop()
        if controller:
            controller.close()
            shiboken6.delete(controller.overlay)
            shiboken6.delete(controller.recording)
            shiboken6.delete(controller)
        if fixture and fixture.poll() is None:
            fixture.terminate()
            fixture.wait(timeout=5)
        shiboken6.delete(profile)
