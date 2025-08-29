# Briar Notify Service

A notification service wrapper for the Briar headless API. Intended to run in the background and allow for integration with other apps using cli one-liners. Comes with a web GUI for managing contacts and basic message scheduling functionality. The goal is a foundation for sovereign and private notifications without the VPN hassle.

Built with help from Claude Code, but please don't assume that I "vibe coded" the whole thing with little effort. I can read code and this was a lot of work. The backend stuff in particular needed a lot of testing.

Feedback is much appreciated. I'm not a security expert. If the service can be improved or hardened, please let me know.

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [CLI Usage](#cli-usage)
- [Notes](#notes)
- [Acknowledgments](#acknowledgments)

## Features

- Command-line interface for easy integration
- Web GUI for contact management
- Message scheduling
- Dead man's switch functionality
- Cross-platform support (x86, ARM64)

## Installation

Right now, it's just a simple script. Will look into packaging for deb and rpm in the future if there's a need.

```bash
# Clone the repository
git clone https://github.com/SJV-S/BriarNotifyService.git
cd BriarNotifyService

# Run the installer
./install.sh 
```

## CLI Usage

### Basic Commands
```bash
# Setup and control
briar-notify create alice        # Create identity
briar-notify start              # Start service
briar-notify status             # Check status
briar-notify contacts           # List contacts

# Send messages
briar-notify send "Title" "Message"           # Fire-and-forget
briar-notify send -c "Title" "Message"       # With confirmation
```

### Integration Examples
```bash
# System monitoring
briar-notify send "Alert" "Server $(hostname) is down"
briar-notify send "Backup" "$(df -h / | awk 'NR==2{print $5}') disk usage"

# Automation
./script.sh || briar-notify send "Error" "Script failed"
```

## Notes

- Security: The briar password and scheduled messages are stored in plain text. This security trade-off was necessary for systemd integration to ensure reliable uptime. Protect the server! The systemd integration can be declined during install if you don't want it, but then you'll need another way of ensuring reliable uptime.
- Compatibility: Briar headless runs on port 7010 to avoid conflicts with the briar messaging app that uses port 7000. So you can run both at the same time. Contacts are however shared between the two, and you probably want to run this on a headless always-on server instead.

## Acknowledgments

This project builds upon the [Briar Project](https://briarproject.org/). Briar is developed by the Briar Project team and is licensed under the GNU General Public License v3.0. Thank you to the Briar developers for making this integration possible.

