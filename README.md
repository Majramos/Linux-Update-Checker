# Linux Update Checker

<div align="center">

![Python Badge](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff&style=flat)
![Gitlab Pipeline Status](https://gitlab.com/majramos/linux-update-checke/badges/main/pipeline.svg)
![Gitlab Release](https://gitlab.com/majramos/linux-update-checker/-/badges/release.svg)
![Gitlab Coverage](https://gitlab.com/majramos/linux-update-checker/badges/main/coverage.svg)

</div>


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
python linux_update_checker --webhook <DISCORD_WEBHOOK_URL>
```
or set the environment variable `LUC_DISCORD_WEBHOOK_URL and run without flags.
```bash
uv run --env-file .env linux-update-checker
```

### Cron setup example
check if cron service is running
```bash
service cron status
```

if it shows “cron is not running”
```bash
service cron start
```

open crontab configuation file
```bash
crontab -e
```

or scheduling for a different user
```bash
crontab -u <username> -e
```

Cron example (every day at 08:00)
```bash
0 8 * * * /usr/bin/python3 linux_update_checker
```

check for active cron jobs
```bash
crontab -l
```
