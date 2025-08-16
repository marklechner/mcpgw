#!/bin/bash

# MCP Gateway Startup Script

echo "🚀 Starting MCP Gateway"
echo "======================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Start the gateway
echo "🌐 Starting MCP Gateway on http://localhost:8000"
echo "   Press Ctrl+C to stop"
echo ""

python main.py
