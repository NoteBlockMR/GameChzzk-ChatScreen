param([string]$StreamerId)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not $StreamerId) { $StreamerId = Read-Host 'SOOP public BJ ID (not stream key)' }
if ($StreamerId -cnotmatch '^[a-zA-Z0-9_]{1,64}$') { throw 'Enter a public BJ ID, not a URL or stream key.' }
& java -Dfile.encoding=UTF-8 -cp 'soop-addon.jar;lib/*' SoopAddon $StreamerId
exit $LASTEXITCODE
