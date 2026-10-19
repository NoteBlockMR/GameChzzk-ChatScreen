"""게임 위 채팅 오버레이 + 게임/채팅을 합친 OBS 녹화용 창."""
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QSettings, QStandardPaths, Signal, QTimer
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSlider, QSizeGrip, QComboBox, QGroupBox, QSpinBox,
    QSystemTrayIcon, QMenu, QStyle, QFontComboBox)
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QColor, QFont, QFontDatabase

from channel import channel_id, chat_url
from hotkeys import GlobalHotkeys
from recording import RecordingWindow
from capture import list_windows, focus_game
from chat_theme import apply_chat_theme
from moderation import install_moderation


class ChatPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, kind, main_frame):
        if not main_frame or url.scheme() in ('about', 'data'):
            return True
        host = url.host().lower()
        return url.scheme() == 'https' and (host == 'naver.com' or host.endswith('.naver.com'))


class OfficialChatView(QWebEngineView):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.popups = []
        page = ChatPage(profile, self)
        page.setBackgroundColor(QColor('#14171c'))
        page.permissionRequested.connect(lambda permission: permission.deny())
        self.setPage(page)
        install_moderation(self)
        apply_chat_theme(self)

    def createWindow(self, _kind):
        popup = OfficialChatView(self.profile, self)
        popup.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        popup.setWindowTitle('치지직 / 네이버 로그인')
        popup.resize(520, 760)
        self.popups.append(popup)
        popup.page().windowCloseRequested.connect(popup.close)
        popup.destroyed.connect(lambda: self.popups.remove(popup) if popup in self.popups else None)
        popup.show()
        return popup


from custom_chat import CustomChatPanel


class ChatView(CustomChatPanel):
    def __init__(self, profile, parent=None):
        super().__init__(profile, OfficialChatView, parent)


class DragBar(QLabel):
    def __init__(self, parent):
        super().__init__('CHAT LOUNGE  ·  드래그하여 이동', parent)
        self.setStyleSheet('background:#29233f;color:#e8dfff;padding:12px;font-weight:bold;letter-spacing:1px;')
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.offset = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.offset = event.globalPosition().toPoint() - self.window().pos()

    def mouseMoveEvent(self, event):
        if self.offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self.offset)

    def mouseReleaseEvent(self, event):
        self.offset = None

    def mouseDoubleClickEvent(self, event):
        self.window().settings_requested.emit()


class ChatOverlay(QWidget):
    changed = Signal()
    settings_requested = Signal()

    def __init__(self, profile, settings):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle('치지직 게임 오버레이')
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.settings = settings
        self.locked = False
        self.resize(380, 600)
        self.setMinimumSize(280, 200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.bar = DragBar(self)
        self.bar.setToolTip('드래그: 이동 · 더블클릭: 설정 창 열기')
        layout.addWidget(self.bar)
        self.chat = ChatView(profile, self)
        layout.addWidget(self.chat, 1)
        self.bottom = QWidget()
        row = QHBoxLayout(self.bottom)
        row.setContentsMargins(8, 0, 0, 0)
        row.addWidget(QLabel('오른쪽 아래 모서리로 크기 조절'), 1)
        row.addWidget(QSizeGrip(self))
        layout.addWidget(self.bottom)
        self.reset_position()
        saved = settings.value('geometry')
        if saved is not None:
            self.restoreGeometry(saved)
        # A disconnected monitor must not strand the overlay off-screen.
        if not any(screen.availableGeometry().intersects(self.geometry()) for screen in QApplication.screens()):
            self.reset_position()
        self.chat.setHtml('<html lang="ko"><body style="background:#14171c;color:#dce4ed;font:15px sans-serif;padding:25px;line-height:1.8">설정 창에서 치지직 채널 주소를 입력하세요.<br><br>채팅창을 게임 위 원하는 위치로 옮긴 뒤<br><b>게임 모드</b>를 켜세요.<br><br>Ctrl+Alt+F8: 클릭 통과 켜기/끄기<br>Ctrl+Alt+F9: 채팅 숨기기/표시</body></html>')

    def reset_position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(380, min(600, screen.height() - 40))
        self.move(screen.right() - self.width() - 20, screen.top() + 20)

    def set_locked(self, locked):
        was_visible = self.isVisible()
        geometry = self.geometry()
        self.locked = bool(locked)
        self.bar.setVisible(not self.locked)
        self.bottom.setVisible(not self.locked)
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, self.locked)
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, self.locked)
        self.setGeometry(geometry)
        if was_visible:
            self.show()
        self.changed.emit()

    def toggle_visible(self):
        self.setVisible(not self.isVisible())
        self.changed.emit()

    def save(self):
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.sync()


class Controller(QWidget):
    def __init__(self, profile, settings=None, register_hotkeys=True):
        super().__init__()
        self.settings = settings if settings is not None else QSettings('NoteBlockCode', 'ChzzkOverlayPython')
        self.setWindowTitle('치지직 게임 · 녹화 화면 설정')
        self.resize(560, 340)
        self.overlay = ChatOverlay(profile, self.settings)
        self.recording = RecordingWindow(profile, ChatView, self.settings)
        self.hotkeys = None
        layout = QVBoxLayout(self)
        title = QLabel('게임 + 치지직 채팅')
        title.setStyleSheet('font-size:20px;color:#00e8a4;font-weight:bold;padding:8px 0;')
        layout.addWidget(title)
        self.channel = QLineEdit(str(self.settings.value('channel', '')))
        self.channel.setPlaceholderText('https://chzzk.naver.com/live/채널ID')
        self.channel.returnPressed.connect(self.connect_chat)
        layout.addWidget(self.channel)
        row = QHBoxLayout()
        self.add_button(row, '채팅 연결', self.connect_chat)
        self.add_button(row, '새로고침', self.reload_chats)
        self.add_button(row, '로그인 · 연결 확인', self.overlay.chat.show_login)
        self.add_button(row, '위치 초기화', self.reset_overlay)
        layout.addLayout(row)
        group = QGroupBox('OBS 녹화용 창 · 게임 + 오른쪽 채팅')
        output_layout = QVBoxLayout(group)
        row = QHBoxLayout()
        self.game_windows = QComboBox()
        self.game_windows.setMinimumWidth(240)
        row.addWidget(self.game_windows, 1)
        self.add_button(row, '창 목록 새로고침', self.refresh_game_windows)
        output_layout.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel('캡처 방식'))
        self.capture_mode = QComboBox()
        self.capture_mode.addItem('자동 (실패 시 화면 영역 캡처)', 'auto')
        self.capture_mode.addItem('게임 창 캡처만 사용', 'window')
        self.capture_mode.addItem('화면 영역 캡처 (호환 모드)', 'desktop')
        row.addWidget(self.capture_mode, 1)
        output_layout.addLayout(row)
        self.capture_method_label = QLabel('현재 캡처 방식: 연결 전')
        self.capture_method_label.setWordWrap(True)
        self.recording.capture_method_changed.connect(lambda method: self.capture_method_label.setText('현재 캡처 방식: ' + method))
        output_layout.addWidget(self.capture_method_label)
        capture_hint = QLabel('호환 모드는 화면에 보이는 게임 영역을 가져옵니다. 게임을 맨 앞으로 두고 녹화용 창은 뒤에 두세요. 다른 창이 겹치면 함께 찍힙니다.')
        capture_hint.setWordWrap(True)
        output_layout.addWidget(capture_hint)
        row = QHBoxLayout()
        self.add_button(row, '게임 연결 · 녹화용 창 열기', self.open_recording)
        self.add_button(row, '캡처 중지', self.recording.stop_capture)
        self.add_button(row, '원래 게임으로 돌아가기', self.return_to_game)
        output_layout.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel('출력 크기'))
        self.output_size = QComboBox()
        self.output_size.addItem('1280 × 720', (1280, 720))
        self.output_size.addItem('1920 × 1080', (1920, 1080))
        self.output_size.currentIndexChanged.connect(self.resize_recording)
        row.addWidget(self.output_size)
        row.addWidget(QLabel('채팅 폭'))
        self.chat_width = QSpinBox()
        self.chat_width.setRange(280, 500)
        self.chat_width.setValue(340)
        self.chat_width.setSuffix(' px')
        self.chat_width.valueChanged.connect(self.recording.set_chat_width)
        row.addWidget(self.chat_width)
        row.addWidget(QLabel('글자'))
        self.chat_font = QSpinBox()
        self.chat_font.setRange(12, 24)
        self.chat_font.setValue(16)
        self.chat_font.valueChanged.connect(self.set_chat_font)
        row.addWidget(self.chat_font)
        output_layout.addLayout(row)
        font_row = QHBoxLayout()
        font_row.addWidget(QLabel('채팅 폰트'))
        self.chat_font_family = QFontComboBox()
        self.chat_font_family.setToolTip('Windows에 설치된 폰트 · 새 폰트를 설치했다면 앱을 다시 실행하세요.')
        saved_family = str(self.settings.value('chat_font_family', 'Malgun Gothic'))
        if saved_family not in QFontDatabase.families():
            saved_family = 'Malgun Gothic'
        self.chat_font_family.setCurrentFont(QFont(saved_family))
        self.chat_font_family.currentFontChanged.connect(self.set_chat_font_family)
        font_row.addWidget(self.chat_font_family, 1)
        output_layout.addLayout(font_row)
        self.set_chat_font_family(self.chat_font_family.currentFont())
        hint = QLabel('OBS → 윈도우 캡처 → CHZZK 게임 + 채팅 — OBS 녹화용\n클라이언트 영역 캡처를 켜세요. 게임 소리는 OBS에서 별도로 추가합니다.')
        hint.setWordWrap(True)
        output_layout.addWidget(hint)
        layout.addWidget(group)
        row = QHBoxLayout()
        self.lock_button = self.add_button(row, '', lambda: self.overlay.set_locked(not self.overlay.locked))
        self.visible_button = self.add_button(row, '', self.overlay.toggle_visible)
        layout.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel('채팅창 불투명도'))
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(30, 100)
        try:
            opacity = int(self.settings.value('opacity', 90))
        except (ValueError, TypeError):
            opacity = 90
        self.opacity.setValue(max(30, min(100, opacity)))
        row.addWidget(self.opacity, 1)
        self.opacity_label = QLabel()
        row.addWidget(self.opacity_label)
        self.opacity.valueChanged.connect(self.set_opacity)
        layout.addLayout(row)
        instructions = QLabel('① 게임을 창 모드/테두리 없는 창 모드로 실행\n② 채팅창 위치·크기 조절 → 게임 모드 켜기\n③ 게임으로 돌아가면 채팅 위에서도 게임 클릭 가능\n\nCtrl+Alt+F8: 게임 모드 전환 · Ctrl+Alt+F9: 숨김/표시\n설정 창은 최소화해도 됩니다. 닫으면 오버레이도 종료됩니다.')
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        self.status = QLabel('채널 주소를 입력하세요.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.hotkey_status = QLabel()
        self.hotkey_status.setWordWrap(True)
        layout.addWidget(self.hotkey_status)
        self.overlay.chat.loadFinished.connect(self.loaded)
        self.recording.status.connect(self.status.setText)
        self.overlay.changed.connect(self.sync_buttons)
        self.overlay.settings_requested.connect(self.show_settings)
        self.overlay.show()
        self.set_opacity(self.opacity.value())
        self.sync_buttons()
        self.refresh_game_windows()
        self.tray = QSystemTrayIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), self)
        self.tray.setToolTip('CHZZK Chat Lounge · 클릭하면 설정 열기')
        self.tray_menu = QMenu(self)
        self.settings_action = self.tray_menu.addAction('설정 창 열기')
        self.settings_action.triggered.connect(self.show_settings)
        self.tray_menu.addAction('채팅 숨김 / 표시', self.overlay.toggle_visible)
        self.tray_menu.addAction('채팅 편집 모드', lambda: self.overlay.set_locked(False))
        self.tray_menu.addSeparator()
        self.tray_menu.addAction('종료', self.close)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()
        instructions.setText(instructions.text() + '\n설정 다시 열기: 트레이 아이콘 클릭 또는 채팅 상단 더블클릭')
        if register_hotkeys:
            self.hotkeys = GlobalHotkeys(QApplication.instance(), {
                0x5101: (0x77, lambda: self.overlay.set_locked(not self.overlay.locked)),
                0x5102: (0x78, self.overlay.toggle_visible),
            })
            if self.hotkeys.failed:
                self.hotkey_status.setText('일부 전역 단축키를 등록하지 못했습니다. 다른 앱의 단축키를 해제하거나 이 설정 창 버튼을 사용하세요.')
        if self.channel.text():
            self.connect_chat()

    @staticmethod
    def add_button(layout, text, callback):
        button = QPushButton(text)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def show_settings(self):
        if not any(screen.availableGeometry().intersects(self.frameGeometry()) for screen in QApplication.screens()):
            area = QApplication.primaryScreen().availableGeometry()
            self.move(area.topLeft() + (area.center() - area.topLeft()) / 2)
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_settings()

    def set_opacity(self, value):
        self.overlay.setWindowOpacity(value / 100)
        self.opacity_label.setText(f'{value}%')
        self.settings.setValue('opacity', value)

    def refresh_game_windows(self):
        previous = self.game_windows.currentData()
        self.game_windows.clear()
        for hwnd, title in list_windows():
            self.game_windows.addItem(title, hwnd)
        index = self.game_windows.findData(previous)
        if index >= 0:
            self.game_windows.setCurrentIndex(index)

    def resize_recording(self):
        self.recording.resize(*self.output_size.currentData())

    def set_chat_font_family(self, font):
        family = font.family()
        self.overlay.chat.set_font_family(family)
        self.recording.chat.set_font_family(family)
        self.settings.setValue("chat_font_family", family)

    def set_chat_font(self, size):
        self.recording.set_font_size(size)
        apply_chat_theme(self.overlay.chat, size)

    def reload_chats(self):
        self.overlay.chat.reload()
        if self.recording.channel:
            self.recording.chat.reload()

    def open_recording(self):
        hwnd = self.game_windows.currentData()
        if hwnd is None:
            self.status.setText('게임을 실행한 뒤 창 목록을 새로고침하세요.')
            return
        if self.channel.text().strip():
            try:
                key = channel_id(self.channel.text())
            except ValueError as exc:
                self.status.setText(str(exc))
                return
            self.recording.set_channel(key)
        self.resize_recording()
        self.recording.show()
        self.recording.start_capture(hwnd, self.capture_mode.currentData())

    def return_to_game(self):
        hwnd = getattr(self.recording, 'capture_hwnd', None) or self.game_windows.currentData()
        if not focus_game(hwnd):
            self.status.setText('게임 창을 앞으로 가져오지 못했습니다. Alt+Tab으로 직접 돌아가세요.')

    def sync_buttons(self):
        self.lock_button.setText('편집 모드로 전환' if self.overlay.locked else '게임 모드 켜기 (클릭 통과)')
        self.visible_button.setText('채팅 숨기기' if self.overlay.isVisible() else '채팅 표시')

    def reset_overlay(self):
        self.overlay.set_locked(False)
        self.overlay.reset_position()
        self.overlay.show()
        self.sync_buttons()

    def connect_chat(self):
        try:
            key = channel_id(self.channel.text())
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        self.channel.setText(f'https://chzzk.naver.com/live/{key}')
        self.settings.setValue('channel', self.channel.text())
        self.overlay.chat.load(QUrl(chat_url(key)))
        self.recording.set_channel(key)
        self.status.setText('치지직 채팅 페이지를 불러오는 중…')

    def loaded(self, success):
        if self.overlay.chat.url().scheme() == 'https':
            self.status.setText('페이지 로드 완료 · 실제 채팅 연결 상태는 채팅창을 확인하세요.' if success else '채팅 로드 실패 · 네트워크 확인 후 새로고침하세요.')

    def closeEvent(self, event):
        self.tray.hide()
        if self.hotkeys is not None:
            self.hotkeys.close()
            self.hotkeys = None
        self.overlay.save()
        self.recording.close()
        self.overlay.close()
        for popup in list(self.overlay.chat.popups):
            popup.close()
        super().closeEvent(event)


STYLE = '''
QWidget { background:#14171c; color:#eaf0f7; font-family:'Malgun Gothic'; font-size:13px; }
QLineEdit { background:#202733; border:1px solid #364152; border-radius:5px; padding:9px; }
QPushButton { background:#273342; border:1px solid #405169; border-radius:5px; padding:9px; }
QPushButton:hover { background:#36516a; }
'''


def main():
    import tempfile
    smoke = '--package-smoke' in sys.argv
    smoke_dir = tempfile.TemporaryDirectory(prefix='chzzk-package-test-') if smoke else None
    app = QApplication(sys.argv)
    app.setApplicationName('ChzzkOverlayPython')
    app.setStyleSheet(STYLE)
    profile = QWebEngineProfile(app) if smoke else QWebEngineProfile('chzzk-overlay', app)
    storage = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)) / 'browser'
    profile.setPersistentStoragePath(str(storage))
    profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
    settings = QSettings(str(Path(smoke_dir.name) / 'settings.ini'), QSettings.Format.IniFormat) if smoke else None
    window = Controller(profile, settings, register_hotkeys=not smoke)
    window.show()
    QTimer.singleShot(0, window.show_settings)
    if smoke:
        def check_startup():
            import ctypes
            from ctypes import wintypes
            visible = ctypes.windll.user32.IsWindowVisible
            visible.argtypes = [wintypes.HWND]
            if not visible(int(window.winId())):
                print('PACKAGE_SMOKE_SETTINGS_HIDDEN', flush=True)
                app.exit(2)
                return
            print('PACKAGE_SMOKE_SETTINGS_VISIBLE', flush=True)
            window.hide()
            window.settings_action.trigger()
            if not visible(int(window.winId())):
                print('PACKAGE_SMOKE_TRAY_RESTORE_FAILED', flush=True)
                app.exit(3)
                return
            print('PACKAGE_SMOKE_TRAY_RESTORE_OK', flush=True)
            window.close()
        QTimer.singleShot(1500, check_startup)
    result = app.exec()
    import shiboken6
    shiboken6.delete(window.overlay)
    shiboken6.delete(window.recording)
    shiboken6.delete(window)
    shiboken6.delete(profile)
    if smoke_dir:
        smoke_dir.cleanup()
    return result


if __name__ == '__main__':
    sys.exit(main())
