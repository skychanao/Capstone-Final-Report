import pandas as pd
from datetime import datetime, timezone

# Load Data
df = pd.read_csv(r"outputs\godot_individual_activity_filtered.csv", parse_dates=['date'])
df['date'] = pd.to_datetime(df['date'], utc=True)

START_DATE = datetime(2025, 9, 23, tzinfo=timezone.utc)
END_DATE = datetime(2026, 9, 23, tzinfo=timezone.utc)
SIX_MONTHS_AGO = datetime(2026, 3, 23, tzinfo=timezone.utc)
THREE_MONTHS_AGO = datetime(2026, 6, 23, tzinfo=timezone.utc)

# Use results form botDetection to remove bots and manual analysis from analysis
def is_bot(user_str):
    user_lower = str(user_str).lower()
    return '[bot]' in user_lower or user_lower == 'ghost' 

# Separate bots from humans
df_bot = df[df['user'].apply(is_bot)].copy()
df_filtered = df[~df['user'].apply(is_bot)].copy()

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

    # only select contributors with more actvities than the mean
    user['total_activities'] = user['total_activities']
    min_5_activity_df = user[user['total_activities'] > int(all_activity_count_stats['mean'].iloc[0])]

    stats = summarize_activity_counts(min_5_activity_df['total_activities'])
    stats['group'] = '> Mean'
    
    # Convert to DataFrame
    stats_df = pd.DataFrame([stats])
    
    # compute 90th percentile of number of activities among all these users
    threshold = min_5_activity_df['total_activities'].quantile(0.90)
    # print(min_5_activity_df['total_activities'].quantile(0.99))
    
    return threshold, stats_df

# Unpack the threshold and the dataframe for the > Mean contributors
frequent_threshold_raw, above_mean_stats_df = frequent_threshold_determinator(user_stats)
frequent_threshold = round(frequent_threshold_raw)
print("frequent_threshold:", frequent_threshold)
mean_threshold = round(all_activity_count_stats['mean'].iloc[0])
print("mean_threshold:", mean_threshold)

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
# 5. STATISTICS & OUTPUT
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

print(all_activity_count_stats.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

print(above_mean_stats_df.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

print("\n=== ACTIVITIES PER USER (one count per canonical contributor) ===")
print(group_count_stats.to_string(index=False, float_format=lambda value: f"{value:.2f}"))

# Export
user_stats.to_csv(r"outputs\user_stats.csv", index=False)
group_count_stats.to_csv(r"outputs\activity_count_statistics.csv", index=False)
df_filtered.to_csv(r"outputs\bot_activity_filtered.csv", index=False)