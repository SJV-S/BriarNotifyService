#!/bin/bash
set -e

# Build Briar headless JAR for specific architecture or show menu
# Usage: build-jar.sh [architecture]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JARS_DIR="$SCRIPT_DIR/jars"

# Supported architectures and their Gradle tasks
declare -A ARCH_TASKS=(
    ["amd64"]="x86LinuxJar"
    ["arm64"]="aarch64LinuxJar"
    ["armv7"]="armhfLinuxJar"
    ["armv6"]="armhfLinuxJar"
    ["386"]="x86LinuxJar"
)

show_usage() {
    echo "Usage: $0 [architecture]"
    echo ""
    echo "Architectures:"
    local i=1
    for arch in "${!ARCH_TASKS[@]}"; do
        echo "  $i. $arch (${ARCH_TASKS[$arch]})"
        ((i++))
    done
    echo ""
    echo "Examples:"
    echo "  $0 amd64      # Build for amd64"
    echo "  $0            # Show interactive menu"
}

show_menu() {
    echo "Briar JAR Builder - Select Architecture"
    echo "======================================"
    echo "Select architecture to build:"
    echo ""
    
    local arch_array=($(printf '%s\n' "${!ARCH_TASKS[@]}" | sort))
    local i=1
    for arch in "${arch_array[@]}"; do
        echo "  $i. $arch (${ARCH_TASKS[$arch]})"
        ((i++))
    done
    echo "  q. Quit"
    echo ""
    
    while true; do
        read -p "Select option (1-${#arch_array[@]} or q): " -r choice
        
        if [[ "$choice" == "q" || "$choice" == "Q" ]]; then
            echo "Build cancelled."
            exit 0
        fi
        
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#arch_array[@]}" ]; then
            local selected_arch="${arch_array[$((choice-1))]}"
            echo "Selected: $selected_arch"
            echo ""
            build_jar "$selected_arch"
            break
        else
            echo "Invalid choice. Please select 1-${#arch_array[@]} or q."
        fi
    done
}

find_java17() {
    local java17_cmd=""
    
    # Look for Java 17 in common locations
    for java_path in \
        "/usr/lib/jvm/java-17-openjdk" \
        "/usr/lib/jvm/java-17-openjdk-amd64" \
        "/usr/lib/jvm/java-17-openjdk-arm64" \
        "/usr/lib/jvm/openjdk-17" \
        "/opt/jdk-17" \
        "/Library/Java/JavaVirtualMachines/openjdk-17.jdk/Contents/Home"; do
        
        if [[ -d "$java_path" && -x "$java_path/bin/java" ]]; then
            java17_cmd="$java_path/bin/java"
            export JAVA_HOME="$java_path"
            export PATH="$java_path/bin:$PATH"
            break
        fi
    done
    
    if [[ -z "$java17_cmd" ]]; then
        echo "Error: Java 17 not found in standard locations."
        echo ""
        echo "Java 17 is specifically required for building Briar JARs."
        echo "To install Java 17:"
        
        if [[ -f /etc/fedora-release ]]; then
            echo "  sudo dnf install java-17-openjdk java-17-openjdk-devel"
        elif [[ -f /etc/debian_version ]]; then
            echo "  sudo apt install openjdk-17-jdk"
        elif [[ -f /etc/arch-release ]]; then
            echo "  sudo pacman -S jdk17-openjdk"
        else
            echo "  Install OpenJDK 17 for your distribution"
        fi
        
        echo ""
        read -p "Install Java 17 now? (y/N): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_java17
        else
            echo "JAR build cancelled. Install Java 17 to continue."
            exit 1
        fi
    fi
    
    # Verify Java 17
    local java_version=$($java17_cmd -version 2>&1 | head -1 | grep -o '"17[^"]*"' | tr -d '"' | cut -d'.' -f1)
    if [[ "$java_version" != "17" ]]; then
        echo "Error: Found Java version $java_version, but need exactly Java 17"
        exit 1
    fi
    
    echo "Using Java 17: $java17_cmd"
}

install_java17() {
    echo "Installing Java 17..."
    if [[ -f /etc/fedora-release ]]; then
        sudo dnf install -y java-17-openjdk java-17-openjdk-devel
        export JAVA_HOME="/usr/lib/jvm/java-17-openjdk"
    elif [[ -f /etc/debian_version ]]; then
        sudo apt update && sudo apt install -y openjdk-17-jdk
        export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-$(dpkg --print-architecture)"
    elif [[ -f /etc/arch-release ]]; then
        sudo pacman -S --noconfirm jdk17-openjdk
        export JAVA_HOME="/usr/lib/jvm/java-17-openjdk"
    else
        echo "ERROR: Automatic installation not supported for this OS."
        exit 1
    fi
    
    export PATH="$JAVA_HOME/bin:$PATH"
    
    if [[ -x "$JAVA_HOME/bin/java" ]]; then
        echo "✓ Java 17 installed successfully"
    else
        echo "ERROR: Java 17 installation may have failed"
        exit 1
    fi
}

build_jar() {
    local arch="$1"
    local gradle_task="${ARCH_TASKS[$arch]}"
    local jar_file="$JARS_DIR/briar-headless-${arch}.jar"
    
    if [[ -z "$gradle_task" ]]; then
        echo "Error: Unsupported architecture '$arch'"
        echo "Supported: ${!ARCH_TASKS[@]}"
        exit 1
    fi
    
    echo "Building Briar JAR for $arch..."
    echo "Gradle task: $gradle_task"
    echo "Output: $jar_file"
    echo ""
    
    # Find Java 17
    find_java17
    
    # Check if git is available
    if ! command -v git &>/dev/null; then
        echo "Error: git not found. Please install git."
        exit 1
    fi
    
    # Create jars directory
    mkdir -p "$JARS_DIR"
    
    # Clone Briar repository
    local temp_dir=$(mktemp -d)
    echo "Cloning Briar repository to $temp_dir..."
    git clone --depth=1 https://github.com/briar/briar.git "$temp_dir/briar"
    
    cd "$temp_dir/briar"
    
    echo ""
    echo "Building JAR for $arch..."
    
    # Build the JAR with memory limits
    export GRADLE_OPTS="-Xmx1g -XX:MaxMetaspaceSize=512m"
    export JAVA_OPTS="-Xmx1g"
    
    ./gradlew --no-daemon --configure-on-demand --max-workers=1 briar-headless:${gradle_task}
    
    # Find and copy the built JAR
    local built_jar=$(find . -name "briar-headless-linux-*.jar" | head -1)
    if [[ -f "$built_jar" ]]; then
        cp "$built_jar" "$jar_file"
        echo "✓ $arch JAR saved to: $jar_file"
        
        # Show file size
        local size=$(du -h "$jar_file" | cut -f1)
        echo "  Size: $size"
        echo ""
        echo "JAR build complete!"
    else
        echo "✗ Failed to build $arch JAR"
        exit 1
    fi
    
    # Cleanup
    cd "$SCRIPT_DIR"
    rm -rf "$temp_dir"
}

# Main logic
if [[ $# -eq 0 ]]; then
    # No arguments - show menu
    show_menu
elif [[ $# -eq 1 ]]; then
    # One argument - build specific architecture
    arch="$1"
    if [[ "$arch" == "-h" || "$arch" == "--help" ]]; then
        show_usage
        exit 0
    fi
    build_jar "$arch"
else
    # Too many arguments
    echo "Error: Too many arguments"
    show_usage
    exit 1
fi