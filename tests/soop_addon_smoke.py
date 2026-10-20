"""Local Java bridge checks; no SOOP connection."""
import json, subprocess, time, http.client, re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def request(headers=None, method='GET'):
    c=http.client.HTTPConnection('127.0.0.1',18767,timeout=2)
    try:
        c.request(method,'/state',headers=headers or {})
        r=c.getresponse()
        return r.status,dict(r.getheaders()),json.loads(r.read())
    finally:c.close()
details=subprocess.run(['java','-XshowSettings:properties','-version'],capture_output=True,text=True).stderr
java_home=re.search(r'java.home = (.+)',details).group(1).strip()
java=str(Path(java_home)/'bin/java.exe')
proc=subprocess.Popen([java,'-cp','soop-addon.jar;lib/*','SoopAddon','fixture_soop','--fixture'],cwd=root/'addons/soop4j',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    for attempt in range(50):
        if proc.poll() is not None:raise AssertionError('Java addon exited')
        try:
            status,headers,state=request()
            if state.get('messages'):break
        except OSError:pass
        time.sleep(.1)
    else:raise AssertionError('Bridge did not start')
    assert proc.poll() is None, 'Expected own bridge process'
    assert state['channel']=='fixture_soop' and '<b>' in state['messages'][0]['content']
    for origin in ['http://127.0.0.1:18766','http://localhost:18766']:
        code,headers,_=request({'Origin':origin})
        assert code==200 and any(k.lower()=='access-control-allow-origin' and v==origin for k,v in headers.items())
    for headers in [{'Origin':'https://evil.example'},{'Host':'evil.example:18767'}]:
        assert request(headers)[0]==403
    assert request(method='POST')[0]==405
    print('SOOP_HTTP_OK: fixture, channel, JSON, allowed origins, denied origins/host/POST')
finally:
    proc.terminate()
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:proc.kill();proc.wait()
