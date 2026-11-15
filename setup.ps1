param([string]$PythonPath = "", [switch]$SkipModel)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    if ($PythonPath) {
        $basePython = $PythonPath
        $baseArgs = @()
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        $basePython = 'py'
        $baseArgs = @('-3.12')
    } else {
        $basePython = 'python'
        $baseArgs = @()
    }
    & $basePython @baseArgs -c "import sys,struct; assert sys.version_info[:2]==(3,12) and struct.calcsize('P')==8, 'Install Python 3.12 64-bit first'"
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 64-bit is required.' }
    & $basePython @baseArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
& $venvPython -m pip install -r requirements.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Package installation failed.' }
& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Package dependency check failed.' }
if (-not $SkipModel) {
    & $venvPython -X utf8 main.py --download-model
    if ($LASTEXITCODE -ne 0) { throw 'Model download failed.' }
}
& $venvPython -X utf8 main.py --check-env
if ($LASTEXITCODE -ne 0) { throw 'Environment check failed.' }
Write-Host 'Setup complete. Run: .\run.ps1 -Mode demo'
