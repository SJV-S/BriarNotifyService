#!/bin/bash

# Briar Notify Service - Host Installation Script
# Installs the service directly on the host system

set -e

# Parse command line arguments
VERBOSE=false
if [[ "$1" == "-v" || "$1" == "--verbose" ]]; then
    VERBOSE=true
fi

# Build JAR using the dedicated build script
build_briar_jar_for_arch() {
    local arch="$1"
    local build_script="$INSTALL_DIR/briar_headless/jar-builds/build-jar.sh"
    
    if [[ "$VERBOSE" == "true" ]]; then
        echo "Building Briar JAR for $arch using build script..."
        # Execute the build script with the specified architecture (verbose)
        "$build_script" "$arch"
        return $?
    else
        echo "Building Briar Headless from source..."
        echo "   Please be patient - this may take several minutes..."
        # Execute the build script with the specified architecture (quiet)
        if ! "$build_script" "$arch" >/dev/null 2>&1; then
            echo "Build failed. Rerun with -v flag for detailed output."
            return 1
        fi
        return 0
    fi
}

INSTALL_DIR="/opt/briar-notify"

echo "=== Briar Notify Service - Host Installer ==="
echo ""
echo "Installation Overview"
echo "=============================================="
echo "  - System dependencies (python3, curl, etc.)"
echo "  - JDK 17 (bundled with installation)"
echo "  - Python virtual environment & dependencies"
echo "  - Briar Headless (built from source - may take a few minutes)"
echo "  - systemd integration (if you want, permission will be requested)"
echo ""
echo "Installation Location: $INSTALL_DIR"
if [[ "$VERBOSE" == "true" ]]; then
    echo "   (Verbose mode enabled)"
fi
echo ""

# Check for sudo access (allow password prompt)
if ! sudo true; then
    echo "This script requires sudo access to install to /opt/"
    exit 1
fi

# Detect OS and set package manager
if command -v apt >/dev/null 2>&1; then
    PKG_MGR="apt"
elif command -v dnf >/dev/null 2>&1; then
    PKG_MGR="dnf"
elif command -v yum >/dev/null 2>&1; then
    PKG_MGR="yum"
else
    echo "❌ Unsupported package manager. Please install manually: python3, python3-venv, curl"
    exit 1
fi

echo "Java Setup: Bundling JDK 17 with application"
BUNDLE_JDK=true

# Detect architecture for JAR selection
JAR_ARCH="amd64"
case $(uname -m) in
    aarch64) JAR_ARCH="arm64" ;;
    armv7l) JAR_ARCH="armv7" ;;
    armv6l) JAR_ARCH="armv6" ;;
    i386|i686) JAR_ARCH="386" ;;
esac

JAR_FILE="briar_headless/jar-builds/jars/briar-headless-${JAR_ARCH}.jar"

# Choose installation method
if [[ -f "$JAR_FILE" ]]; then
    echo ""
    echo "1) Use pre-packaged JAR (fast)"
    echo "2) Build from source (slow, for paranoid users)"
    read -p "Choose (1/2): " -r choice
    if [[ "$choice" == "2" ]]; then
        echo "WARNING: Building from source may take 10+ minutes on weak hardware"
        BUILD_FROM_SOURCE=true
    else
        BUILD_FROM_SOURCE=false
    fi
else
    echo "No pre-packaged JAR for $JAR_ARCH - building from source"
    echo "WARNING: This may take 10+ minutes on weak hardware"
    BUILD_FROM_SOURCE=true
fi

# Install system dependencies
echo ""
echo "Installing system dependencies..."
if [[ "$VERBOSE" == "true" ]]; then
    case $PKG_MGR in
        apt)
            sudo apt update
            sudo apt install -y python3 python3-venv curl
            ;;
        dnf)
            sudo dnf install -y python3 python3-pip curl
            ;;
        yum)
            sudo yum install -y python3 python3-pip curl
            ;;
    esac
else
    case $PKG_MGR in
        apt)
            sudo apt update >/dev/null 2>&1
            sudo apt install -y python3 python3-venv curl >/dev/null 2>&1
            ;;
        dnf)
            sudo dnf install -y python3 python3-pip curl >/dev/null 2>&1
            ;;
        yum)
            sudo yum install -y python3 python3-pip curl >/dev/null 2>&1
            ;;
    esac
fi

# Create installation directory and copy files
echo "Creating installation directory: $INSTALL_DIR"
sudo mkdir -p "$INSTALL_DIR"

echo "Copying application files to $INSTALL_DIR"
sudo cp -r . "$INSTALL_DIR/"

# Set ownership to current user
sudo chown -R "$USER:$USER" "$INSTALL_DIR"

# Download and install JDK 17 (always bundled)
if [[ "$BUNDLE_JDK" == "true" ]]; then
    echo "Setting up JDK 17..."
    
    # Detect architecture
    ARCH=$(uname -m)
    case $ARCH in
        x86_64)
            JDK_ARCH="x64"
            ;;
        aarch64|arm64)
            JDK_ARCH="aarch64"
            ;;
        armv7l|armv7*)
            JDK_ARCH="arm"
            ;;
        armv6l|armv6*)
            JDK_ARCH="arm"
            ;;
        i386|i686)
            JDK_ARCH="x86"
            ;;
        *)
            echo "Unsupported architecture: $ARCH"
            echo "Supported: x86_64, aarch64, arm64, armv7l, armv6l, i386, i686"
            exit 1
            ;;
    esac
    
    # Create architecture-specific JDK directory structure
    JDK_DIR="briar_headless/jdk17/$JDK_ARCH"
    JDK_URL="https://download.java.net/java/GA/jdk17.0.2/dfd4a8d0985749f896bed50d7138ee7f/8/GPL/openjdk-17.0.2_linux-${JDK_ARCH}_bin.tar.gz"
    JDK_FILE="openjdk-17-${JDK_ARCH}.tar.gz"
    
    echo "   Architecture: $ARCH -> $JDK_ARCH"
    echo "   JDK Directory: $JDK_DIR"
    echo "   Downloading from: $JDK_URL"
    
    cd "$INSTALL_DIR"
    
    # Check if JDK already exists
    if [[ -x "$INSTALL_DIR/$JDK_DIR/bin/java" ]]; then
        echo "JDK 17 already installed at $INSTALL_DIR/$JDK_DIR"
    else
        echo "   Downloading JDK for $JDK_ARCH architecture..."
        
        # Create architecture-specific directory
        mkdir -p "$JDK_DIR"
        
        # Download JDK
        if curl -L -o "$JDK_FILE" "$JDK_URL"; then
        echo "   Extracting JDK..."
        tar -xzf "$JDK_FILE" -C "$JDK_DIR" --strip-components=1
        rm "$JDK_FILE"
        
            # Verify installation
            if [[ -x "$INSTALL_DIR/$JDK_DIR/bin/java" ]]; then
                echo "JDK 17 bundled to $INSTALL_DIR/$JDK_DIR"
            else
                echo "JDK extraction failed - java binary not found"
                exit 1
            fi
        else
            echo "Failed to download JDK for architecture $JDK_ARCH"
            echo "   This may indicate the architecture is not supported by OpenJDK 17"
            echo "   Falling back to system Java - choose option 2 when re-running"
            exit 1
        fi
    fi
fi

# Create Python virtual environment
echo "Creating Python virtual environment..."
cd "$INSTALL_DIR"

# Remove any existing venv
if [[ -d "briar_notify/venv" ]]; then
    rm -rf briar_notify/venv
fi

python3 -m venv briar_notify/venv

# Install Python dependencies
echo "Installing Python dependencies..."
if [[ "$VERBOSE" == "true" ]]; then
    if ! ./briar_notify/venv/bin/pip install -r briar_notify/requirements.txt; then
        echo "Failed to install Python dependencies. Check briar_notify/requirements.txt and try again."
        exit 1
    fi
else
    if ! ./briar_notify/venv/bin/pip install -r briar_notify/requirements.txt >/dev/null 2>&1; then
        echo "Failed to install Python dependencies. Check briar_notify/requirements.txt and try again."
        exit 1
    fi
fi

# Handle Briar JAR
echo ""
echo "Setting up Briar JAR..."

if [[ "$BUILD_FROM_SOURCE" == "true" ]]; then
    if ! build_briar_jar_for_arch "$JAR_ARCH"; then
        echo "Failed to build Briar JAR from source"
        exit 1
    fi
else
    echo "Using architecture-specific JAR for $JAR_ARCH"
fi

# Make scripts executable
echo "Making launch scripts executable..."
chmod +x "$INSTALL_DIR/launch.sh"
if [[ -f "$INSTALL_DIR/briar-notify.sh" ]]; then
    chmod +x "$INSTALL_DIR/briar-notify.sh"
fi

# Create global symlink for briar-notify command
echo "Creating global symlink for briar-notify command..."
sudo ln -sf "$INSTALL_DIR/briar-notify.sh" /usr/local/bin/briar-notify

echo ""

# Check if identity exists and ask about creating one
echo "Checking for Briar identity..."
IDENTITY_EXISTS=false
if "$INSTALL_DIR/briar_notify/venv/bin/python" -c "
import sys
from pathlib import Path
sys.path.insert(0, '$INSTALL_DIR/briar_notify')
from internal_service.briar_service import get_identity_name
if not get_identity_name():
    exit(1)
" 2>/dev/null; then
    IDENTITY_EXISTS=true
    echo "✓ Briar identity found"
else
    echo "No Briar identity found."
    echo ""
    read -p "Create a Briar identity now? (y/n): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        read -p "Enter nickname for your Briar identity: " -r NICKNAME
        if [[ -n "$NICKNAME" ]]; then
            echo "Creating identity with nickname: $NICKNAME"
            if "$INSTALL_DIR/briar-notify.sh" create "$NICKNAME"; then
                IDENTITY_EXISTS=true
                echo "✓ Identity created successfully"
            else
                echo "❌ Failed to create identity"
            fi
        else
            echo "❌ No nickname provided, skipping identity creation"
        fi
    fi
fi

echo ""

# Ask about systemd only if identity exists
SYSTEMD_INSTALLED=false
if [[ "$IDENTITY_EXISTS" == "true" ]]; then
    read -p "Install systemd service? (y/n): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        "$INSTALL_DIR/systemd/install-systemd.sh"
        SYSTEMD_INSTALLED=true
    else
        echo "Systemd installation skipped"
    fi
else
    echo "Systemd service installation skipped - no Briar identity found."
    echo ""
    echo "Next steps:"
    echo "1) Create an identity: briar-notify create <nickname>"
    echo "2) Optionally install systemd: $INSTALL_DIR/systemd/install-systemd.sh"
fi

echo ""
echo "=== Installation Complete ==="
echo "=============================================="
echo ""
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "Web Interface:"
echo "  Local:   http://localhost:8010"
echo "  Network: http://$LOCAL_IP:8010"
echo ""
if [[ "$SYSTEMD_INSTALLED" == "true" ]]; then
    echo "Service Management (systemd):"
    echo "  Status:   systemctl status briar-notify"
    echo "  Logs:     journalctl -u briar-notify -f"
    echo ""
    echo "Manual Control (if systemd fails):"
    echo "  Start:    briar-notify start"
    echo "  Stop:     briar-notify stop"
elif [[ "$IDENTITY_EXISTS" == "true" ]]; then
    echo "Manual Service Control:"
    echo "  Start:    briar-notify start"
    echo "  Stop:     briar-notify stop"
fi
echo ""
echo "Important Locations:"
echo "  Install:  $INSTALL_DIR"
echo "  Config:   $INSTALL_DIR/briar_notify/config/"
echo "  Data:     ~/.local/share/briar/"
echo ""
if [[ "$SYSTEMD_INSTALLED" == "true" ]]; then
    echo "The service is now running automatically via systemd."
    echo "Open http://localhost:8010 or http://$LOCAL_IP:8010 in your browser to access GUI"
elif [[ "$IDENTITY_EXISTS" == "true" ]]; then
    echo "To start the service manually, run: briar-notify start"
    echo "Then open http://localhost:8010 or http://$LOCAL_IP:8010 in your browser to access GUI"
fi
echo ""

