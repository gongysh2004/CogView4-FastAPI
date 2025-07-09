#!/bin/bash

# Build script to replace environment variables
# Usage: ./build.sh [environment]

ENVIRONMENT=${1:-development}

# Set API URLs based on environment
case $ENVIRONMENT in
    "production")
        API_BASE_URL="https://api.your-production-domain.com"
        ;;
    "staging")
        API_BASE_URL="https://api-staging.your-domain.com"
        ;;
    "development")
        API_BASE_URL="http://localhost:8000"
        ;;
    "local")
        API_BASE_URL="http://192.168.95.192:8000"
        ;;
    *)
        echo "Unknown environment: $ENVIRONMENT"
        exit 1
        ;;
esac

VERSION=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "Building for environment: $ENVIRONMENT"
echo "API URL: $API_BASE_URL"
echo "Version: $VERSION"

# Copy template and replace variables
cp static/build-config.js static/build-config.tmp.js

# Replace placeholders
sed -i.bak "s|{{API_BASE_URL}}|$API_BASE_URL|g" static/build-config.tmp.js
sed -i.bak "s|{{ENVIRONMENT}}|$ENVIRONMENT|g" static/build-config.tmp.js
sed -i.bak "s|{{VERSION}}|$VERSION|g" static/build-config.tmp.js

# Move the processed file
mv static/build-config.tmp.js static/build-config.js
rm static/build-config.js.bak

echo "Build complete!"
echo "Config file updated with:"
echo "  API_BASE_URL: $API_BASE_URL"
echo "  ENVIRONMENT: $ENVIRONMENT"
echo "  VERSION: $VERSION" 