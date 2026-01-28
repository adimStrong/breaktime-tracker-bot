"""
Breaktime Tracker Dashboard - Data Layer
Reads data from Excel files stored in database/YYYY-MM/break_logs_YYYY-MM-DD.xlsx
"""

import os
import pandas as pd
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# Configuration
BASE_DIR = os.getenv('BASE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATABASE_DIR = os.path.join(BASE_DIR, "database")

# Philippine Timezone (UTC+8)
PH_TIMEZONE = timezone(timedelta(hours=8))
UTC_TIMEZONE = timezone.utc

def get_ph_now():
    """Get current datetime in Philippine timezone."""
    return datetime.now(PH_TIMEZONE)

def convert_to_ph_time(timestamp_str):
    """Convert a timestamp string to PH timezone display format."""
    try:
        # Parse the timestamp
        dt = pd.to_datetime(timestamp_str)
        # Timestamps are already saved in PH time by the bot, just format them
        return dt.strftime('%Y-%m-%d %I:%M:%S %p')
    except:
        return timestamp_str


# ============================================
# DATA CLASSES
# ============================================

@dataclass
class RealtimeMetrics:
    """Real-time dashboard header metrics."""
    active_breaks: int = 0
    completed_breaks_today: int = 0
    agents_active_today: int = 0
    total_break_time_today: float = 0.0
    compliance_rate: float = 100.0
    timestamp: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class BreakDistribution:
    """Break distribution by type."""
    break_type: str
    count: int
    total_duration: float
    avg_duration: float
    percentage: float


@dataclass
class AgentPerformance:
    """Individual agent performance metrics."""
    user_id: int
    full_name: str
    total_breaks: int
    total_duration: float
    avg_duration: float
    status: str  # 'available'


@dataclass
class HourlyData:
    """Hourly break distribution."""
    hour: int
    hour_label: str
    break_outs: int
    break_backs: int


@dataclass
class ComplianceTrend:
    """Daily compliance trend data point."""
    date: str
    total_breaks: int
    agents_count: int


@dataclass
class ActiveBreak:
    """Currently active break (agent is OUT)."""
    user_id: int
    full_name: str
    break_type: str
    out_time: str
    duration_minutes: float


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_ph_date():
    """Get current date in Philippine timezone."""
    return get_ph_now().date()

def get_daily_log_file(target_date: date = None) -> str:
    """Get the log file path for a specific date."""
    if target_date is None:
        target_date = get_ph_date()  # Use PH date instead of server date

    year_month = target_date.strftime('%Y-%m')
    day_str = target_date.strftime('%Y-%m-%d')

    month_dir = os.path.join(DATABASE_DIR, year_month)
    log_file = os.path.join(month_dir, f"break_logs_{day_str}.xlsx")
    return log_file


def load_daily_data(target_date: date = None) -> pd.DataFrame:
    """Load break data for a specific date."""
    log_file = get_daily_log_file(target_date)

    if not os.path.exists(log_file):
        return pd.DataFrame(columns=['User ID', 'Username', 'Full Name', 'Break Type',
                                     'Action', 'Timestamp', 'Duration (minutes)', 'Reason'])

    try:
        df = pd.read_excel(log_file, engine='openpyxl')
        # Ensure Timestamp is string
        if 'Timestamp' in df.columns:
            df['Timestamp'] = df['Timestamp'].astype(str)
        return df
    except Exception as e:
        print(f"Error loading {log_file}: {e}")
        return pd.DataFrame(columns=['User ID', 'Username', 'Full Name', 'Break Type',
                                     'Action', 'Timestamp', 'Duration (minutes)', 'Reason'])


def load_data_for_period(start_date: date, end_date: date) -> pd.DataFrame:
    """Load break data for a date range."""
    all_data = []
    current = start_date

    while current <= end_date:
        df = load_daily_data(current)
        if not df.empty:
            df['Date'] = current.strftime('%Y-%m-%d')
            all_data.append(df)
        current += timedelta(days=1)

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame(columns=['User ID', 'Username', 'Full Name', 'Break Type',
                                 'Action', 'Timestamp', 'Duration (minutes)', 'Reason', 'Date'])


# ============================================
# METRICS FUNCTIONS
# ============================================

def get_realtime_metrics() -> RealtimeMetrics:
    """Get real-time metrics for dashboard header."""
    df = load_daily_data()

    if df.empty:
        return RealtimeMetrics(timestamp=get_ph_now().strftime('%Y-%m-%d %H:%M:%S'))

    # Completed breaks (BACK actions)
    completed = len(df[df['Action'] == 'BACK'])

    # Active agents
    agents = df['User ID'].nunique()

    # Total break time (excluding CR)
    back_df = df[df['Action'] == 'BACK'].copy()
    non_cr = back_df[~back_df['Break Type'].str.contains('Comfort Room', case=False, na=False)]
    total_time = non_cr['Duration (minutes)'].sum() if 'Duration (minutes)' in non_cr.columns else 0

    return RealtimeMetrics(
        active_breaks=0,  # Would need session tracking
        completed_breaks_today=completed,
        agents_active_today=agents,
        total_break_time_today=round(float(total_time) if pd.notna(total_time) else 0, 1),
        compliance_rate=100.0,
        timestamp=get_ph_now().strftime('%Y-%m-%d %H:%M:%S')
    )


def get_break_distribution_today() -> List[BreakDistribution]:
    """Get break distribution by type for today."""
    df = load_daily_data()

    if df.empty:
        return []

    back_df = df[df['Action'] == 'BACK'].copy()

    if back_df.empty:
        return []

    # Group by break type
    grouped = back_df.groupby('Break Type').agg({
        'User ID': 'count',
        'Duration (minutes)': ['sum', 'mean']
    }).reset_index()

    grouped.columns = ['break_type', 'count', 'total_duration', 'avg_duration']
    total_count = grouped['count'].sum()

    results = []
    for _, row in grouped.iterrows():
        results.append(BreakDistribution(
            break_type=row['break_type'],
            count=int(row['count']),
            total_duration=round(float(row['total_duration']) if pd.notna(row['total_duration']) else 0, 1),
            avg_duration=round(float(row['avg_duration']) if pd.notna(row['avg_duration']) else 0, 1),
            percentage=round(100 * row['count'] / total_count, 1) if total_count > 0 else 0
        ))

    return results


def get_agent_performance_today() -> List[AgentPerformance]:
    """Get performance metrics for all agents today."""
    df = load_daily_data()

    if df.empty:
        return []

    back_df = df[df['Action'] == 'BACK'].copy()

    if back_df.empty:
        # Return agents with 0 breaks
        agents_df = df[['User ID', 'Full Name']].drop_duplicates()
        return [
            AgentPerformance(
                user_id=int(row['User ID']),
                full_name=row['Full Name'],
                total_breaks=0,
                total_duration=0,
                avg_duration=0,
                status='available'
            )
            for _, row in agents_df.iterrows()
        ]

    # Filter out CR breaks for duration calculation
    non_cr = back_df[~back_df['Break Type'].str.contains('Comfort Room', case=False, na=False)]

    grouped = non_cr.groupby(['User ID', 'Full Name']).agg({
        'Break Type': 'count',
        'Duration (minutes)': ['sum', 'mean']
    }).reset_index()

    grouped.columns = ['user_id', 'full_name', 'total_breaks', 'total_duration', 'avg_duration']

    results = []
    for _, row in grouped.iterrows():
        results.append(AgentPerformance(
            user_id=int(row['user_id']),
            full_name=row['full_name'],
            total_breaks=int(row['total_breaks']),
            total_duration=round(float(row['total_duration']) if pd.notna(row['total_duration']) else 0, 1),
            avg_duration=round(float(row['avg_duration']) if pd.notna(row['avg_duration']) else 0, 1),
            status='available'
        ))

    return sorted(results, key=lambda x: x.total_breaks, reverse=True)


def get_hourly_distribution_today() -> List[HourlyData]:
    """Get hourly break distribution for today."""
    df = load_daily_data()

    # Initialize all hours
    hourly_data = {h: {'outs': 0, 'backs': 0} for h in range(24)}

    if not df.empty and 'Timestamp' in df.columns:
        for _, row in df.iterrows():
            try:
                ts = pd.to_datetime(row['Timestamp'])
                hour = ts.hour
                if row['Action'] == 'OUT':
                    hourly_data[hour]['outs'] += 1
                else:
                    hourly_data[hour]['backs'] += 1
            except:
                pass

    results = []
    for hour in range(24):
        data = hourly_data[hour]
        if hour == 0:
            label = "12 AM"
        elif hour < 12:
            label = f"{hour} AM"
        elif hour == 12:
            label = "12 PM"
        else:
            label = f"{hour - 12} PM"

        results.append(HourlyData(
            hour=hour,
            hour_label=label,
            break_outs=data['outs'],
            break_backs=data['backs']
        ))

    return results


def get_active_breaks() -> List[ActiveBreak]:
    """Get list of agents currently on break (OUT without BACK)."""
    df = load_daily_data()

    if df.empty:
        return []

    # Track last action per user
    active = {}

    # Sort by timestamp to process in order
    if 'Timestamp' in df.columns:
        df = df.sort_values('Timestamp')

    for _, row in df.iterrows():
        user_id = int(row['User ID'])
        action = row['Action']

        if action == 'OUT':
            # User went on break
            active[user_id] = {
                'user_id': user_id,
                'full_name': row['Full Name'],
                'break_type': row['Break Type'],
                'out_time': row['Timestamp']
            }
        elif action == 'BACK' and user_id in active:
            # User came back
            del active[user_id]

    # Calculate duration for active breaks
    now = get_ph_now()
    results = []
    for data in active.values():
        try:
            out_time = pd.to_datetime(data['out_time'])
            # Timestamps are saved in PH time by the bot, so treat as PH time
            if out_time.tzinfo is None:
                out_time = out_time.replace(tzinfo=PH_TIMEZONE)
            duration = (now - out_time).total_seconds() / 60
        except:
            duration = 0

        results.append(ActiveBreak(
            user_id=data['user_id'],
            full_name=data['full_name'],
            break_type=data['break_type'],
            out_time=convert_to_ph_time(data['out_time']),
            duration_minutes=round(duration, 1)
        ))

    # Sort by duration descending (longest break first)
    return sorted(results, key=lambda x: x.duration_minutes, reverse=True)


def get_compliance_trend(days: int = 7) -> List[ComplianceTrend]:
    """Get compliance trend over the last N days."""
    end_date = get_ph_date()
    start_date = end_date - timedelta(days=days-1)

    results = []
    current = start_date

    while current <= end_date:
        df = load_daily_data(current)

        if df.empty:
            results.append(ComplianceTrend(
                date=current.strftime('%Y-%m-%d'),
                total_breaks=0,
                agents_count=0
            ))
        else:
            back_df = df[df['Action'] == 'BACK']
            results.append(ComplianceTrend(
                date=current.strftime('%Y-%m-%d'),
                total_breaks=len(back_df),
                agents_count=df['User ID'].nunique()
            ))

        current += timedelta(days=1)

    return results


def get_full_dashboard_data() -> Dict:
    """Get all data needed for the main dashboard in one call."""
    active_breaks = get_active_breaks()
    realtime = get_realtime_metrics()
    realtime.active_breaks = len(active_breaks)

    return {
        'realtime': realtime.to_dict(),
        'active_breaks': [asdict(a) for a in active_breaks],
        'break_distribution': [asdict(d) for d in get_break_distribution_today()],
        'agent_performance': [asdict(a) for a in get_agent_performance_today()],
        'hourly_distribution': [asdict(h) for h in get_hourly_distribution_today()],
        'compliance_trend': [asdict(t) for t in get_compliance_trend(7)],
        'generated_at': get_ph_now().strftime('%Y-%m-%d %H:%M:%S')
    }


def get_break_logs(start_date: date, end_date: date,
                   user_id: Optional[int] = None,
                   break_type: Optional[str] = None,
                   limit: int = 100, offset: int = 0) -> Dict:
    """Get historical break logs with filters."""
    df = load_data_for_period(start_date, end_date)

    if df.empty:
        return {'total': 0, 'limit': limit, 'offset': offset, 'logs': []}

    # Apply filters
    if user_id:
        df = df[df['User ID'] == user_id]

    if break_type:
        df = df[df['Break Type'].str.contains(break_type, case=False, na=False)]

    total = len(df)

    # Sort by timestamp descending
    df = df.sort_values('Timestamp', ascending=False)

    # Apply pagination
    df = df.iloc[offset:offset+limit]

    logs = []
    for _, row in df.iterrows():
        logs.append({
            'timestamp': convert_to_ph_time(row['Timestamp']),
            'full_name': row['Full Name'],
            'user_id': int(row['User ID']),
            'break_type': row['Break Type'],
            'action': row['Action'],
            'duration_minutes': row['Duration (minutes)'] if pd.notna(row.get('Duration (minutes)')) else None,
            'reason': row['Reason'] if pd.notna(row.get('Reason')) else None
        })

    return {
        'total': total,
        'limit': limit,
        'offset': offset,
        'logs': logs
    }


# ============================================
# TEST
# ============================================

if __name__ == '__main__':
    print("Testing Data Layer...")
    print(f"\nDatabase directory: {DATABASE_DIR}")

    print("\n1. Real-time Metrics:")
    metrics = get_realtime_metrics()
    print(f"   Completed today: {metrics.completed_breaks_today}")
    print(f"   Agents active: {metrics.agents_active_today}")

    print("\n2. Break Distribution:")
    for dist in get_break_distribution_today():
        print(f"   {dist.break_type}: {dist.count} ({dist.percentage}%)")

    print("\n3. Agent Performance:")
    for agent in get_agent_performance_today()[:5]:
        print(f"   {agent.full_name}: {agent.total_breaks} breaks")

    print("\nData layer test complete!")
