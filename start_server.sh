#!/bin/bash

# CogView4 API Server Startup Script

set -e

echo "🚀 Starting CogView4 Image Generation API Server..."
echo "=================================================="

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed or not in PATH"
    exit 1
fi



# Install dependencies if requirements.txt exists
# if [ -f "requirements.txt" ]; then
#     echo "📋 Installing dependencies..."
#     pip install -r requirements.txt
# else
#     echo "⚠️  requirements.txt not found. Installing basic dependencies..."
#     pip install fastapi uvicorn torch torchvision transformers diffusers pillow numpy pydantic accelerate
# fi

# Set environment variables
export COGVIEW4_HOST=${COGVIEW4_HOST:-"0.0.0.0"}
export COGVIEW4_PORT=${COGVIEW4_PORT:-"8000"}
export COGVIEW4_DEVICE=${COGVIEW4_DEVICE:-"cuda"}

# Check CUDA availability
python -c "import torch; print(f'🔥 CUDA Available: {torch.cuda.is_available()}')" 2>/dev/null || {
    echo "⚠️  PyTorch not installed yet, will be installed with requirements"
}

echo ""
echo "🌟 Configuration:"
echo "   Host: $COGVIEW4_HOST"
echo "   Port: $COGVIEW4_PORT"
echo "   Device: $COGVIEW4_DEVICE"
echo ""

# Check if server file exists
if [ ! -f "cogview4_api_server.py" ]; then
    echo "❌ cogview4_api_server.py not found in current directory"
    echo "   Please ensure all files are in the correct location"
    exit 1
fi

echo "🎯 Starting server..."
echo "   API will be available at: http://localhost:$COGVIEW4_PORT"
echo "   Web client: Open web_client.html in your browser"
echo "   Health check: curl http://localhost:$COGVIEW4_PORT/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================="

# Start the server
python cogview4_api_server.py

echo ""
echo "👋 Server stopped" 