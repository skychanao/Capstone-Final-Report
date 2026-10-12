import pandas as pd
from datetime import datetime, timezone
import time

# Run the fetcher (comment this out and load from CSV on subsequent runs)

df = pd.read_csv("outputs\godot_individual_activity.csv", parse_dates=['date'])


START_DATE = datetime(2025, 9, 23, tzinfo=timezone.utc)
END_DATE = datetime(2026, 9, 23, tzinfo=timezone.utc)
SIX_MONTHS_AGO = datetime(2026, 3, 23, tzinfo=timezone.utc)
# ==========================================
# 2. BOT & ACCOUNT FILTERING
# ==========    ================================
# Measure 1 for Bots: Username contains '[bot]'
def is_bot(user_str):
    return '[bot]' in str(user_str).lower() or str(user_str).lower() == 'godot-engine-bot'


df_bot = df[df['user'].apply(is_bot)].copy()
df_filtered = df[~df['user'].apply(is_bot)].copy()


# Measure 1 for Multiple Accounts: Normalization by Email
# Create a mapping of email addresses to a single primary GitHub username using commit data
email_to_user = df_filtered.dropna(subset=['email']).groupby('email')['user'].first().to_dict()

# Apply the mapping. If an email is found, use the mapped user, otherwise fall back to the original username.
df_filtered['canonical_user'] = df_filtered['email'].map(email_to_user).fillna(df_filtered['user'])

# ==========================================
# 3. CONTRIBUTOR CATEGORIZATION
# ==========================================
user_stats = df_filtered.groupby('canonical_user').agg(
    total_activities=('activity_type', 'count'),
    first_seen=('date', 'min'),
    last_seen=('date', 'max'),
active_months=('date', lambda x: pd.to_datetime(x).dt.strftime('%Y-%m').nunique())
).reset_index()

def categorize_contributor(row):
    # Threshold: >= 50 activities OR active for at least 6 months
    if row['total_activities'] >= 50 or row['active_months'] >= 6:
        return 'Frequent'
    
    # Threshold: First activity within the last 6 months AND <= 5 total activities
    elif row['first_seen'] >= SIX_MONTHS_AGO and row['total_activities'] <= 5:
        return 'Newcomer'
    
    # Threshold: More than 5 activities historically, but zero in the last 6 months
    elif row['first_seen'] < SIX_MONTHS_AGO and row['last_seen'] < SIX_MONTHS_AGO and row['total_activities'] >= 5:
        return 'Dormant'
    
    else:
        return 'Casual'

user_stats['category'] = user_stats.apply(categorize_contributor, axis=1)

print("\n=== CONTRIBUTOR HEALTH SUMMARY ===")
print(user_stats['category'].value_counts())
print(df_bot)

user_stats.to_csv("outputs\user_stats.csv", index = False)
# df_filtered.to_csv("activity_filtered.csv", index=False)
