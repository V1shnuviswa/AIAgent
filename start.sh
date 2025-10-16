#!/bin/bash

echo "================================"
echo " Mutual Funds Agent - Full Stack"
echo "================================"
echo ""

echo "Installing Python dependencies..."
pip install fastapi uvicorn websockets python-multipart aiohttp

echo ""
echo "Installing Node.js dependencies..."
cd frontend
npm install

echo ""
echo "================================"
echo " Starting Services"
echo "================================"

echo ""
echo "Starting FastAPI backend server..."
cd ..
python api_server.py &
BACKEND_PID=$!

echo "Waiting for backend to start..."
sleep 5

echo ""
echo "Starting React frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "================================"
echo " Services Started Successfully!"
echo "================================"
echo ""
echo "Backend API: http://localhost:8000"
echo "Frontend UI: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for user interrupt
trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
