#!/bin/bash

echo "🔧 Fixing static/images permissions for Docker container..."

# Stop the container if running
echo "Stopping container..."
docker stop aigc-image 2>/dev/null || echo "Container not running"

# Create directory if it doesn't exist
echo "Creating static/images directory..."
mkdir -p static/images

# Set permissions
echo "Setting permissions (777 for Docker compatibility)..."
chmod 777 static/images

# Check if directory is writable
echo "Testing write permissions..."
touch static/images/test-write.tmp && rm static/images/test-write.tmp
if [ $? -eq 0 ]; then
    echo "✅ Write permissions OK"
else
    echo "❌ Write permissions still not working"
    echo "Trying with sudo..."
    sudo chmod 777 static/images
fi

# Start container again
echo "Starting container..."
docker start aigc-image

# Check container status
sleep 3
if docker ps | grep -q aigc-image; then
    echo "✅ Container is running"
    echo "📋 You can now test image generation and publishing to gallery"
else
    echo "❌ Container failed to start"
    echo "Check logs with: docker logs aigc-image"
fi

echo "🎉 Permission fix complete!"
echo ""
echo "💡 If you still have issues, try:"
echo "   1. docker exec aigc-image ls -la /app/static/images"
echo "   2. docker logs aigc-image" 