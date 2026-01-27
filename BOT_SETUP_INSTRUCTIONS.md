# Telegram Break Time Tracker Bot - Setup Instructions

## Features
- **E1/E2** - 🍽️ Eating break tracking
- **C1/C2** - 🚻 Comfort room break tracking
- **S1/S2** - 🚬 Smoke break tracking
- **O1/O2** - ⚠️ Other concerns with reason (asks for reason when O1 is clicked)
- **Automatic time tracking** - Calculates duration between OUT and BACK
- **Excel logging** - All breaks logged to `break_time_log.xlsx`
- **Daily summary** - View break counts and total time

## Setup Steps

### 1. Install Python Package
```bash
pip install python-telegram-bot
```

Or use the requirements file:
```bash
pip install -r bot_requirements.txt
```

### 2. Create Your Bot on Telegram

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow the instructions:
   - Choose a name for your bot (e.g., "Break Time Tracker")
   - Choose a username (e.g., "breaktime_tracker_bot")
4. Copy the **bot token** you receive (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 3. Configure the Bot

Open `breaktime_tracker_bot.py` and replace this line:
```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
```

With your actual token:
```python
BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
```

### 4. Run the Bot

```bash
python breaktime_tracker_bot.py
```

You should see:
```
Initializing Break Time Tracker Bot...
Log file: C:/Users/us/Desktop/break_time_log.xlsx
Bot is running... Press Ctrl+C to stop
```

### 5. Use the Bot

1. Open Telegram and search for your bot username
2. Click **Start** or send `/start`
3. You'll see buttons for all break types
4. Click to track your breaks!

## How It Works

### Break Codes
- **E1** - Going out to eat
- **E2** - Back from eating
- **C1** - Going to comfort room
- **C2** - Back from comfort room
- **S1** - Going for smoke break
- **S2** - Back from smoke break
- **O1** - Going out for other concern (will ask for reason)
- **O2** - Back from other concern

### Special Features

1. **Reason for O1**: When you click "Other Out (O1)", the bot will ask you to type the reason
2. **Active Break Warning**: If you try to start a new break while one is active, you'll get a warning
3. **Duration Calculation**: Automatically calculates how long each break took
4. **Daily Summary**: Click "My Break Summary" to see today's breaks

### Commands
- `/start` - Show welcome message and buttons
- `/menu` - Show buttons again

## Log File

All breaks are saved to: `C:/Users/us/Desktop/break_time_log.xlsx`

Columns:
- User ID
- Username
- Full Name
- Break Type
- Action (OUT/BACK)
- Timestamp
- Duration (minutes) - only for BACK actions
- Reason - only for Other Concern breaks

## Example Usage

1. Click "🍽️ Eat Out (E1)" at 12:00 PM
2. Bot confirms and logs start time
3. Click "✅ Eat Back (E2)" at 12:30 PM
4. Bot shows: "Duration: 30 minutes"

## Troubleshooting

### Bot doesn't respond
- Check if bot token is correct
- Make sure bot is running (check terminal)
- Verify internet connection

### "Failed to resolve env" in VS Code
- Already fixed! Use the Python interpreter at: `C:\Program Files\Python313\python.exe`
- Run from terminal: `python breaktime_tracker_bot.py`

### Excel file not created
- Check if Desktop folder exists
- Verify write permissions
- Look for error messages in terminal

## Running 24/7

To keep the bot running continuously:

**Option 1: Keep terminal open**
- Just keep the terminal window open

**Option 2: Background process (Windows)**
```bash
start /min python breaktime_tracker_bot.py
```

**Option 3: Use PM2 (if installed)**
```bash
pm2 start breaktime_tracker_bot.py --name breaktime-bot
```

## Viewing Logs

Open `break_time_log.xlsx` with Excel to view and analyze break patterns.

## Need Help?

Check the terminal for error messages. Most issues are logged there.