@echo off
echo Starting IPAM Backend (FastAPI)...
start /b "" ".\backend\venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

echo Starting IPAM Frontend (Vite/React)...
set PATH=%~dp0node_env\node-v22.14.0-win-x64;%PATH%
cd frontend
start /b "" npm.cmd run dev

echo.
echo Application is starting!
echo Backend will be available at: http://localhost:8000
echo Frontend will be available at: http://localhost:5173
echo.
echo Press Ctrl+C to stop the servers.
pause
