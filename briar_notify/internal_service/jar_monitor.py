import time
import threading
from typing import Optional
from internal_service.briar_service import identity_running, start_briar_process, logout_identity, wait_for_briar_ready
from internal_service.password_manager import password_manager


class JarMonitor:
    # Background monitor that keeps the Briar JAR process alive.

    def __init__(self):
        self.check_interval_seconds = 60
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        
    def start_monitoring(self) -> bool:
        # Start the background monitoring thread.
        if self.running:
            return False
            
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="JarMonitor",
            daemon=True
        )
        self.monitor_thread.start()
        return True
        
    def stop_monitoring(self):
        # Stop the background monitoring thread.
        if not self.running:
            return
            
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
    def _monitor_loop(self):
        # Main monitoring loop - runs in background thread.
        while self.running:
            try:
                if not identity_running():
                    self._restart_jar()
            except Exception:
                pass

                
    def _restart_jar(self) -> bool:
        # Restart the JAR process.
        try:
            system_password = password_manager.identity_password
            if not system_password:
                return False
                
            logout_identity()
            time.sleep(2)
            
            proc = start_briar_process(system_password)
            if not proc:
                return False
                
            return wait_for_briar_ready()
                
        except Exception:
            return False


# Global monitor instance
jar_monitor = JarMonitor()
