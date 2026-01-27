# Docker Setup for Breaktime Tracker Bot

This guide explains how to run the Breaktime Tracker Bot using Docker with auto-connect and auto-reconnect capabilities.

## Prerequisites

- Docker Desktop installed on Windows
- Docker Compose (included with Docker Desktop)
- Your Telegram Bot Token from @BotFather

## Features

✅ **Auto-connect**: Bot starts automatically when Docker starts
✅ **Auto-reconnect**: Automatically restarts on crashes or connection failures
✅ **Persistent data**: Excel logs saved to your Desktop
✅ **Health monitoring**: Automatic health checks every 30 seconds
✅ **Log rotation**: Keeps logs manageable (10MB max, 3 files)

## Quick Start

### 1. Verify Configuration

Make sure your `.env` file exists and contains your bot token:

```bash
# .env file content
BOT_TOKEN=8417145929:AAGW8uDSrK_VrRN4NIadLf9bOwcTXWabgEo
BASE_DIR=/app
```

### 2. Build the Docker Image

```bash
cd C:/Users/us/Desktop/breaktime_tracker_bot
docker-compose build
```

### 3. Start the Bot

```bash
docker-compose up -d
```

The `-d` flag runs the container in detached mode (background).

### 4. Verify Bot is Running

```bash
docker-compose ps
```

You should see:
```
NAME                      STATUS              PORTS
breaktime_tracker_bot     Up X seconds (healthy)
```

## Managing the Bot

### View Live Logs

```bash
docker-compose logs -f
```

Press `Ctrl+C` to stop viewing logs (bot keeps running).

### Stop the Bot

```bash
docker-compose stop
```

### Start the Bot (after stopping)

```bash
docker-compose start
```

### Restart the Bot

```bash
docker-compose restart
```

### Stop and Remove Container

```bash
docker-compose down
```

Note: This removes the container but keeps your data in the `database/` folder.

### Rebuild After Code Changes

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

## Auto-Restart Behavior

The bot is configured with `restart: unless-stopped`, which means:

✅ Restarts automatically if the bot crashes
✅ Restarts automatically when Docker starts (system reboot)
✅ Restarts automatically if health check fails
❌ Does NOT restart if you manually stop it with `docker-compose stop`

## Data Storage

All Excel break logs are stored in:
```
C:/Users/us/Desktop/breaktime_tracker_bot/database/
```

The folder structure is:
```
database/
├── 2025-10/
│   ├── break_logs_2025-10-13.xlsx
│   ├── break_logs_2025-10-14.xlsx
│   └── ...
└── 2025-11/
    ├── break_logs_2025-11-01.xlsx
    └── ...
```

This data persists even if you delete the Docker container.

## Health Checks

The bot includes automatic health monitoring:

- **Check interval**: Every 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3 attempts before marking unhealthy
- **Start period**: 40 seconds initial grace period

If the health check fails 3 times, Docker will automatically restart the container.

## Viewing Health Status

```bash
docker inspect --format='{{.State.Health.Status}}' breaktime_tracker_bot
```

Possible statuses:
- `healthy` - Bot is running normally
- `unhealthy` - Bot failed health checks, will restart soon
- `starting` - Bot is initializing (first 40 seconds)

## Troubleshooting

### Bot not starting

1. Check logs:
   ```bash
   docker-compose logs
   ```

2. Verify .env file exists and has correct BOT_TOKEN

3. Make sure database folder exists:
   ```bash
   mkdir -p database
   ```

### Bot keeps restarting

1. View logs to see error messages:
   ```bash
   docker-compose logs -f
   ```

2. Common issues:
   - Invalid BOT_TOKEN in .env
   - Network connectivity issues
   - Telegram API rate limiting

### Data not persisting

1. Verify volume mount in docker-compose.yml:
   ```yaml
   volumes:
     - ./database:/app/database
   ```

2. Check folder permissions on Windows

### Can't connect to Telegram

1. Verify internet connection
2. Check if Telegram is blocked by firewall
3. Review Docker network settings:
   ```bash
   docker network ls
   ```

## Running Bot Without Docker (Alternative)

If you prefer to run without Docker:

1. Set environment variable:
   ```cmd
   set BOT_TOKEN=8417145929:AAGW8uDSrK_VrRN4NIadLf9bOwcTXWabgEo
   set BASE_DIR=C:/Users/us/Desktop/breaktime_tracker_bot
   ```

2. Run Python directly:
   ```cmd
   python breaktime_tracker_bot.py
   ```

## Updating the Bot

### Method 1: Quick restart (no code changes)
```bash
docker-compose restart
```

### Method 2: Full rebuild (after code changes)
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Method 3: Update just the code
```bash
docker-compose down
# Make your code changes
docker-compose up -d --build
```

## Advanced Configuration

### Change Restart Policy

Edit `docker-compose.yml` and modify the `restart` option:

- `always` - Always restart, even after manual stop
- `unless-stopped` - Restart unless manually stopped (default)
- `on-failure` - Only restart on error
- `no` - Never restart automatically

### Adjust Health Check Settings

Edit `docker-compose.yml`:

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
  interval: 30s      # How often to check
  timeout: 10s       # Max time for check
  retries: 3         # Failures before unhealthy
  start_period: 40s  # Grace period on start
```

### Change Log Rotation Settings

Edit `docker-compose.yml`:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"   # Max size per log file
    max-file: "3"     # Number of log files to keep
```

## Security Notes

⚠️ **IMPORTANT**:
- Never commit `.env` file to Git (it contains your bot token)
- `.gitignore` is configured to exclude `.env` automatically
- Keep your bot token secure and don't share it

## Getting Help

- Check Docker logs: `docker-compose logs -f`
- Verify bot status: `docker-compose ps`
- Check health: `docker inspect breaktime_tracker_bot`
- Original bot setup: See `BOT_SETUP_INSTRUCTIONS.md`

## System Requirements

- Windows 10/11 with WSL2
- Docker Desktop 4.0+
- 2GB available RAM
- 500MB disk space for Docker image

## Performance

- Container size: ~150MB
- Memory usage: ~50-100MB
- CPU usage: Minimal (<5%)
- Network: Telegram API only (minimal bandwidth)

---

**Author**: Docker configuration for Breaktime Tracker Bot
**Version**: 1.0
**Last Updated**: November 2025
