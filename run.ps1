param([ValidateSet('demo','preview','present','check')][string]$Mode = 'demo',
      [int]$Camera = 0)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw 'Run .\setup.ps1 first, or use Python 3.12 to run main.py --demo.'
}
$modeArgs = @(switch ($Mode) {
    'demo' { @('--demo') }
    'preview' { @('--camera', "$Camera") }
    'present' { @('--camera', "$Camera", '--enable-input') }
    'check' { @('--check-model') }
})
& $venvPython -X utf8 main.py @modeArgs
exit $LASTEXITCODE
