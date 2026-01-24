# Switch Releases Notifier

Get Discord notifications when new Nintendo Switch releases appear on [srrDB](https://www.srrdb.com/).

![Discord notification example](https://img.shields.io/badge/Discord-Notifications-5865F2?logo=discord&logoColor=white)

## Features

- Monitors srrDB every 15 minutes for new Switch releases
- Sends rich Discord embeds with:
  - Release name, type (Base/Update/DLC), and size
  - TitleID with link to Nintendo eShop
  - Game cover image from Tinfoil
- Tracks already-notified releases to avoid duplicates
- Runs automatically via GitHub Actions (free)

## Setup

### 1. Fork this repository

Click the **Fork** button at the top right of this page.

### 2. Create a Discord webhook

1. In your Discord server, go to **Server Settings** → **Integrations** → **Webhooks**
2. Click **New Webhook**
3. Choose the channel where you want notifications
4. Copy the webhook URL

### 3. Add the webhook as a GitHub secret

1. In your forked repo, go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `Releases_new_switch_TOKEN`
4. Value: paste your Discord webhook URL
5. Click **Add secret**

### 4. Enable GitHub Actions

1. Go to the **Actions** tab in your forked repo
2. Click **I understand my workflows, go ahead and enable them**

That's it! The workflow will run every 15 minutes and notify you of new releases.

## How it works

```
srrDB API  →  Parse NFO for TitleID  →  Discord webhook
    ↓                                         ↓
 New NSW      Game cover from Tinfoil    Rich embed with
 releases     eShop link                 all release info
```

1. Queries [srrDB API](https://api.srrdb.com/v1/search/category:nsw/order:date-desc) for latest Switch releases
2. Downloads and parses NFO files to extract TitleID
3. Masks TitleID to get the base game ID (for cover images and eShop links)
4. Sends a Discord embed with all release information
5. Saves seen releases to `seen_releases.json` to avoid duplicates

## Manual trigger

You can manually trigger the workflow:
1. Go to **Actions** → **Notifier for New Switch Releases**
2. Click **Run workflow**

## Local development

```bash
pip install requests
export DISCORD_WEBHOOK="your_webhook_url"
python main.py
```

## License

MIT
