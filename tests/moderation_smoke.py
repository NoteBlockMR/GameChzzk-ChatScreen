"""로컬 웹 페이지에서 공식 SDK 형태의 제재 패킷과 React 행 갱신을 재현."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl
from PySide6.QtTest import QTest
from PySide6.QtWebEngineCore import QWebEngineScript
from PySide6.QtWebEngineWidgets import QWebEngineView

app = QApplication([])
view = QWebEngineView()
script = QWebEngineScript()
script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
script.setSourceCode('window.WebSocket = class extends EventTarget { constructor(url) {super();} };\n' + Path('moderation.js').read_text(encoding='utf-8'))
view.page().scripts().insert(script)


def js(code):
    result = []
    view.page().runJavaScript(code, result.append)
    end = time.monotonic() + 5
    while not result:
        assert time.monotonic() < end, 'JavaScript timed out'
        QTest.qWait(20)
    return result[0]


def emit(cmd, body):
    packet = json.dumps(json.dumps({'cmd': cmd, 'bdy': body}))
    js(f'socket.dispatchEvent(new MessageEvent("message", {{data:{packet}}}));')
    QTest.qWait(600)


def hidden(name):
    return js(f'getComputedStyle(document.getElementById({json.dumps(name)})).display === "none"')


try:
    loaded = []
    view.loadFinished.connect(loaded.append)
    view.setHtml('<html><head></head><body></body></html>', QUrl('https://chzzk.naver.com/live/test/chat'))
    view.show()
    end = time.monotonic() + 10
    while not loaded:
        assert time.monotonic() < end
        QTest.qWait(20)
    js('''
      window.socket = new WebSocket('wss://kr-ss1.nchat.naver.com/chat');
      window.oldTime = Date.now() - 10000;
      window.addRow = (name, user, time) => {
        const row = document.createElement('div'); row.id=name;
        row.className='_chatting_message_w9pvh_21';
        row.textContent='동일닉네임: 추방당했습니다';
        row.__reactFiber$test={memoizedProps:{},return:{memoizedProps:{chatMessage:{user,time,status:'NORMAL'}}}};
        document.body.appendChild(row); return row;
      };
      addRow('a1','user-a',oldTime); addRow('a2','user-a',oldTime+1);
      addRow('b1','user-b',oldTime); addRow('noid','',oldTime);
    ''')
    emit(93101, {'msg': 'user-a 추방', 'userId': 'user-a'})
    assert not hidden('a1') and not hidden('b1')
    emit(94015, {'penaltyType': 'BAN', 'userId': 'user-a'})
    assert hidden('a1') and hidden('a2')
    assert not hidden('b1') and not hidden('noid')
    js("addRow('late','user-a',oldTime+2)")
    QTest.qWait(600)
    assert hidden('late')
    emit(94015, {'penaltyType': 'CANCEL', 'userId': 'user-a'})
    js("addRow('future','user-a',Date.now()+1000)")
    QTest.qWait(600)
    assert hidden('a1') and not hidden('future')
    js("document.getElementById('a1').__reactFiber$test.return.memoizedProps.chatMessage={user:'user-b',time:oldTime+5}")
    QTest.qWait(600)
    assert not hidden('a1'), 'recycled row remains incorrectly hidden'
    for name, cmd, body in [
        ('mute', 94015, {'penaltyType':'MUTE','userId':'mute-user'}),
        ('kick', 94005, {'quitUserIdList':['kick-user']}),
        ('temp', 93006, {'type':'TEMPORARY_RESTRICT','userIdHash':'temp-user'}),
        ('restrict', 93006, {'type':'RESTRICT_USER','userIdHash':'restrict-user'}),
    ]:
        js(f"addRow('{name}','{name}-user',oldTime)")
        emit(cmd, body)
        assert hidden(name), name
    old = js('oldTime')
    emit(94008, {'blindType':'BLIND','userId':'user-b','messageTime':old})
    assert hidden('b1') and not hidden('a1'), 'single deletion must not purge all messages'
    emit(94008, {'blindType':'CANCEL','userId':'user-b','messageTime':old})
    assert not hidden('b1')
    js("history.pushState({},'', '/live/other/chat')")
    QTest.qWait(600)
    assert not hidden('a2'), 'sanction leaked across channels'
    print('PASS: ban/mute/kick/restrict, matching user IDs only, late history, new messages after release, recycled rows, individual delete/undo, channel isolation')
finally:
    view.close()
