import sys,threading,time,json,urllib.request,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
spec=importlib.util.spec_from_file_location('bridge',Path('obs-plugin/bridge.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl,QTimer
from PySide6.QtTest import QTest
app=QApplication([]);bridge=module.Bridge();bridge.channel='a'*32
bridge.messages=[dict(nickname='<b>닉네임</b>',content='최신 메시지',user='test')];bridge.updated=time.monotonic()
timer=QTimer();timer.timeout.connect(lambda: setattr(bridge,'updated',time.monotonic()));timer.start(100)
server=module.make_server(bridge,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
base=f'http://127.0.0.1:{server.server_port}'
view=QWebEngineView();view.resize(380,720);view.show()
def js(code):
 result=[];view.page().runJavaScript(code,result.append)
 for _ in range(100):
  if result:return result[0]
  QTest.qWait(20)
 raise AssertionError('JS timeout')
try:
 loaded=[];view.loadFinished.connect(loaded.append);view.load(QUrl(base+'/?channel='+bridge.channel+'&font=Arial&size=24'))
 for _ in range(150):
  QTest.qWait(20)
  if loaded:break
 QTest.qWait(800)
 assert js('document.querySelector(".text").textContent')=='최신 메시지'
 assert js('document.querySelector(".name b")===null')
 bridge.messages=[];bridge.updated=time.monotonic();QTest.qWait(800)
 assert js('document.querySelectorAll(".card").length')==0
 bridge.messages=[dict(nickname='test',content='long '*500)];bridge.updated=time.monotonic();QTest.qWait(800)
 QTest.qWait(500)
 assert js('document.querySelector(".card").getBoundingClientRect().bottom<=innerHeight')
 server.shutdown();server.server_close();QTest.qWait(4000)
 assert js('document.querySelectorAll(".card").length')==0
 print('OBS_BRIDGE_OK: HTTP, safe text, deletion, newest visible, disconnect clears')
finally:
 view.close();server.shutdown();server.server_close()
