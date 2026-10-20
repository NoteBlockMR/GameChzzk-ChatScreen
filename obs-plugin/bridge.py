"""Local-only bridge for the OBS Lua extension. Run separately from OBS."""
import sys, json, threading, time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer, QUrl, Signal, QObject
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtWebEngineCore import QWebEngineProfile
from main import ChatView
from channel import channel_id, chat_url

ROOT=Path(__file__).resolve().parent
class Bridge(QObject):
    requested=Signal(str)
    def __init__(self):
        super().__init__()
        self.lock=threading.Lock()
        self.channel=''
        self.messages=[]
        self.updated=0
    def snapshot(self):
        with self.lock:
            return dict(channel=self.channel,messages=self.messages if time.monotonic()-self.updated<5 else [])


def make_server(bridge, port=18765):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'):
                self.send_error(403);return
            url=urlparse(self.path)
            if url.path=='/state':
                try: key=channel_id(parse_qs(url.query).get('channel',[''])[0])
                except ValueError: self.send_error(400,'Invalid channel');return
                bridge.requested.emit(key)
                data=bridge.snapshot()
                if data['channel']!=key:data=dict(channel=key,messages=[])
                payload=json.dumps(data,ensure_ascii=False).encode()
                mime='application/json; charset=utf-8'
            elif url.path=='/':
                payload=(ROOT/'overlay.html').read_bytes();mime='text/html; charset=utf-8'
            else:self.send_error(404);return
            self.send_response(200)
            self.send_header('Content-Type',mime)
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Length',str(len(payload)))
            self.end_headers()
            try:self.wfile.write(payload)
            except (BrokenPipeError,ConnectionResetError):pass
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


def main():
    app=QApplication(sys.argv)
    app.setApplicationName('ChzzkObsBridge')
    bridge=Bridge()
    window=QWidget();window.setWindowTitle('CHZZK · OBS 채팅 수신기');window.resize(430,160)
    layout=QVBoxLayout(window)
    label=QLabel('OBS 스크립트에서 채널을 설정해 주세요.\n이 창은 최소화해도 됩니다. 닫으면 수신을 종료합니다.')
    label.setWordWrap(True);layout.addWidget(label)
    profile=QWebEngineProfile('chzzk-obs-bridge',app)
    panel=ChatView(profile,window)
    panel.hide()
    button=QPushButton('치지직 로그인 · 연결 확인');button.clicked.connect(panel.show_login);layout.addWidget(button)
    def connect(key):
        if key==bridge.channel:return
        with bridge.lock:
            bridge.channel=key;bridge.messages=[];bridge.updated=0
        panel.load(QUrl(chat_url(key)))
        label.setText('OBS 채팅 수신 중 · 한 채널 지원\n창을 닫으면 채팅 수신이 종료됩니다.')
    bridge.requested.connect(connect)
    timer=QTimer(window)
    def publish():
        with bridge.lock:
            bridge.messages=list(panel.messages);bridge.updated=time.monotonic()
    timer.timeout.connect(publish);timer.start(250)
    try:server=make_server(bridge)
    except OSError:
        label.setText('18765 포트를 사용할 수 없습니다. 이미 켜진 수신기를 확인하세요.')
        window.show();return app.exec()
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    window.show()
    result=app.exec()
    server.shutdown();server.server_close();thread.join(timeout=2)
    import shiboken6
    panel.timer.stop();shiboken6.delete(window);shiboken6.delete(profile)
    return result
if __name__=='__main__':sys.exit(main())
