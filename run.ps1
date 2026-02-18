# BattWise AI - One-command run
# From battwise-ai folder: .\run.ps1

$root = $PSScriptRoot
$venv = Join-Path $root ".venv"
$py = Join-Path $venv "Scripts\python.exe"

# Free ports 8000 and 8501 if already in use
foreach ($p in @(8000, 8501)) {
    Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
Start-Sleep -Seconds 1

if (-not (Test-Path $py)) {
    Write-Host "Creating venv and installing dependencies..."
    python -m venv $venv
    & $py -m pip install -r (Join-Path $root "requirements.txt") -q
}

$env:PYTHONPATH = $root

Write-Host "Starting backend: http://127.0.0.1:8000"
Start-Process -FilePath $py -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $root

Start-Sleep -Seconds 3
Write-Host "Starting frontend: http://localhost:8501"
& $py -m streamlit run (Join-Path $root "frontend\app.py") --server.port 8501
