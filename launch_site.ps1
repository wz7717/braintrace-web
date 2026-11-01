param(
    [string]$ScientificPython,
    [int]$Port=8766,
    [string]$PublicOrigin
)
$ErrorActionPreference='Stop'
if (-not $ScientificPython) {
    $taskConfigPath=Join-Path $PSScriptRoot 'runtime.local.json'
    if (Test-Path -LiteralPath $taskConfigPath) {
        $taskRuntime=Get-Content -LiteralPath $taskConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $ScientificPython=$taskRuntime.python
    }
}
if (-not $ScientificPython) { throw 'Specify -ScientificPython or configure runtime.local.json.' }
Push-Location -LiteralPath $PSScriptRoot
try {
    $taskSiteArgs=@('-X','utf8','-B',(Join-Path $PSScriptRoot 'site_server.py'),'--port',"$Port")
    if ($PublicOrigin) { $taskSiteArgs+=@('--public-origin',$PublicOrigin) }
    & $ScientificPython @taskSiteArgs
    if ($LASTEXITCODE -ne 0) { throw "BrainTrace exited with code $LASTEXITCODE" }
} finally { Pop-Location }
