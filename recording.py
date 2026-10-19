"""OBS에서 창 하나로 캡처하는 게임 + 오른쪽 채팅 출력 창."""
from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from capture import GameCapture, DesktopRegionCapture, window_state
import time
from channel import chat_url
from chat_theme import apply_chat_theme


class GamePreview(QWidget):
    def __init__(self):
        super().__init__()
        self.image = None
        self.message = '게임 화면을 기다리고 있습니다'
        self.setMinimumWidth(240)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#080c12'))
        if self.image is None:
            painter.setPen(QColor('#9cafbf'))
            painter.drawText(self.rect().adjusted(25, 25, -25, -25),
                             Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.message)
            return
        size = self.image.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        rect = self.rect()
        rect.setSize(size)
        rect.moveCenter(self.rect().center())
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(rect, self.image)


class RecordingWindow(QWidget):
    status = Signal(str)
    capture_method_changed = Signal(str)

    def __init__(self, profile, chat_factory, settings):
        super().__init__()
        self.setWindowTitle('CHZZK 게임 + 채팅 — OBS 녹화용')
        self.setMinimumSize(800, 450)
        self.resize(1280, 720)
        self.settings = settings
        self.capture = None
        self.channel = ''
        self.frame_count = 0
        self.elapsed_ticks = 0
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.preview = GamePreview()
        layout.addWidget(self.preview, 1)
        self.panel = QWidget()
        self.panel.setObjectName('chatPanel')
        self.panel.setStyleSheet('#chatPanel { background:#0e1020; border-left:1px solid #38334f; }')
        self.panel.setFixedWidth(340)
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        header = QWidget()
        header.setStyleSheet('background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #302745,stop:1 #171b30);')
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 18, 20, 16)
        label = QLabel('CHAT LOUNGE')
        label.setStyleSheet('background:transparent;color:#e8dfff;font-size:21px;font-weight:bold;letter-spacing:2px;')
        header_layout.addWidget(label)
        subtitle = QLabel('CHZZK  /  플레이에 대화를 더하다')
        subtitle.setStyleSheet('background:transparent;color:#b5a8d1;font-size:11px;')
        header_layout.addWidget(subtitle)
        panel_layout.addWidget(header)
        self.chat = chat_factory(profile, self.panel)
        panel_layout.addWidget(self.chat, 1)
        layout.addWidget(self.panel)
        apply_chat_theme(self.chat)
        self.chat.setHtml('<html lang="ko"><body style="background:#101923;color:#9aafc1;font:16px sans-serif;padding:30px;line-height:1.8">채널을 연결하면<br>이곳에 채팅이 표시됩니다.</body></html>')
        self.chat.loadFinished.connect(self.chat_loaded)
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.update_frame)

    def set_channel(self, channel):
        url = chat_url(channel)
        if channel != self.channel:
            self.channel = channel
            self.chat.load(QUrl(url))

    def chat_loaded(self, ok):
        if self.chat.url().scheme() == 'https':
            self.status.emit('녹화용 채팅 페이지 로드 완료' if ok else '녹화용 채팅 로드 실패 · 새로고침하세요.')

    def set_chat_width(self, width):
        self.panel.setFixedWidth(max(280, min(500, int(width))))

    def set_font_size(self, size):
        apply_chat_theme(self.chat, size)

    def start_capture(self, hwnd, mode='window'):
        self.stop_capture()
        self.capture_hwnd = hwnd
        self.capture_mode = mode
        self.capture_started = time.monotonic()
        self.timeout_reported = False
        self.last_frame_at = self.capture_started
        try:
            state = window_state(hwnd)
            if state:
                raise RuntimeError(state)
            self.capture = DesktopRegionCapture(hwnd, int(self.winId())) if mode == 'desktop' else GameCapture(hwnd)
            self.capture.start()
        except Exception as exc:
            self.stop_capture()
            if mode == 'auto' and not window_state(hwnd):
                return self.start_capture(hwnd, 'desktop')
            self.preview.message = f'게임 연결 실패\n{exc}'
            self.preview.update()
            self.status.emit(f'게임 연결 실패: {exc}')
            return False
        self.frame_count = 0
        self.elapsed_ticks = 0
        self.preview.message = '게임 연결 중…\n게임 창을 최소화하지 마세요.'
        self.preview.update()
        self.timer.start()
        self.capture_method_changed.emit('화면 영역 캡처 · 게임을 맨 앞으로 두세요' if mode == 'desktop' else 'Windows 게임 창 캡처')
        self.status.emit('게임 연결 중 · OBS에서 녹화용 창을 윈도우 캡처로 선택하세요.')
        return True

    def update_frame(self):
        if self.capture is None:
            return
        if self.capture.closed:
            message = self.capture.error or '게임 창이 닫혔거나 캡처가 종료되었습니다.'
            self.stop_capture()
            self.status.emit(message)
            return
        self.elapsed_ticks += 1
        waiting = getattr(self.capture, 'waiting', '') or window_state(self.capture_hwnd)
        if waiting:
            self.preview.image = None
            self.preview.message = waiting
            self.preview.update()
            self.status.emit(waiting)
            return
        image = self.capture.take_frame()
        if image is not None:
            self.preview.image = image
            self.preview.update()
            self.frame_count += 1
            self.last_frame_at = time.monotonic()
            if self.frame_count == 1:
                self.status.emit('게임 화면 수신 중 · 실제 게임 조작은 원래 게임 창에서 하세요.')
        elif not self.timeout_reported and self.frame_count == 0 and time.monotonic() - self.capture_started >= 5:
            self.timeout_reported = True
            if self.capture_mode == 'auto':
                self.start_capture(self.capture_hwnd, 'desktop')
                return
            message = '게임 화면을 받지 못했습니다.\n게임의 최소화를 해제하고 창 모드로 바꿔 보세요.\n계속 안 되면 설정의 캡처 방식을 호환 모드로 바꾸고 다시 연결하세요.'
            self.preview.message = message
            self.preview.update()
            self.status.emit(message.replace('\n', ' '))

    def stop_capture(self):
        self.timer.stop()
        capture, self.capture = self.capture, None
        if capture:
            try:
                capture.stop()
            except Exception as exc:
                self.status.emit(f'캡처 종료: {exc}')
        self.preview.image = None
        self.preview.message = '설정 창에서 게임을 선택하고 연결하세요.'
        self.preview.update()

    def closeEvent(self, event):
        self.stop_capture()
        for popup in list(self.chat.popups):
            popup.close()
        self.status.emit('녹화용 창을 닫았습니다. 게임 연결 버튼으로 다시 열 수 있습니다.')
        super().closeEvent(event)
