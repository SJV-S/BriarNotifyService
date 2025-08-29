BRIAR NOTIFY SERVICE - QUICK REFERENCE

== SERVICE COMMANDS ==
sudo systemctl start briar-notify      # Start service
sudo systemctl stop briar-notify       # Stop service
sudo systemctl restart briar-notify    # Restart service
sudo systemctl status briar-notify     # Check status
sudo systemctl enable briar-notify     # Auto-start on boot
sudo systemctl disable briar-notify    # Disable auto-start

== LOG MONITORING ==
sudo journalctl -u briar-notify -f     # Live tail logs
sudo journalctl -u briar-notify -n 50  # Last 50 lines
sudo journalctl -u briar-notify --since "1 hour ago"

== MANUAL START (WITHOUT SYSTEMD) ==
./launch.sh                            # Direct launch script

== SYSTEMD SCRIPTS ==
systemd/briar-notify.service           # Main service definition
systemd/systemd-launch.sh              # Service startup script
systemd/systemd-stop.sh                # Service shutdown script
systemd/install-systemd.sh             # Install systemd service

