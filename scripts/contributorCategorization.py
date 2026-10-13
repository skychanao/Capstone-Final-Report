import pandas as pd
from datetime import datetime, timezone

# Load Data
df = pd.read_csv(r"outputs\godot_individual_activity_filtered.csv", parse_dates=['date'])
df['date'] = pd.to_datetime(df['date'], utc=True)



START_DATE = datetime(2025, 9, 23, tzinfo=timezone.utc)
END_DATE = datetime(2026, 9, 23, tzinfo=timezone.utc)
SIX_MONTHS_AGO = datetime(2026, 3, 23, tzinfo=timezone.utc)

#Use results form botDetection to remove bots from analysis
def is_bot(user_str):
    user_lower = str(user_str).lower()
    return '[bot]' in user_lower or user_lower == 'ghost' 

# Separate bots from humans
df_bot = df[df['user'].apply(is_bot)].copy()
df_filtered = df[~df['user'].apply(is_bot)].copy()

# Measure 1 for Multiple Accounts: Normalization by Email
email_to_user = df_filtered.dropna(subset=['email']).groupby('email')['user'].first().to_dict()
df_filtered['canonical_user'] = df_filtered['email'].map(email_to_user).fillna(df_filtered['user'])


user_stats = df_filtered.groupby('canonical_user').agg(
    total_activities=('activity_type', 'count'),
    first_seen=('date', 'min'),
    last_seen=('date', 'max'),
    active_months=('date', lambda x: pd.to_datetime(x).dt.strftime('%Y-%m').nunique())
).reset_index()

def categorize_contributor(row):
    if row['total_activities'] >= 50 or row['active_months'] >= 6:
        return 'Frequent / Key'
    elif row['first_seen'] >= SIX_MONTHS_AGO and row['total_activities'] <= 5:
        return 'Newcomer'
    elif row['first_seen'] < SIX_MONTHS_AGO and row['last_seen'] < SIX_MONTHS_AGO and row['total_activities'] >= 5:
        return 'Dormant'
    else:
        return 'Casual'

user_stats['category'] = user_stats.apply(categorize_contributor, axis=1)

# ==========================================
# 5. STATISTICS & OUTPUT
# ==========================================
def summarize_activity_counts(activity_counts):
    modes = activity_counts.mode()
    mode_frequency = activity_counts.value_counts().max()
    return {
        'user_count': activity_counts.count(),
        'mean': activity_counts.mean(),
        'median': activity_counts.median(),
        'mode': ', '.join(str(int(value)) for value in modes) if not modes.empty else "N/A",
        'mode_frequency': int(mode_frequency) if pd.notna(mode_frequency) else 0,
        'std_dev': activity_counts.std(),
        'min': activity_counts.min(),
        '25th_percentile': activity_counts.quantile(0.25),
        '75th_percentile': activity_counts.quantile(0.75),
        'max': activity_counts.max()
    }

activity_count_statistics = pd.DataFrame([
    {'group': 'All contributors', **summarize_activity_counts(user_stats['total_activities'])},
    *[
        {'group': category, **summarize_activity_counts(group['total_activities'])}
        for category, group in user_stats.groupby('category', sort=True)
    ]
])

print("\n=== CONTRIBUTOR HEALTH SUMMARY ===")
print(user_stats['category'].value_counts())
print("\n=== ACTIVITIES PER USER (one count per canonical contributor) ===")
print(activity_count_statistics.to_string(index=False, float_format=lambda value: f"{value:.2f}"))

# Save the exports safely using raw string paths
user_stats.to_csv(r"outputs\user_stats.csv", index=False)
activity_count_statistics.to_csv(r"outputs\activity_count_statistics.csv", index=False)
df_filtered.to_csv(r"outputs\bot_activity_filtered.csv", index=False)