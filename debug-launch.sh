#!/bin/bash

echo "Setting up debug environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "briar_notify/venv" ]; then
    echo "Creating virtual environment..."
    cd briar_notify
    python -m venv venv
    cd ..
fi

# Activate virtual environment
echo "Activating virtual environment..."
source briar_notify/venv/bin/activate

# Install dependencies if requirements.txt exists
if [ -f "briar_notify/requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -r briar_notify/requirements.txt
fi

# Download and install JDK 17 if missing
ARCH=$(uname -m)
case $ARCH in
    x86_64) JDK_ARCH="x64" ;;
    aarch64|arm64) JDK_ARCH="aarch64" ;;
    armv7l|armv7*) JDK_ARCH="arm" ;;
    armv6l|armv6*) JDK_ARCH="arm" ;;
    i386|i686) JDK_ARCH="x86" ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

JDK_DIR="briar_headless/jdk17/$JDK_ARCH"
JDK_URL="https://download.java.net/java/GA/jdk17.0.2/dfd4a8d0985749f896bed50d7138ee7f/8/GPL/openjdk-17.0.2_linux-${JDK_ARCH}_bin.tar.gz"
JDK_FILE="openjdk-17-${JDK_ARCH}.tar.gz"

if [[ ! -x "$JDK_DIR/bin/java" ]]; then
    echo "JDK not found, downloading for $JDK_ARCH architecture..."
    mkdir -p "$JDK_DIR"
    
    if curl -L -o "$JDK_FILE" "$JDK_URL"; then
        echo "Extracting JDK..."
        tar -xzf "$JDK_FILE" -C "$JDK_DIR" --strip-components=1
        rm "$JDK_FILE"
        echo "JDK installed to $JDK_DIR"
    else
        echo "Failed to download JDK"
        exit 1
    fi
fi

# Kill any existing Flask processes on port 8010
echo "Checking for existing processes on port 8010..."
PID=$(lsof -t -i:8010 2>/dev/null || true)
if [ ! -z "$PID" ]; then
    echo "Killing existing process $PID on port 8010..."
    kill -9 $PID 2>/dev/null || true
    sleep 2
fi

# Start Flask application
echo "Starting Flask debug application..."
cd briar_notify
export PYTHONPATH="."
python web_ui/app.py