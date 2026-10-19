"""Hidden receiver → native cards, filtering and moderation regression."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import shiboken6
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineScript
from PySide6.QtTest import QTest
from main import ChatView
app=QApplication([])
profile=QWebEngineProfile(app)
view=ChatView(profile)
view.resize(340,720)
view.show()
def wait(check):
    until=time.monotonic()+10
    while not check():
        assert time.monotonic()<until, 'timeout'
        QTest.qWait(30)
def js(code):
    result=[]
    view.page().runJavaScript(code,result.append)
    wait(lambda: result)
    return result[0]
try:
    loaded=[]
    view.loadFinished.connect(loaded.append)
    script=QWebEngineScript()
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    script.setSourceCode('window.WebSocket = class extends EventTarget { constructor(url) {super();} };\n'+Path('moderation.js').read_text(encoding='utf-8'))
    # Replace the production hook to insert a mock socket before it.
    view.page().scripts().clear()
    view.page().scripts().insert(script)
    view.setHtml('<html><body><button>OFFICIAL LOGIN</button><div>OFFICIAL NOTICE</div></body></html>',QUrl('https://chzzk.naver.com/live/test/chat'))
    wait(lambda: loaded)
    js('''window.socket=new WebSocket('wss://kr-ss1.nchat.naver.com/chat');
    window.add=(id,user,nickname,content,time)=>{
      const row=document.createElement('div');row.id=id;row.className='chatting_message_test';row.textContent=content;
      row.__reactFiber$test={memoizedProps:{chatMessage:{user,time,profile:{nickname},content,status:'NORMAL'}}};
      document.body.appendChild(row);
    };
    add('a','a','별빛','오늘 게임 분위기 너무 좋네요 ✨',Date.now()-1000);
    add('b','b','민트','<b>안녕하세요!</b> 같이 봐요',Date.now()-999);
    ''')
    wait(lambda: len(view.messages)==2)
    assert not view.dialog.isVisible()
    import ctypes
    assert not ctypes.windll.user32.IsWindowVisible(int(view.receiver.winId()))
    texts=[label.text() for label in view.feed.findChildren(QLabel)]
    assert not any('OFFICIAL' in t for t in texts)
    assert '<b>안녕하세요!</b> 같이 봐요' in texts
    view.set_font_size(20)
    QTest.qWait(200)
    Path('artifacts').mkdir(exist_ok=True)
    view.grab().save('artifacts/custom-chat.png')
    js('socket.dispatchEvent(new MessageEvent("message",{data:JSON.stringify({cmd:94015,bdy:{penaltyType:"BAN",userId:"a"}})}))')
    wait(lambda: len(view.messages)==1)
    assert view.messages[0]['user']=='b'
    js('document.getElementById("b").remove()')
    wait(lambda: not view.messages)
    view.show_login()
    assert view.dialog.isVisible()
    view.dialog.close()
    assert not view.dialog.isVisible()
    print('CUSTOM_CHAT_OK: hidden receiver, native plain text, chrome excluded, ban/remove, login')
finally:
    view.timer.stop()
    view.close()
    shiboken6.delete(view)
    shiboken6.delete(profile)
