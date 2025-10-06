#!/bin/bash

# ATC Kinematics Engine Startup Script

set -e

echo "🚀 Starting ATC Kinematics Engine - Phase A"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your database credentials before running"
    exit 1
fi

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found"
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate venv
echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "✅ Setup complete"
echo ""
echo "Starting engine..."
echo "Press Ctrl+C to stop"
echo ""

# Run the engine
python -m engine.core_engine "$@"

