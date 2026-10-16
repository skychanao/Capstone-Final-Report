import re
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

# ==========================================
# 0. CONFIGURATION & DATA LOADING
# ==========================================
# Resolve outputs directory whether run from repo root or scripts directory
if Path("outputs").is_dir():
    OUTPUTS_DIR = Path("outputs")
elif (Path(__file__).resolve().parent.parent / "outputs").is_dir():
    OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
else:
    OUTPUTS_DIR = Path("outputs")

df = pd.read_csv(OUTPUTS_DIR / "godot_individual_activity_filtered.csv", parse_dates=['date'])
df['date'] = pd.to_datetime(df['date'], utc=True)

START_DATE = datetime(2025, 9, 23, tzinfo=timezone.utc)
END_DATE = datetime(2026, 9, 23, tzinfo=timezone.utc)
SIX_MONTHS_AGO = datetime(2026, 3, 23, tzinfo=timezone.utc)
THREE_MONTHS_AGO = datetime(2026, 6, 23, tzinfo=timezone.utc)

# ==========================================
# 1. BOT DETECTION & FILTERING
# ==========================================
# Measure 1: Name Matching
def check_name_bot(user_str):
    user_lower = str(user_str).lower()
    if '[bot]' in user_lower:
        return "Measure 1: Username contains '[bot]'"
    elif user_lower in ['godot-engine-bot', 'dependabot']:
        return f"Measure 1: Known bot account '{user_str}'"
    return None

# Measure 2: PR and Issues vs Commits (Behavioral volume)
def check_activity_count(activity_df):
    activity_pivot = activity_df.groupby(['user', 'activity_type']).size().unstack(fill_value=0)
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

# Measure 3: Check frequencies of the same activity (Speed)
def check_frequencies(activity_df):
    # Sort locally to avoid modifying original ordering
    df_sorted = activity_df.sort_values(by=['user', 'date']).copy()

    # Calculate time difference between consecutive actions
    df_sorted['time_since_last_action'] = df_sorted.groupby('user')['date'].diff().dt.total_seconds()

    # Define fast action threshold (bursts)
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

speed_bots, speed_stats, FAST_ACTION_THRESHOLD_SECONDS = check_frequencies(df)
behavioral_bots, activity_pivot = check_activity_count(df)

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

# Tag and filter out bots
df['bot_reason'] = df['user'].apply(get_bot_reason)
df_bot = df[df['bot_reason'].notnull()].copy()
df_filtered = df[df['bot_reason'].isnull()].copy().drop(columns=['bot_reason'])

print("=== IDENTIFIED BOTS & REASONS ===")
bot_summary = df_bot[['user', 'bot_reason']].drop_duplicates().sort_values(by='bot_reason')
for _, row in bot_summary.iterrows():
    print(f"User: {row['user'].ljust(20)} | {row['bot_reason']}")
print(f"Total bot actions removed: {len(df_bot)} across {df_bot['user'].nunique()} bot accounts.\n")

# ==========================================
# 2. MULTIPLE ACCOUNT DETECTION (Identity Aliasing)
# ==========================================
# Measure 1: Exact Email Matching
email_to_primary_user = df_filtered.dropna(subset=['email']).groupby('email')['user'].first().to_dict()
user_to_primary_user = (
    df_filtered.dropna(subset=['email'])
    .set_index('user')['email']
    .map(email_to_primary_user)
    .to_dict()
)
df_filtered['canonical_user'] = (
    df_filtered['user'].map(user_to_primary_user)
    .fillna(df_filtered['email'].map(email_to_primary_user))
    .fillna(df_filtered['user'])
)

# Measure 2: Username String Normalization
def normalize_username(name):
    # Strip all non-alphanumeric characters and convert to lowercase
    return re.sub(r'[^a-zA-Z0-9]', '', str(name)).lower()

df_filtered['simplified_name'] = df_filtered['canonical_user'].apply(normalize_username)
simplified_to_canonical = df_filtered.groupby('simplified_name')['canonical_user'].first().to_dict()
df_filtered['canonical_user'] = df_filtered['simplified_name'].map(simplified_to_canonical)
df_filtered = df_filtered.drop(columns=['simplified_name'])

merged_accounts = df_filtered.groupby('canonical_user')['user'].unique()
aliased_users = merged_accounts[merged_accounts.apply(len) > 1]

print("=== MULTIPLE ACCOUNT DETECTION SUMMARY ===")
print("Account normalization complete.")
print(f"Found {len(aliased_users)} developers using multiple accounts.\n")
print("=== EXAMPLES OF MERGED ACCOUNTS ===")
for canonical, originals in aliased_users.items():
    print(f"Canonical User: '{canonical}' is used by accounts: {list(originals)}")

# ==========================================
# 3. CONTRIBUTOR ANALYSIS & CATEGORIZATION
# ==========================================
user_stats = df_filtered.groupby('canonical_user').agg(
    total_activities=('activity_type', 'count'),
    first_activity=('date', 'min'),
    latest_activity=('date', 'max'),
    active_months=('date', lambda x: pd.to_datetime(x).dt.strftime('%Y-%m').nunique())
).reset_index()

def summarize_activity_counts(activity_counts):
    modes = activity_counts.mode()
    mode_frequency = activity_counts.value_counts().max()
    return {
        'user_count': activity_counts.count(),
        'mean': activity_counts.mean(),
        'median': activity_counts.median(),
        'mode': ', '.join(str(int(value)) for value in modes) if not modes.empty else "N/A",
        'std_dev': activity_counts.std(),
        'min': activity_counts.min(),
        '25th_percentile': activity_counts.quantile(0.25),
        '90th_percentile': activity_counts.quantile(0.90),
        'max': activity_counts.max()
    }

all_activity_count_stats = pd.DataFrame([
    {'group': 'All contributors', **summarize_activity_counts(user_stats['total_activities'])}
])

def frequent_threshold_determinator(user):
    # only select contributors with more activities than the mean
    user['total_activities'] = user['total_activities']
    min_5_activity_df = user[user['total_activities'] > int(all_activity_count_stats['mean'].iloc[0])]

    stats = summarize_activity_counts(min_5_activity_df['total_activities'])
    stats['group'] = '> Mean'
    
    # Convert to DataFrame
    stats_df = pd.DataFrame([stats])
    
    # compute 90th percentile of number of activities among all these users
    threshold = min_5_activity_df['total_activities'].quantile(0.90)
    
    return threshold, stats_df

# Unpack the threshold and the dataframe for the > Mean contributors
frequent_threshold_raw, above_mean_stats_df = frequent_threshold_determinator(user_stats)
frequent_threshold = round(frequent_threshold_raw)
print(f"\nfrequent_threshold: {frequent_threshold}")
mean_threshold = round(all_activity_count_stats['mean'].iloc[0])
print(f"mean_threshold: {mean_threshold}")

def categorize_contributor(row):
    # 1. High-impact or consistent contributors
    if row['total_activities'] >= frequent_threshold or row['active_months'] >= 6:
        return 'Frequent / Key'
    
    # 2. Joined in the last 6 months (Pipeline)
    if row['first_activity'] >= THREE_MONTHS_AGO:
        return 'Newcomer'
    
    # 3. Was active (4+ actions) but hasn't returned in 6 months
    if row['latest_activity'] < SIX_MONTHS_AGO and row['total_activities'] >= mean_threshold:
        return 'Dormant'
    
    # 4. Only one activity and hasn't returned in 6 months
    if row['total_activities'] < mean_threshold and row['latest_activity'] < THREE_MONTHS_AGO:
        return 'Drive-thru'
    
    # 5. Established but low frequency, or active but low volume
    return 'Casual'

user_stats['category'] = user_stats.apply(categorize_contributor, axis=1)


# ==========================================
# 4. STATISTICS & OUTPUT
# ==========================================

# Standardize column order for all tables
cols = ['group', 'user_count', 'mean', 'median', 'mode', 'std_dev', 'min', '25th_percentile', '90th_percentile', 'max']

# Calculate group stats
group_count_stats = pd.DataFrame([
    *[
        {'group': category, **summarize_activity_counts(group['total_activities'])}
        for category, group in user_stats.groupby('category', sort=True)
    ]
])

# Reorder columns for all dataframes
all_activity_count_stats = all_activity_count_stats[cols]
above_mean_stats_df = above_mean_stats_df[cols]
group_count_stats = group_count_stats[cols]

print("\n=== CONTRIBUTOR HEALTH SUMMARY ===")
print(user_stats['category'].value_counts().to_string())

print("\n=== OVERALL & >MEAN ACTIVITY STATS ===")
print(all_activity_count_stats.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
print(above_mean_stats_df.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

print("\n=== ACTIVITIES PER USER (one count per canonical contributor) ===")
print(group_count_stats.to_string(index=False, float_format=lambda value: f"{value:.2f}"))

# Export
user_stats.to_csv(OUTPUTS_DIR / "user_stats.csv", index=False)
group_count_stats.to_csv(OUTPUTS_DIR / "activity_count_statistics.csv", index=False)
df_filtered.to_csv(OUTPUTS_DIR / "activity_filtered.csv", index=False)
print("\nExported successfully to outputs/")