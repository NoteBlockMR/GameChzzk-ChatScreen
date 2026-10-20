"""Verify the shipped PowerShell launcher's exact Java argument boundaries."""
import json, subprocess, sys
from pathlib import Path
launcher=Path(sys.argv[1] if len(sys.argv)>1 else 'addons/soop4j/start.ps1').resolve()
quoted=str(launcher).replace("'","''")
script="function java { ConvertTo-Json -InputObject @($args) -Compress; $global:LASTEXITCODE=0 }; & '"+quoted+"' -StreamerId fixture_soop"
r=subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-Command',script],capture_output=True,text=True)
assert r.returncode==0,r.stderr
assert json.loads(r.stdout)==['-Dfile.encoding=UTF-8','-cp','soop-addon.jar;lib/*','SoopAddon','fixture_soop'],r.stdout
r=subprocess.run(['powershell','-NoProfile','-Command',"& java '-Dfile.encoding=UTF-8' -version"],capture_output=True,text=True)
assert r.returncode==0,r.stderr
print('LAUNCHER_OK: PowerShell passes exact arguments; real Java accepts encoding option')
