import os
import json
import time
import secrets
import base64
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from internal_service.service_config import BRIAR_NOTIFY_DIR


class SecurePassword:
    def __init__(self, password: str):
        self._data = bytearray(password.encode('utf-8'))
        self._last_access = time.time()
    
    def get_bytes(self) -> bytes:
        self._last_access = time.time()
        return bytes(self._data)
    
    def get_string(self) -> str:
        self._last_access = time.time()
        return self._data.decode('utf-8')
    
    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        return time.time() - self._last_access > timeout_seconds
    
    def clear(self):
        # Zero out the bytearray
        for i in range(len(self._data)):
            self._data[i] = 0
        self._data.clear()


class PasswordManager:
    def __init__(self):
        self._secure_password: Optional[SecurePassword] = None
        self._session_timeout = None  # No timeout for always-on server
        # Use user accessible directory for now (can be moved to system location later with proper setup)
        self.system_password_file = BRIAR_NOTIFY_DIR / "briar-password"
    
    def generate_secure_password(self) -> str:
        """Generate cryptographically secure password for Briar identity.
        
        Returns:
            str: 32-byte (256-bit entropy) URL-safe base64 encoded password
        """
        return secrets.token_urlsafe(32)
    
    def save_system_password(self, password: str, identity_name: str = "identity") -> bool:
        """Save password to secure system location.
        
        Args:
            password: The password to save
            identity_name: Name of the identity (for logging/tracking)
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Ensure directory exists with proper permissions
            self.system_password_file.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
            
            # Write password to file with restrictive permissions
            # Using umask to ensure file is created with 600 permissions
            original_umask = os.umask(0o077)  # Only owner can read/write
            try:
                with open(self.system_password_file, 'w') as f:
                    f.write(password)
            finally:
                os.umask(original_umask)
            
            # Ensure 600 permissions for current user (skip sudo for now)
            os.chmod(self.system_password_file, 0o600)
            
            return True
            
        except Exception as e:
            print(f"Failed to save system password: {e}")
            return False
    
    def load_system_password(self) -> Optional[str]:
        """Load password from system location.
        
        Returns:
            str: Password if found and readable, None otherwise
        """
        try:
            if self.system_password_file.exists():
                with open(self.system_password_file, 'r') as f:
                    return f.read().strip()
            return None
        except Exception as e:
            print(f"Failed to load system password: {e}")
            return None
    
    def system_password_exists(self) -> bool:
        """Check if system password file exists and is readable.
        
        Returns:
            bool: True if password file exists and can be read
        """
        try:
            return self.system_password_file.exists() and self.system_password_file.is_file()
        except Exception:
            return False
    
    def set_identity_password(self, password: str):
        """Set password in memory for current session.
        
        Args:
            password: Password to store in memory
        """
        # Clear existing password first
        self.clear_identity_password()
        self._secure_password = SecurePassword(password)
    
    def clear_identity_password(self):
        """Clear password from memory."""
        if self._secure_password:
            self._secure_password.clear()
            self._secure_password = None
    
    def _get_password(self) -> Optional[str]:
        """Get password from memory.
        
        Returns:
            str: Password if set, None otherwise
        """
        if not self._secure_password:
            return None
        # No timeout check for always-on server
        return self._secure_password.get_string()
    
    @property
    def identity_password(self) -> Optional[str]:
        """Current identity password from memory.
        
        Returns:
            str: Password if available, None otherwise
        """
        return self._get_password()
    
    def load_password_into_memory(self) -> bool:
        """Load system password into memory for immediate use.
        
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        system_password = self.load_system_password()
        if system_password:
            self.set_identity_password(system_password)
            return True
        return False
    
    def create_auto_generated_identity_password(self, identity_name: str = "identity") -> Optional[str]:
        """Generate new password and save it to system location.
        
        Args:
            identity_name: Name for the identity
            
        Returns:
            str: Generated password if successful, None if failed
        """
        # Generate secure password
        auto_password = self.generate_secure_password()
        
        # Save to system location
        if self.save_system_password(auto_password, identity_name):
            # Also set in memory for immediate use
            self.set_identity_password(auto_password)
            return auto_password
        
        return None
    
    # === FILE OPERATIONS (plaintext only) ===
    
    def save_file(self, data: Dict[str, Any], filepath: Path):
        """Save data to file as plaintext JSON.
        
        Args:
            data: Data to save
            filepath: Path to save to
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_file(self, filepath: Path) -> Dict[str, Any]:
        """Load data from plaintext JSON file.
        
        Args:
            filepath: Path to load from
            
        Returns:
            dict: Loaded data, empty dict if file doesn't exist
        """
        if not filepath.exists():
            return {}
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def save_password_verification_hash(self, password: str, identity_name: str = "identity"):
        """Save PBKDF2 hash for password verification.
        
        Args:
            password: Password to hash
            identity_name: Identity name for the hash file
        """
        # Generate random salt for verification hash
        salt = os.urandom(16)
        
        # Create PBKDF2 hash with same parameters as derive_key_from_password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        password_hash = kdf.derive(password.encode())
        
        # Save hash and salt to file using identity name
        hash_file = BRIAR_NOTIFY_DIR / f'{identity_name}.hash'
        hash_file.parent.mkdir(parents=True, exist_ok=True)
        
        hash_data = {
            'hash': base64.b64encode(password_hash).decode(),
            'salt': base64.b64encode(salt).decode()
        }
        
        with open(hash_file, 'w') as f:
            json.dump(hash_data, f)
    
    def verify_password(self, password: str) -> bool:
        """Verify password against stored PBKDF2 hash.
        
        Args:
            password: Password to verify
            
        Returns:
            bool: True if password matches hash
        """
        # Find any .hash file in the directory
        hash_files = list(BRIAR_NOTIFY_DIR.glob('*.hash'))
        if not hash_files:
            return False
        
        # Use the first .hash file found
        hash_file = hash_files[0]
        
        try:
            with open(hash_file, 'r') as f:
                hash_data = json.load(f)
            
            stored_hash = base64.b64decode(hash_data['hash'])
            salt = base64.b64decode(hash_data['salt'])
            
            # Verify password using same PBKDF2 parameters
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=480000,
            )
            
            try:
                kdf.verify(password.encode(), stored_hash)
                return True
            except Exception:
                return False
                
        except Exception:
            return False
    
    def has_password_verification_hash(self) -> bool:
        """Check if password verification hash exists.
        
        Returns:
            bool: True if hash file exists
        """
        hash_files = list(BRIAR_NOTIFY_DIR.glob('*.hash'))
        return len(hash_files) > 0


# Global instance
password_manager = PasswordManager()