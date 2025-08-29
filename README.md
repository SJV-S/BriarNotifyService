# Briar Notify Service

A notification service wrapper for the Briar headless API. Intended to run in the background and allow for integration with other apps using cli one-liners. Comes with a web GUI for managing contacts and basic message scheduling functionality. The goal is a foundation for sovereign and private notifications.

## Quick Start

```bash
# Create identity
briar-notify create alice

# Start service
briar-notify start

# Send notification
briar-notify send "Alert" "Server is down"
```

## Features

- Command-line interface for easy integration
- Web GUI for contact management
- Message scheduling
- Dead man's switch functionality
- Cross-platform support (x86, ARM64)

## Installation

*Installation instructions coming soon*

## Usage

*Detailed usage documentation coming soon*

## Acknowledgments

This project builds upon the [Briar Project](https://briarproject.org/), which provides secure, decentralized messaging capabilities. Briar is developed by the Briar Project team and is licensed under the GNU General Public License v3.0.

Special thanks to the Briar developers for creating the headless API that makes this integration possible.

