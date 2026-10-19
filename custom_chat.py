"""Native chat-only presentation; the official browser is a hidden receiver."""
import hashlib
import json
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QWidget, QDialog, QVBoxLayout, QScrollArea, QLabel, QFrame

SNAPSHOT = r'''(() => {
 const result = [], seen = new Set();
 for (const row of document.querySelectorAll('[class*="live_chatting_list_item"], [class*="chatting_message"]')) {
   const prop = Object.keys(row).find(k => k.startsWith('__reactFiber$'));
   let fiber = prop && row[prop], message;
   for (let i=0; fiber && i<20; i++, fiber=fiber.return) {
     if (fiber.memoizedProps?.chatMessage) { message=fiber.memoizedProps.chatMessage; break; }
   }
   if (!message || typeof message.user !== 'string' || !Number.isFinite(message.time)) continue;
   if (row.closest('[data-gv-moderated]') || row.querySelector('[data-gv-moderated]')) continue;
   if (message.status && message.status !== 'NORMAL') continue;
   const key = message.user + ':' + message.time;
   if (seen.has(key)) continue;
   let profile = message.profile;
   if (typeof profile === 'string') { try { profile=JSON.parse(profile); } catch { profile={}; } }
   const nickname = profile?.nickname || row.querySelector('[class*="nickname"]')?.textContent;
   const content = message.content;
   if (!nickname || typeof content !== 'string' || !content.trim()) continue;
   seen.add(key);
   result.push({key, user:message.user, nickname, content});
 }
 return JSON.stringify(result.slice(-100));
})()'''


class CustomChatPanel(QWidget):
    loadFinished = Signal(bool)

    def __init__(self, profile, web_factory, parent=None):
        super().__init__(parent)
        self.font_size = 16
        self.messages = []
        self.generation = 0
        self.pending = False
        self.dialog = QDialog(self)
        self.dialog.setWindowTitle('치지직 로그인 · 연결 확인 (녹화 화면과 별도)')
        self.dialog.resize(460, 720)
        self.login_layout = QVBoxLayout(self.dialog)
        # A never-laid-out/hidden web view has a 0×0 viewport: CHZZK's
        # virtual list then produces no rows. Render offscreen at a real size.
        self.receiver = QWidget(self, Qt.WindowType.Tool)
        self.receiver.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.receiver.resize(380, 800)
        self.receiver_layout = QVBoxLayout(self.receiver)
        self.source = web_factory(profile, self.receiver)
        self.receiver_layout.addWidget(self.source)
        self.receiver.show()
        self.dialog.finished.connect(self._hide_login)
        self.popups = self.source.popups
        self.popups.append(self.dialog)
        self.source.loadStarted.connect(self._starting)
        self.source.loadFinished.connect(self._loaded)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        # Wrapped cards can change height after the first layout pass. Follow
        # the final scroll range, not the previous frame's maximum.
        self.scroll.verticalScrollBar().rangeChanged.connect(self._scroll_to_latest)
        self.scroll.setStyleSheet('QScrollArea,QWidget#chatFeed {background:#101321;} QScrollBar:vertical {width:4px;background:#101321;} QScrollBar::handle:vertical {background:#635c88;min-height:20px;}')
        self.feed = QWidget()
        self.feed.setObjectName('chatFeed')
        self.rows = QVBoxLayout(self.feed)
        self.rows.setContentsMargins(16, 20, 16, 20)
        self.rows.setSpacing(12)
        self.rows.addStretch()
        self.scroll.setWidget(self.feed)
        layout.addWidget(self.scroll)
        self._render()
        self.timer = QTimer(self)
        self.timer.setInterval(350)
        self.timer.timeout.connect(self._poll)
        self.timer.start()

    def page(self):
        return self.source.page()

    def url(self):
        return self.source.url()

    def load(self, url):
        self.source.load(url)

    def reload(self):
        self.source.reload()

    def setHtml(self, *args):
        self.source.setHtml(*args)

    def show_login(self):
        self.login_layout.addWidget(self.source)
        self.source.show()
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def _hide_login(self, _result):
        self.receiver_layout.addWidget(self.source)
        self.receiver.show()
        self.source.show()

    def set_font_size(self, size):
        self.font_size = max(12, min(24, int(size)))
        self._render()

    def _starting(self):
        self.generation += 1
        self.messages = []
        self._render()

    def _loaded(self, ok):
        self.loadFinished.emit(ok)
        if not ok and not self.messages:
            self.empty.setText('연결하지 못했어요\n설정에서 새로고침해 주세요')

    def _poll(self):
        if self.pending:
            return
        self.pending = True
        generation = self.generation
        def receive(raw):
            self.pending = False
            if generation != self.generation:
                return
            try:
                messages = json.loads(raw)
            except (ValueError, TypeError):
                return
            if isinstance(messages, list) and messages != self.messages:
                self.messages = messages
                self._render()
        self.page().runJavaScript(SNAPSHOT, 0, receive)

    def _scroll_to_latest(self, *_args):
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _render(self):
        while self.rows.count() > 1:
            item = self.rows.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self.empty = QLabel('대화가 모이는 곳\n채널 연결 후 메시지를 기다리고 있어요')
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setWordWrap(True)
        self.empty.setStyleSheet('color:#8f99b7;background:transparent;padding:24px 0;font-size:13px;')
        self.rows.addWidget(self.empty)
        self.empty.setVisible(not self.messages)
        colors = ('#b9a2ff', '#6ee7cb', '#f4b6d7', '#85c9ff', '#f5cf8f')
        for message in self.messages:
            color = colors[hashlib.sha256(message['user'].encode()).digest()[0] % len(colors)]
            card = QFrame()
            card.setObjectName('messageCard')
            card.setStyleSheet(f'QFrame#messageCard {{background:#1c2033;border:1px solid #30374e;border-left:3px solid {color};border-radius:12px;}}')
            box = QVBoxLayout(card)
            box.setContentsMargins(14, 12, 14, 14)
            box.setSpacing(6)
            for text, size, ink in ((message['nickname'], max(12, self.font_size-3), color), (message['content'], self.font_size, '#eef1ff')):
                label = QLabel(text)
                label.setTextFormat(Qt.TextFormat.PlainText)
                label.setWordWrap(True)
                label.setMinimumWidth(0)
                label.setStyleSheet(f'background:transparent;border:none;color:{ink};font-size:{size}px;')
                box.addWidget(label)
            self.rows.addWidget(card)
        QTimer.singleShot(0, self._scroll_to_latest)
