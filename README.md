# Linux Update Checker

Checks for pending system updates (apt / dnf) and sends a Discord notification via a webhook URL.

## Setup & Installation

This project uses uv for ultra-fast Python package and project management.

1. Install uv (if you haven't already):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
2. Clone and Sync:
```bash
git clone https://gitlab.com/majramos/bank-to-actualbudget.git
cd bank-to-actualbudget
uv sync
```

## Usage
```bash
python3 linux_update_checker --webhook <DISCORD_WEBHOOK_URL>
```

Or set the environment variable DISCORD_WEBHOOK_URL and run without flags.

### Cron setup example
Cron example (every day at 08:00)
0 8 * * * /usr/bin/python3 linux_update_checker
