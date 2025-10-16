@echo off
echo ================================
echo  Mutual Funds Agent - Full Stack
echo ================================
echo.

echo Installing Python dependencies...
pip install fastapi uvicorn websockets python-multipart aiohttp

echo.
echo Installing Node.js dependencies...
cd frontend
call npm install

echo.
echo ================================
echo  Starting Services
echo ================================

echo.
echo Starting FastAPI backend server...
cd ..
start "MF Agent API" cmd /k "python api_server.py"

echo Waiting for backend to start...
timeout /t 5 > nul

echo.
echo Starting React frontend...
cd frontend
start "MF Agent Frontend" cmd /k "npm run dev"

echo.
echo ================================
echo  Services Started Successfully!
echo ================================
echo.
echo Backend API: http://localhost:8000
echo Frontend UI: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to exit...
pause > nul
