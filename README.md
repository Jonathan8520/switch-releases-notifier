# Switch Releases Notifier

Sends Discord notifications when new Nintendo Switch game releases are detected.

## Setup

1. Fork this repository
2. Add a Discord webhook secret named `Releases_new_switch_TOKEN` in your repository settings
3. The workflow runs every 15 minutes and notifies your Discord channel of new releases

## Configuration

The workflow is defined in `.github/workflows/releases_new_switch.yml`.

## Local development

```bash
pip install -r requirements.txt
export DISCORD_WEBHOOK="your_webhook_url"
python main.py
```
