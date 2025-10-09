#!/bin/bash

echo "🚁 Starting ATC Radar System..."

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "Port $1 is already in use"
        return 1
    else
        return 0
    fi
}

# Start the radar service (Python Flask)
echo "📍 Starting Radar Service on port 5000..."
cd /Users/nrup/ATC-1/atc-nextjs/radar-service

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Start the radar service in background
python app.py &
RADAR_PID=$!

# Wait a moment for the service to start
sleep 3

# Check if radar service is running
if check_port 5000; then
    echo "❌ Failed to start radar service on port 5000"
    exit 1
else
    echo "✅ Radar service started successfully"
fi

# Start the Next.js application
echo "🚀 Starting Next.js application on port 3000..."
cd /Users/nrup/ATC-1/atc-nextjs

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

# Start Next.js in background
npm run dev &
NEXTJS_PID=$!

# Wait a moment for the service to start
sleep 5

# Check if Next.js is running
if check_port 3000; then
    echo "❌ Failed to start Next.js on port 3000"
    kill $RADAR_PID 2>/dev/null
    exit 1
else
    echo "✅ Next.js application started successfully"
fi

echo ""
echo "🎯 ATC Radar System is now running!"
echo "📍 Radar Map: http://localhost:5000"
echo "🚀 ATC Interface: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both services"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $RADAR_PID 2>/dev/null
    kill $NEXTJS_PID 2>/dev/null
    echo "✅ Services stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Wait for user to stop
wait
