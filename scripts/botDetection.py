import pandas as pd

# Load activity data
df = pd.read_csv(r"outputs\godot_individual_activity_filtered.csv", parse_dates=['date'])

# 1. Name Matching
def check_name_bot(user_str):
    user_lower = str(user_str).lower()
    if '[bot]' in user_lower:
        return "Measure 1: Username contains '[bot]'"
    elif user_lower in ['godot-engine-bot', 'dependabot']:
        return f"Measure 1: Known bot account '{user_str}'"
    return None

# 2. PR and Issues vs Commits
def check_activity_count():
    activity_pivot = df.groupby(['user', 'activity_type']).size().unstack(fill_value=0)
    for col in ['commit', 'pull_request', 'issue']:
        if col not in activity_pivot.columns:
            activity_pivot[col] = 0
            
    activity_pivot['automated_actions'] = activity_pivot['pull_request'] + activity_pivot['issue']

    # Threshold: >50 PRs/Issues and exactly 0 commits
    behavioral_bots = activity_pivot[
        (activity_pivot['automated_actions'] > 50) & 
        (activity_pivot['commit'] == 0)
    ].index.tolist()

    return behavioral_bots, activity_pivot

# 3. Frequencies of activties
def check_frequencies():
    # Sort locally to not mess up the main dataframe's order
    df_sorted = df.sort_values(by=['user', 'date']).copy()

    # Calculate time difference between consecutive actions
    df_sorted['time_since_last_action'] = df_sorted.groupby('user')['date'].diff().dt.total_seconds()

    # Define fast action threshold
    FAST_ACTION_THRESHOLD_SECONDS = 3
    df_sorted['is_fast_action'] = df_sorted['time_since_last_action'] < FAST_ACTION_THRESHOLD_SECONDS

    # Count fast actions per user
    speed_stats = df_sorted.groupby('user').agg(
        total_actions=('date', 'count'),
        fast_actions=('is_fast_action', 'sum')
    ).reset_index()

    # Flag users with > 15 incredibly fast actions
    speed_bots = speed_stats[speed_stats['fast_actions'] > 15]['user'].tolist()

    return speed_bots, speed_stats, FAST_ACTION_THRESHOLD_SECONDS

# Run filters
speed_bots, speed_stats, FAST_ACTION_THRESHOLD_SECONDS = check_frequencies()
behavioral_bots, activity_pivot = check_activity_count()

def get_bot_reason(user_str):
    # Check Measure 1 (Name)
    name_reason = check_name_bot(user_str)
    if name_reason:
        return name_reason
    
    # Check Measure 2 (Volume vs Commits)
    if user_str in behavioral_bots:
        pull_requests = activity_pivot.loc[user_str, 'pull_request']
        issues = activity_pivot.loc[user_str, 'issue']
        return f"Measure 2: Behavioral (0 commits, {pull_requests} automated PRs, {issues} Issues)"

    # Check Measure 3 (Activity Speed)
    if user_str in speed_bots:
        fast_count = speed_stats.loc[speed_stats['user'] == user_str, 'fast_actions'].values[0]
        return f"Measure 3: Activity Speed ({fast_count} actions under {FAST_ACTION_THRESHOLD_SECONDS}s)"
        
    return None


# Create explanation column
df['bot_reason'] = df['user'].apply(get_bot_reason)

# Split dataset
df_bot = df[df['bot_reason'].notnull()].copy()
df_filtered = df[df['bot_reason'].isnull()].copy().drop(columns=['bot_reason'])

# Print summary of caught bots
bot_summary = df_bot[['user', 'bot_reason']].drop_duplicates().sort_values(by='bot_reason')

print("=== IDENTIFIED BOTS & REASONS ===")
for _, row in bot_summary.iterrows():
    print(f"User: {row['user'].ljust(20)} | {row['bot_reason']}")