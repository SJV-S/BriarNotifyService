
from pathlib import Path
import platform

# Map Python's architecture to (JAR_arch, JDK_arch)
arch_mapping = {
    'x86_64': ('amd64', 'x64'),
    'amd64': ('amd64', 'x64'),
    'aarch64': ('arm64', 'aarch64'),
    'arm64': ('arm64', 'aarch64'),
    'armv7l': ('armv7', 'arm'),
    'armv7': ('armv7', 'arm'),
    'armv6l': ('armv6', 'arm'),
    'armv6': ('armv6', 'arm'),
    'i386': ('386', 'x86'),
    'i686': ('386', 'x86')
}
machine = platform.machine().lower()
jar_arch, jdk_arch = arch_mapping.get(machine, ('amd64', 'x64'))  # Default to amd64/x64

# Application paths
BRIAR_DIR = Path.home() / '.briar'
BRIAR_NOTIFY_DIR = Path.home() / '.briar-notify'

app_dir = Path(__file__).parent.parent.parent
BRIAR_JAR_PATH = str(app_dir / "briar_headless" / "jar-builds" / "jars" / f'briar-headless-{jar_arch}.jar')

# Always use bundled Java
bundled_java = app_dir / 'briar_headless' / 'jdk17' / jdk_arch / 'bin' / 'java'
JAVA_PATH = str(bundled_java)

# Other defaults
DEFAULT_BRIAR_PORT = 7010  # Normal Briar chat app uses 7000
DEFAULT_WEB_UI_PORT = 8010
WS_URL = f"ws://127.0.0.1:{DEFAULT_BRIAR_PORT}/v1/ws"

class BriarAuthManager:
    def __init__(self):
        self.token_path = BRIAR_DIR / 'auth_token'
    
    def get_token(self):
        if not self.token_path.exists():
            return None
        return self.token_path.read_text().strip()
    
    def get_auth_headers(self):
        """Get authorization headers for requests"""
        token = self.get_token()
        if not token:
            return None
        return {'Authorization': f'Bearer {token}'}
    
    def has_token(self):
        return self.token_path.exists()


# Singleton instance
auth_manager = BriarAuthManager()
