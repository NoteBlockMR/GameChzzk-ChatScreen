$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force lib,build/classes | Out-Null
foreach ($dependency in (Get-Content dependencies.json -Raw | ConvertFrom-Json)) {
    $destination = Join-Path 'lib' $dependency.name
    if (-not (Test-Path -LiteralPath $destination)) {
        Invoke-WebRequest $dependency.url -OutFile $destination
    }
    if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLower() -ne $dependency.sha256) {
        throw "Dependency checksum mismatch: $($dependency.name)"
    }
}
& javac --release 11 -encoding UTF-8 -cp 'lib/*' -d build/classes src/SoopAddon.java
if ($LASTEXITCODE -ne 0) { throw 'Java compilation failed' }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archivePath = Join-Path $PSScriptRoot ('build/' + [guid]::NewGuid().ToString() + '.jar')
[System.IO.Compression.ZipFile]::CreateFromDirectory((Join-Path $PSScriptRoot 'build/classes'), $archivePath)
Move-Item -LiteralPath $archivePath -Destination (Join-Path $PSScriptRoot 'soop-addon.jar') -Force
Write-Output 'Built soop-addon.jar (Java 11+)'
