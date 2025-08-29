#!/usr/bin/env python3

import os
import sys
import time
import json
import secrets
import subprocess
import tempfile
from pathlib import Path

# Configuration
BRIAR_CONFIG_DIR = Path.home() / ".briar-notify"
BRIAR_PASSWORD_FILE = BRIAR_CONFIG_DIR / "briar-password"
BRIAR_IDENTITY_FILE = BRIAR_CONFIG_DIR / "identity.json"
BRIAR_DATA_DIR = Path.home() / ".briar"

# Import paths for Briar components
script_dir = Path(__file__).parent.parent.parent  # Go up from briar_notify/external_client/ to project root
if (script_dir / "briar_notify" / "internal_service").exists():
    # We're in development directory
    INSTALL_DIR = script_dir
else:
    # We're in production install
    INSTALL_DIR = Path("/opt/briar-notify")

sys.path.insert(0, str(INSTALL_DIR / "briar_notify"))

from internal_service.service_config import JAVA_PATH, jar_arch
from internal_service.briar_service import get_identity_name

def check_root():
    """No root check needed - using user home directories."""
    pass

def generate_secure_password():
    """Generate cryptographically secure password."""
    return secrets.token_urlsafe(32)

def get_briar_jar_path():
    """Get architecture-specific Briar JAR path."""
    return INSTALL_DIR / "briar_headless" / "jar-builds" / "jars" / f"briar-headless-{jar_arch}.jar"

def create_identity(nickname):
    """Create new Briar identity with auto-generated password."""
    check_root()
    
    print(f"Creating Briar identity: {nickname}")
    
    # Check if identity already exists
    existing_identity = get_identity_name()
    if existing_identity:
        print(f"ERROR: Identity already exists: {existing_identity}")
        print("Delete existing identity first with:")
        print("  briar-notify identity delete")
        sys.exit(1)
    
    # Ensure config directory exists
    BRIAR_CONFIG_DIR.mkdir(exist_ok=True)
    
    # Generate secure password
    password = generate_secure_password()
    print("Generated secure password")
    
    # Clean any existing Briar data
    if BRIAR_DATA_DIR.exists():
        print("Cleaning existing Briar data...")
        subprocess.run(['rm', '-rf', str(BRIAR_DATA_DIR)], check=False)
    
    # Kill any running Briar processes
    print("Stopping any running Briar processes...")
    subprocess.run(['pkill', '-9', '-f', 'briar-headless'], check=False)
    time.sleep(2)
    
    # Prepare identity creation input
    input_data = f"{nickname}\n{password}\n{password}\n"
    
    # Start Briar process for identity creation
    print("Starting Briar identity creation...")
    jar_path = get_briar_jar_path()
    
    if not jar_path.exists():
        print(f"ERROR: Briar JAR not found: {jar_path}")
        sys.exit(1)
    
    if not Path(JAVA_PATH).exists():
        print(f"ERROR: Java not found: {JAVA_PATH}")
        sys.exit(1)
    
    try:
        # Use subprocess with stdin to pass password securely
        process = subprocess.Popen(
            [JAVA_PATH, '-jar', str(jar_path), '--port', '7010'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(INSTALL_DIR)
        )
        
        # Send identity creation data
        process.stdin.write(input_data)
        process.stdin.close()
        
        # Wait for Briar API to be ready (identity creation is asynchronous)
        print("Waiting for Briar API to be ready...")
        api_ready = False
        
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            
            # Check if process is still running
            if process.poll() is not None:
                print(f"Briar process exited with code: {process.returncode}")
                break
                
            # Check if API is responding
            try:
                import requests
                response = requests.get(f'http://localhost:7010/v1/contacts/add/link', timeout=2)
                if response.status_code == 401:  # Expected - no auth token yet, but API is up
                    api_ready = True
                    print(f"Briar API ready after {i+1} seconds")
                    break
                elif response.status_code == 200:
                    api_ready = True
                    print(f"Briar API ready after {i+1} seconds")
                    break
            except:
                pass  # API not ready yet
                
            if i % 5 == 0:
                print(f"Still waiting... ({i+1}/30)")
        
        # Kill the process after identity creation
        # if process.poll() is None:
        #     process.terminate()
        #     time.sleep(2)
        #     if process.poll() is None:
        #         process.kill()
                
        if not api_ready:
            print("WARNING: API did not become ready, but identity may still have been created")
        
        # Save password to user directory
        BRIAR_PASSWORD_FILE.write_text(password)
        os.chmod(BRIAR_PASSWORD_FILE, 0o600)  # -rw-------
        
        # Save identity metadata file  
        BRIAR_IDENTITY_FILE.write_text(json.dumps({
            "nickname": nickname,
            "created": time.time()
        }))
        os.chmod(BRIAR_IDENTITY_FILE, 0o600)  # -rw-------
        
        print(f"Identity '{nickname}' created successfully")
        print(f"Password stored securely in: {BRIAR_PASSWORD_FILE}")
        
        # Kill the temporary JAR process
        print("Stopping temporary Briar process...")
        subprocess.run(['pkill', '-9', '-f', 'briar-headless'], check=False)
        time.sleep(1)
        
        print()
        print("Identity creation complete!")
        print("You can now start the full service with:")
        print("  briar-notify service start")
        
    except Exception as e:
        print(f"ERROR: Failed to create identity: {e}")
        # Kill any temporary JAR process
        subprocess.run(['pkill', '-9', '-f', 'briar-headless'], check=False)
        # Cleanup on failure
        if BRIAR_PASSWORD_FILE.exists():
            BRIAR_PASSWORD_FILE.unlink()
        if BRIAR_IDENTITY_FILE.exists():
            BRIAR_IDENTITY_FILE.unlink()
        sys.exit(1)

def delete_identity():
    """Delete existing Briar identity."""
    check_root()
    
    if not BRIAR_DATA_DIR.exists() and not BRIAR_PASSWORD_FILE.exists():
        print("No identity exists to delete")
        return
    
    # Get identity info
    identity_name = "unknown"
    if BRIAR_IDENTITY_FILE.exists():
        try:
            data = json.loads(BRIAR_IDENTITY_FILE.read_text())
            identity_name = data.get("nickname", "unknown")
        except:
            pass
    
    print(f"Deleting identity: {identity_name}")
    
    # Stop any running processes
    print("Stopping Briar processes...")
    subprocess.run(['pkill', '-9', '-f', 'briar-headless'], check=False)
    time.sleep(2)
    
    # Remove password files
    if BRIAR_PASSWORD_FILE.exists():
        BRIAR_PASSWORD_FILE.unlink()
        print("Removed password file")
    
    if BRIAR_IDENTITY_FILE.exists():
        BRIAR_IDENTITY_FILE.unlink()
        print("Removed identity metadata file")
    
    # Remove Briar data directory
    if BRIAR_DATA_DIR.exists():
        subprocess.run(['rm', '-rf', str(BRIAR_DATA_DIR)], check=False)
        print("Removed Briar data directory")
    
    print("Identity deleted successfully")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  briar-notify identity create [nickname]")
        print("  briar-notify identity delete")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 3:
            # Interactive nickname input
            try:
                nickname = input("Name: ").strip()
                if not nickname:
                    print("ERROR: Nickname cannot be empty")
                    sys.exit(1)
            except KeyboardInterrupt:
                print("\nCancelled")
                sys.exit(1)
        else:
            nickname = sys.argv[2]
        
        create_identity(nickname)
        
    elif command == "delete":
        delete_identity()
        
    else:
        print(f"Unknown command: {command}")
        print("Available commands: create, delete")
        sys.exit(1)

if __name__ == "__main__":
    main()