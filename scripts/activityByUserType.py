import pandas as pd
from pathlib import Path


# Resolve outputs directory whether run from repo root or scripts directory
if Path("outputs").is_dir():
    OUTPUTS_DIR = Path("outputs")
elif (Path(__file__).resolve().parent.parent / "outputs").is_dir():
    OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
else:
    OUTPUTS_DIR = Path("outputs")

# 1. Load user categories and activities
user_stats_path = OUTPUTS_DIR / "user_stats.csv"
activity_path = OUTPUTS_DIR / "activity_filtered.csv"
if not activity_path.exists():
    activity_path = OUTPUTS_DIR / "godot_individual_activity_filtered.csv"

print(f"Loading users from:      {user_stats_path}")
print(f"Loading activities from: {activity_path}\n")

df_users = pd.read_csv(user_stats_path)
df_activity = pd.read_csv(activity_path)


# Group directly from user_stats
user_type_summary = df_users.groupby('category').agg(
    user_count=('canonical_user', 'count'),
    total_activities=('total_activities', 'sum'),
    avg_per_user=('total_activities', 'mean'),
    median_per_user=('total_activities', 'median')
).reset_index()

total_all_activities = user_type_summary['total_activities'].sum()
user_type_summary['pct_of_all_activities'] = (user_type_summary['total_activities'] / total_all_activities) * 100

# Sort by highest activity volume
user_type_summary = user_type_summary.sort_values(by='total_activities', ascending=False)

print("=" * 70)
print("             NUMBER OF ACTIVITIES PER USER TYPE              ")
print("=" * 70)
print(f"{'User Type (Category)':<18} {'Users':<8} {'Total Activities':<18} {'% Share':<10} {'Avg/User':<10}")
print("-" * 70)
for _, row in user_type_summary.iterrows():
    print(f"{row['category']:<18} {int(row['user_count']):<8,d} {int(row['total_activities']):<18,d} {row['pct_of_all_activities']:<9.1f}% {row['avg_per_user']:<9.1f}")
print("-" * 70)
tot_users = user_type_summary['user_count'].sum()
print(f"{'Total':<18} {int(tot_users):<8,d} {int(total_all_activities):<18,d} {'100.0%':<10} {total_all_activities/tot_users:<9.1f}\n")



# Merge individual activities with their user category
merged = pd.merge(df_activity, df_users[['canonical_user', 'category']], on='canonical_user', how='left')

# Pivot table: Commits, PRs, and Issues per User Type
breakdown = merged.pivot_table(
    index='category',
    columns='activity_type',
    values='identifier',
    aggfunc='count',
    fill_value=0
)

# Ensure standard column order
for col in ['commit', 'pull_request', 'issue']:
    if col not in breakdown.columns:
        breakdown[col] = 0
breakdown = breakdown[['commit', 'pull_request', 'issue']]

# Add total activities and user counts
breakdown['Total Activities'] = breakdown.sum(axis=1)
user_counts = df_users.groupby('category')['canonical_user'].count().rename('User Count')
full_breakdown = pd.concat([user_counts, breakdown], axis=1)
full_breakdown = full_breakdown.sort_values(by='Total Activities', ascending=False)
full_breakdown.columns = ['Users', 'Commits', 'Pull Requests', 'Issues', 'Total Activities']

# Add overall total row
overall_row = pd.DataFrame({
    'Users': [full_breakdown['Users'].sum()],
    'Commits': [full_breakdown['Commits'].sum()],
    'Pull Requests': [full_breakdown['Pull Requests'].sum()],
    'Issues': [full_breakdown['Issues'].sum()],
    'Total Activities': [full_breakdown['Total Activities'].sum()]
}, index=['Overall'])

full_breakdown_table = pd.concat([full_breakdown, overall_row])

print("=" * 70)
print("         ACTIVITY TYPE BREAKDOWN PER USER CATEGORY           ")
print("=" * 70)
print(full_breakdown_table.to_string(formatters={
    'Users': lambda x: f"{int(x):,}",
    'Commits': lambda x: f"{int(x):,}",
    'Pull Requests': lambda x: f"{int(x):,}",
    'Issues': lambda x: f"{int(x):,}",
    'Total Activities': lambda x: f"{int(x):,}"
}))
print("=" * 70 + "\n")


csv_output = OUTPUTS_DIR / "activity_by_user_type.csv"
full_breakdown_table.to_csv(csv_output)
print(f"Summary table saved to: {csv_output}")
