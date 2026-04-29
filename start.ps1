# Start the IPAM MVP Application (Backend + Frontend)

Write-Host "Starting IPAM Backend (FastAPI)..." -ForegroundColor Green
Start-Process -NoNewWindow -FilePath ".\backend\venv\Scripts\python.exe" -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8000"

Write-Host "Starting IPAM Frontend (Vite/React)..." -ForegroundColor Blue
$env:PATH = "$PSScriptRoot\node_env\node-v22.14.0-win-x64;" + $env:PATH
Set-Location -Path ".\frontend"
Start-Process -NoNewWindow -FilePath "npm.cmd" -ArgumentList "run dev"

Write-Host "`nApplication is starting! `nBackend will be available at: http://localhost:8000 `nFrontend will be available at: http://localhost:5173" -ForegroundColor Yellow
Write-Host "`nPress Ctrl+C to stop the servers." -ForegroundColor Gray

# Keep the window open so the user can see output and stop it with Ctrl+C
Wait-Event
