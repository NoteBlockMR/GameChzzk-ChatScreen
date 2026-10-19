"""공식 웹 채팅 수신 이벤트를 읽어 앱 화면의 삭제 상태를 반영합니다."""
from pathlib import Path
from PySide6.QtWebEngineCore import QWebEngineScript


def install_moderation(view):
    script = QWebEngineScript()
    script.setName('game-view-moderation')
    # Install before the official client constructs its WebSocket.
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    script.setRunsOnSubFrames(False)
    script.setSourceCode(Path(__file__).with_name('moderation.js').read_text(encoding='utf-8'))
    view.page().scripts().insert(script)
