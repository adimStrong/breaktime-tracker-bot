"""
Telegram Break Time Tracker Bot
Tracks employee break times with buttons for different break types
Production-ready with daily database archiving and Excel Online sync
"""
import os
import pandas as pd
from datetime import datetime, timedelta, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Microsoft Excel Online sync (optional)
try:
    from microsoft.excel_handler import sync_break_event, init_excel_handler
    EXCEL_SYNC_AVAILABLE = True
except ImportError:
    EXCEL_SYNC_AVAILABLE = False
    print("[Excel] Microsoft module not found - Excel sync disabled")

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')  # Load from environment variable
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required. Please set it in your .env file.")

# For Docker: Use /app, for local: Use current directory
BASE_DIR = os.getenv('BASE_DIR', '/app')
DATABASE_DIR = os.path.join(BASE_DIR, "database")

# Conversation states
WAITING_FOR_REASON = 1

# Store user break sessions
user_sessions = {}

# Store users waiting to provide reasons
waiting_for_reason_users = {}


def get_daily_log_file():
    """Get the log file path for today's date."""
    today = datetime.now().strftime('%Y-%m-%d')
    year_month = datetime.now().strftime('%Y-%m')

    # Create directory structure: database/YYYY-MM/
    month_dir = os.path.join(DATABASE_DIR, year_month)
    os.makedirs(month_dir, exist_ok=True)

    # File format: break_logs_YYYY-MM-DD.xlsx
    log_file = os.path.join(month_dir, f"break_logs_{today}.xlsx")
    return log_file


def init_database_structure():
    """Initialize the database directory structure."""
    # Create main database directory
    os.makedirs(DATABASE_DIR, exist_ok=True)
    print(f"Database directory: {DATABASE_DIR}")

    # Get today's log file and ensure it exists
    log_file = get_daily_log_file()
    if not os.path.exists(log_file):
        df = pd.DataFrame(columns=['User ID', 'Username', 'Full Name', 'Break Type', 'Action', 'Timestamp', 'Duration (minutes)', 'Reason'])
        df.to_excel(log_file, index=False, engine='openpyxl')
        print(f"Created new daily log file: {log_file}")
    else:
        print(f"Using existing log file: {log_file}")


def log_break_activity(user_id, username, full_name, break_type, action, timestamp, duration=None, reason=None):
    """Log break activity to daily Excel file and sync to Excel Online"""
    log_file = get_daily_log_file()

    # Read existing data
    if os.path.exists(log_file):
        df = pd.read_excel(log_file, engine='openpyxl')
    else:
        df = pd.DataFrame(columns=['User ID', 'Username', 'Full Name', 'Break Type', 'Action', 'Timestamp', 'Duration (minutes)', 'Reason'])

    # Append new row
    new_row = pd.DataFrame([[user_id, username, full_name, break_type, action, timestamp, duration or '', reason or '']],
                          columns=['User ID', 'Username', 'Full Name', 'Break Type', 'Action', 'Timestamp', 'Duration (minutes)', 'Reason'])
    df = pd.concat([df, new_row], ignore_index=True)

    # Save to local Excel file
    df.to_excel(log_file, index=False, engine='openpyxl')

    # Sync to Excel Online (non-blocking)
    if EXCEL_SYNC_AVAILABLE:
        try:
            # Parse timestamp string to datetime for Excel sync
            ts = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            sync_break_event(
                user_id=user_id,
                username=username,
                full_name=full_name,
                break_type=break_type,
                action=action,
                timestamp=ts,
                duration=duration,
                reason=reason
            )
        except Exception as e:
            print(f"[Excel] Sync error (non-blocking): {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with break time buttons"""
    user = update.effective_user

    keyboard = [
        [
            InlineKeyboardButton("🍽️ Eat Out (E1)", callback_data='E1'),
            InlineKeyboardButton("✅ Eat Back (E2)", callback_data='E2')
        ],
        [
            InlineKeyboardButton("🚻 CR Out (C1)", callback_data='C1'),
            InlineKeyboardButton("✅ CR Back (C2)", callback_data='C2')
        ],
        [
            InlineKeyboardButton("🚬 Smoke Out (S1)", callback_data='S1'),
            InlineKeyboardButton("✅ Smoke Back (S2)", callback_data='S2')
        ],
        [
            InlineKeyboardButton("⚠️ Other Out (O1)", callback_data='O1'),
            InlineKeyboardButton("✅ Other Back (O2)", callback_data='O2')
        ],
        [
            InlineKeyboardButton("📊 My Break Summary", callback_data='summary')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_message = (
        f"👋 Welcome {user.first_name}!\n\n"
        "🕐 **Break Time Tracker Bot**\n\n"
        "Track your breaks using the buttons below:\n\n"
        "🍽️ **Eat** - E1 (Out) / E2 (Back)\n"
        "🚻 **Comfort Room** - C1 (Out) / C2 (Back)\n"
        "🚬 **Smoke Break** - S1 (Out) / S2 (Back)\n"
        "⚠️ **Other Concerns** - O1 (Out) / O2 (Back)\n\n"
        "Click a button to log your break time!"
    )

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id
    username = user.username or 'N/A'
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    action_code = query.data
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Store group chat ID if message is from a group
    group_chat_id = None
    if query.message.chat.type in ['group', 'supergroup']:
        group_chat_id = query.message.chat.id

    # Handle summary request
    if action_code == 'summary':
        await show_summary(query, user_id, username, full_name)
        return ConversationHandler.END

    break_types = {
        'E': '🍽️ Eating',
        'C': '🚻 Comfort Room',
        'S': '🚬 Smoke Break',
        'O': '⚠️ Other Concern'
    }

    break_type_code = action_code[0]
    action_type = action_code[1]
    break_type = break_types.get(break_type_code, 'Unknown')

    active_session = user_sessions.get(user_id)
    is_active = active_session and active_session.get('active')

    # Handle "OUT" actions (E1, C1, S1, O1)
    if action_type == '1':
        if is_active:
            await query.message.reply_text(
                f"""⚠️ **Warning, {full_name}!**

You still have an active break: {active_session['break_type']}

Please clock back in first before starting a new break!""",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        if action_code == 'O1':
            context.user_data['break_type'] = break_type
            context.user_data['start_time'] = timestamp
            context.user_data['group_chat_id'] = group_chat_id
            await query.message.reply_text(
                f"""⚠️ **Other Concern - Out, {full_name}**

🕐 Time: {timestamp}

Please type the reason for your break:""",
                parse_mode='Markdown'
            )
            return WAITING_FOR_REASON

        session_data = {
            'break_type': break_type,
            'start_time': timestamp,
            'active': True,
            'full_name': full_name,
            'group_chat_id': group_chat_id
        }
        if break_type_code in ['E', 'S']:
            session_data['reminder_sent'] = False
        user_sessions[user_id] = session_data

        log_break_activity(user_id, username, full_name, break_type, 'OUT', timestamp)

        await query.message.reply_text(
            f"""✅ **{full_name}** - Break Started

Type: {break_type}
🕐 Time Out: {timestamp}

Don't forget to clock back in when you return!""",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    # Handle "BACK" actions (E2, C2, S2, O2)
    elif action_type == '2':
        if not is_active:
            await query.message.reply_text(
                f"""⚠️ **No Active Break, {full_name}!**

You don't have an active break to end.
Please start a break first!""",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        active_break_type_name = active_session['break_type']
        if active_break_type_name != break_type:
            await query.message.reply_text(
                f"""⚠️ **Warning, {full_name}!**

You are trying to end a '{break_type}' break, but your active break is '{active_break_type_name}'.""",
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        start_time_str = active_session['start_time']
        reason = active_session.get('reason', None)

        start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        duration_minutes = round((end_time - start_time).total_seconds() / 60, 1)

        log_break_activity(user_id, username, full_name, break_type, 'BACK', timestamp, duration_minutes, reason)
        user_sessions[user_id] = {'active': False}

        reason_text = f"\n📝 Reason: {reason}" if reason else ""
        await query.message.reply_text(
            f"""✅ **{full_name}** - Break Ended

Type: {break_type}
🕐 Time Out: {start_time_str}
🕐 Time Back: {timestamp}
⏱️ Duration: {duration_minutes:.1f} minutes{reason_text}

Welcome back!""",
            parse_mode='Markdown'
        )
        return ConversationHandler.END


async def handle_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reason input for O1 (Other Concern)"""
    user = update.effective_user
    user_id = user.id
    username = user.username or 'N/A'
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    reason = update.message.text

    break_type = context.user_data['break_type']
    start_time = context.user_data['start_time']
    group_chat_id = context.user_data.get('group_chat_id')

    # Start break session
    user_sessions[user_id] = {
        'break_type': break_type,
        'start_time': start_time,
        'active': True,
        'reason': reason,
        'full_name': full_name,
        'group_chat_id': group_chat_id
    }

    # Log the activity with reason
    log_break_activity(user_id, username, full_name, break_type, 'OUT', start_time, reason=reason)

    await update.message.reply_text(
        f"""✅ **{full_name}** - Break Started

Type: {break_type}
📝 Reason: {reason}
🕐 Time Out: {start_time}

Don't forget to clock back in when you return!""",
        parse_mode='Markdown'
    )
    return ConversationHandler.END


async def show_summary(query, user_id, username, full_name):
    """Show user's break summary for today"""
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = get_daily_log_file()

    if not os.path.exists(log_file):
        await query.message.reply_text("📊 No break history found for today.")
        return

    df = pd.read_excel(log_file, engine='openpyxl')
    # Ensure Timestamp is string before filtering
    df['Timestamp'] = df['Timestamp'].astype(str)
    user_breaks_df = df[(df['User ID'] == user_id) & (df['Timestamp'].str.startswith(today))]

    if user_breaks_df.empty:
        await query.message.reply_text(f"📊 **Today's Break Summary**\n\nNo breaks recorded today.")
        return

    # Calculate total excluding Comfort Room breaks
    total_time = user_breaks_df[user_breaks_df['Break Type'] != '🚻 Comfort Room']['Duration (minutes)'].sum()

    # Group by break type to get count and sum of duration
    summary_df = user_breaks_df[user_breaks_df['Action'] == 'BACK'].groupby('Break Type').agg(
        count=('Break Type', 'size'),
        total_duration=('Duration (minutes)', 'sum')
    ).to_dict('index')

    summary_text = f"📊 **Today's Break Summary**\n\n"
    summary_text += f"👤 {full_name}\n"
    summary_text += f"📅 Date: {today}\n\n"

    summary_text += "**Break Details:**\n"
    if not summary_df:
        summary_text += "No breaks completed today.\n"
    else:
        for break_type, stats in summary_df.items():
            summary_text += f"• {break_type}: {stats['count']} time(s) - {stats['total_duration']:.1f} min\n"

    summary_text += f"\n⏱️ **Total Break Time (excluding CR):** {total_time:.1f} minutes\n"

    await query.message.reply_text(summary_text, parse_mode='Markdown')


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the main menu with buttons"""
    keyboard = [
        [
            InlineKeyboardButton("🍽️ Eat Out (E1)", callback_data='E1'),
            InlineKeyboardButton("✅ Eat Back (E2)", callback_data='E2')
        ],
        [
            InlineKeyboardButton("🚻 CR Out (C1)", callback_data='C1'),
            InlineKeyboardButton("✅ CR Back (C2)", callback_data='C2')
        ],
        [
            InlineKeyboardButton("🚬 Smoke Out (S1)", callback_data='S1'),
            InlineKeyboardButton("✅ Smoke Back (S2)", callback_data='S2')
        ],
        [
            InlineKeyboardButton("⚠️ Other Out (O1)", callback_data='O1'),
            InlineKeyboardButton("✅ Other Back (O2)", callback_data='O2')
        ],
        [
            InlineKeyboardButton("📊 My Break Summary", callback_data='summary')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🕐 **Break Time Tracker**\n\nSelect an option:", reply_markup=reply_markup, parse_mode='Markdown')




def get_keyboard(user_id):
    """Return the main keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🍽️ Eat Out (E1)", callback_data='E1'),
            InlineKeyboardButton("✅ Eat Back (E2)", callback_data='E2')
        ],
        [
            InlineKeyboardButton("🚻 CR Out (C1)", callback_data='C1'),
            InlineKeyboardButton("✅ CR Back (C2)", callback_data='C2')
        ],
        [
            InlineKeyboardButton("🚬 Smoke Out (S1)", callback_data='S1'),
            InlineKeyboardButton("✅ Smoke Back (S2)", callback_data='S2')
        ],
        [
            InlineKeyboardButton("⚠️ Other Out (O1)", callback_data='O1'),
            InlineKeyboardButton("✅ Other Back (O2)", callback_data='O2')
        ],
        [
            InlineKeyboardButton("📊 My Break Summary", callback_data='summary')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def handle_break_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle break commands like /e1, /e2, /c1, /c2, /s1, /s2, /o1, /o2"""
    user = update.effective_user
    user_id = user.id
    username = user.username or 'N/A'
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    keyboard = get_keyboard(user_id)

    # Get group chat ID if message is from a group
    group_chat_id = None
    if update.message.chat.type in ['group', 'supergroup']:
        group_chat_id = update.message.chat.id

    command = update.message.text.split()[0].lower().replace('/', '').upper()
    message_parts = update.message.text.split(maxsplit=1)
    reason_from_command = message_parts[1] if len(message_parts) > 1 else None

    break_types = {
        'E': '🍽️ Eating',
        'C': '🚻 Comfort Room',
        'S': '🚬 Smoke Break',
        'O': '⚠️ Other Concern'
    }

    if command not in break_types.keys() and command not in ['E1', 'E2', 'C1', 'C2', 'S1', 'S2', 'O1', 'O2']:
        return

    break_type_code = command[0]
    action_type = command[1]
    break_type = break_types.get(break_type_code, 'Unknown')

    active_session = user_sessions.get(user_id)
    is_active = active_session and active_session.get('active')

    # Handle OUT actions
    if action_type == '1':
        if is_active:
            await update.message.reply_text(
                f"""⚠️ **{full_name}**

You already have an active break: {active_session['break_type']}

Please finish it first!""",
                reply_markup=keyboard, parse_mode='Markdown'
            )
            return

        if command == 'O1' and not reason_from_command:
            await update.message.reply_text(
                f"""⚠️ **{full_name}**

Please provide a reason for your 'Other' break.
Example: `/o1 emergency call`""",
                parse_mode='Markdown'
            )
            return

        # Start the new break session
        session_data = {
            'break_type': break_type,
            'start_time': timestamp,
            'active': True,
            'reason': reason_from_command,
            'full_name': full_name,
            'group_chat_id': group_chat_id
        }
        if break_type_code in ['E', 'S']:
            session_data['reminder_sent'] = False
        user_sessions[user_id] = session_data

        log_break_activity(user_id, username, full_name, break_type, 'OUT', timestamp, reason=reason_from_command)

        reason_text = f"\n📝 Reason: {reason_from_command}" if reason_from_command else ""
        await update.message.reply_text(
            f"""✅ **{full_name}** - Break Started

Type: {break_type}{reason_text}
🕐 Time Out: {timestamp}""",
            reply_markup=keyboard, parse_mode='Markdown'
        )

    # Handle BACK actions
    elif action_type == '2':
        if not is_active:
            await update.message.reply_text(
                f"""⚠️ **{full_name}**

No active break to end!""",
                reply_markup=keyboard, parse_mode='Markdown'
            )
            return

        # Check if the break type matches
        active_break_type_name = active_session['break_type']
        if active_break_type_name != break_type:
            await update.message.reply_text(
                f"""⚠️ **{full_name}**

You are trying to end a '{break_type}' break, but your active break is '{active_break_type_name}'.""",
                reply_markup=keyboard, parse_mode='Markdown'
            )
            return

        # End the break
        start_time = datetime.strptime(active_session['start_time'], '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        duration_minutes = round((end_time - start_time).total_seconds() / 60, 1)
        reason = active_session.get('reason')

        log_break_activity(user_id, username, full_name, break_type, 'BACK', timestamp, duration_minutes, reason)
        user_sessions[user_id] = {'active': False}

        reason_text = f"\n📝 Reason: {reason}" if reason else ""
        await update.message.reply_text(
            f"""✅ **{full_name}** - Break Ended

Type: {break_type}
⏱️ Duration: {duration_minutes:.1f} min{reason_text}""",
            reply_markup=keyboard, parse_mode='Markdown'
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text(
        "Operation cancelled.",
    )
    return ConversationHandler.END


async def check_break_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Periodically check for long-running breaks and send reminders."""
    now = datetime.now()
    for user_id, session in user_sessions.items():
        if session.get('active') and not session.get('reminder_sent'):
            break_type = session.get('break_type')

            # Define reminder thresholds for specific break types
            reminder_config = {
                '🚬 Smoke Break': 15,  # S1 - 15 minutes
                '🍽️ Eating': 60       # E1 - 60 minutes (1 hour)
                # C1 (Comfort Room) and O1 (Other Concern) - no reminders
            }

            # Check if this break type has a reminder threshold
            if break_type in reminder_config:
                threshold_minutes = reminder_config[break_type]
                start_time = datetime.strptime(session['start_time'], '%Y-%m-%d %H:%M:%S')
                duration_minutes = (now - start_time).total_seconds() / 60

                if duration_minutes >= threshold_minutes:
                    full_name = session.get('full_name', 'there')
                    group_chat_id = session.get('group_chat_id')

                    # Send to group if available, otherwise to user
                    target_chat_id = group_chat_id if group_chat_id else user_id

                    await context.bot.send_message(
                        chat_id=target_chat_id,
                        text=f"""🔔 **Break Reminder, {full_name}!**

You have been on your '{break_type}' break for {int(duration_minutes)} minutes (limit: {threshold_minutes} minutes)!""",
                        parse_mode='Markdown'
                    )
                    session['reminder_sent'] = True


async def run_end_of_day_reports(context: ContextTypes.DEFAULT_TYPE):
    """Run daily reports for 'no back' breaks and individual summaries."""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"\n{'='*50}")
    print(f"Running end-of-day reports for {yesterday}...")
    print(f"{'='*50}")

    # Get yesterday's log file
    year_month = (datetime.now() - timedelta(days=1)).strftime('%Y-%m')
    month_dir = os.path.join(DATABASE_DIR, year_month)
    log_file = os.path.join(month_dir, f"break_logs_{yesterday}.xlsx")

    if not os.path.exists(log_file):
        print(f"Log file not found for {yesterday}. Skipping daily reports.")
        return

    df = pd.read_excel(log_file, engine='openpyxl')

    if df.empty:
        print("No activity yesterday. Skipping reports.")
        return

    # 1. Generate 'No Back' summary
    _generate_no_back_summary(df, yesterday)

    # 2. Send individual summaries
    await _send_individual_summaries(df, context)


def _generate_no_back_summary(df: pd.DataFrame, date: str):
    """Analyzes the dataframe for breaks that were not ended and prints a summary."""
    print(f"\n--- Daily 'No Back' Report for {date} ---")
    summary = {}
    for _, row in df.iterrows():
        user_key = (row['User ID'], row['Full Name'])
        if user_key not in summary:
            summary[user_key] = {}

        break_type = row['Break Type']
        if break_type not in summary[user_key]:
            summary[user_key][break_type] = {'OUT': 0, 'BACK': 0}

        summary[user_key][break_type][row['Action']] += 1

    found_missing = False
    for user, breaks in summary.items():
        user_id, full_name = user
        for break_type, actions in breaks.items():
            if actions['OUT'] > actions['BACK']:
                found_missing = True
                print(f"⚠️  User: {full_name} ({user_id}) - Break: {break_type} - Missing {actions['OUT'] - actions['BACK']} 'BACK' log(s).")

    if not found_missing:
        print("✅ All breaks were properly logged.")
    print(f"{'='*50}\n")


async def _send_individual_summaries(df: pd.DataFrame, context: ContextTypes.DEFAULT_TYPE):
    """Sends each user a summary of their breaks for the day."""
    unique_users = df['User ID'].unique()

    for user_id in unique_users:
        user_df = df[df['User ID'] == user_id]
        full_name = user_df['Full Name'].iloc[0]
        report_date = user_df['Timestamp'].iloc[0].split()[0]

        # Calculate total excluding Comfort Room breaks
        total_time = user_df[user_df['Break Type'] != '🚻 Comfort Room']['Duration (minutes)'].sum()

        # Group by break type to get count and sum of duration
        summary_df = user_df[user_df['Action'] == 'BACK'].groupby('Break Type').agg(
            count=('Break Type', 'size'),
            total_duration=('Duration (minutes)', 'sum')
        ).to_dict('index')

        summary_text = f"📊 **Your Daily Break Summary**\n\n"
        summary_text += f"👤 {full_name}\n"
        summary_text += f"📅 Date: {report_date}\n\n"

        summary_text += "**Break Details:**\n"
        if not summary_df:
            summary_text += "No breaks completed for this day.\n"
        else:
            for break_type, stats in summary_df.items():
                summary_text += f"• {break_type}: {stats['count']} time(s) - {stats['total_duration']:.1f} min\n"

        summary_text += f"\n⏱️ **Total Break Time (excluding CR):** {total_time:.1f} minutes\n"

        try:
            await context.bot.send_message(chat_id=user_id, text=summary_text, parse_mode='Markdown')
        except Exception as e:
            print(f"Failed to send daily summary to {user_id}: {e}")


def main():
    """Start the bot"""
    print("\n" + "="*60)
    print("🤖 Break Time Tracker Bot - Production Mode")
    print("="*60)

    # Initialize database structure
    init_database_structure()

    # Initialize Excel Online sync (if configured)
    if EXCEL_SYNC_AVAILABLE:
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(init_excel_handler())
            if result:
                print("✅ Excel Online sync enabled")
            else:
                print("⚠️ Excel Online sync not configured or failed to initialize")
        except Exception as e:
            print(f"⚠️ Excel Online sync initialization error: {e}")
    else:
        print("ℹ️ Excel Online sync not available (module not installed)")

    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # --- Job Queue Setup ---
    job_queue = application.job_queue
    # Run reminder check every minute
    job_queue.run_repeating(check_break_reminders, interval=60, first=0)
    print("✅ Break reminder system activated (checks every 60 seconds)")

    # Run daily reports every day at midnight
    job_queue.run_daily(run_end_of_day_reports, time=time(0, 0), job_kwargs={'misfire_grace_time': 30})
    print("✅ Daily report system scheduled (runs at midnight)")
    print("="*60)


    # Create a ConversationHandler for O1 reason entry only
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback, pattern='^O1$')],
        states={
            WAITING_FOR_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reason)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('menu', menu))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(CommandHandler("e1", handle_break_command))
    application.add_handler(CommandHandler("e2", handle_break_command))
    application.add_handler(CommandHandler("c1", handle_break_command))
    application.add_handler(CommandHandler("c2", handle_break_command))
    application.add_handler(CommandHandler("s1", handle_break_command))
    application.add_handler(CommandHandler("s2", handle_break_command))
    application.add_handler(CommandHandler("o1", handle_break_command))
    application.add_handler(CommandHandler("o2", handle_break_command))

    # Start the bot
    print("\n🚀 Bot is now running...")
    print("📂 Database location:", DATABASE_DIR)
    print("📊 Today's log file:", get_daily_log_file())
    print("\nPress Ctrl+C to stop the bot\n")
    print("="*60 + "\n")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
