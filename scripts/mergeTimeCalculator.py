import os
import re
import pandas as pd
import numpy as np
from pathlib import Path


if Path("outputs").is_dir():
    OUTPUTS_DIR = Path("outputs")
elif (Path(__file__).resolve().parent.parent / "outputs").is_dir():
    OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
else:
    OUTPUTS_DIR = Path("outputs")

# Load Datasets
act_file = OUTPUTS_DIR / "activity_filtered.csv"
if not act_file.exists():
    act_file = OUTPUTS_DIR / "godot_individual_activity_filtered.csv"

merge_file = OUTPUTS_DIR / "godot_merge_commits.csv"

if not merge_file.exists():
    raise FileNotFoundError(f"Could not find merge commits file at: {merge_file}. Run fetchMergeCommits.py first.")

print(f"Loading Pull Requests from: {act_file}")
df_activity = pd.read_csv(act_file, parse_dates=['date'])
print(f"Loading Merge Commits from:  {merge_file}")
df_merge_commits = pd.read_csv(merge_file, parse_dates=['date'])

# Extract Data
# Separate Pull Requests
prs = df_activity[df_activity['activity_type'] == 'pull_request'].copy()

# Ensure datetime objects with UTC timezone
prs['date'] = pd.to_datetime(prs['date'], utc=True)
df_merge_commits['date'] = pd.to_datetime(df_merge_commits['date'], utc=True)

# Extract PR Number from PR dataset (identifier column holds PR number)
prs['pr_number'] = pd.to_numeric(prs['identifier'], errors='coerce')
prs = prs.dropna(subset=['pr_number'])
prs['pr_number'] = prs['pr_number'].astype(int)

# Extract PR Number from Merge Commits dataset
# (Supports 'merged_pr_number', 'title', or 'message' columns)
if 'merged_pr_number' in df_merge_commits.columns and df_merge_commits['merged_pr_number'].notnull().any():
    df_merge_commits['pr_number'] = pd.to_numeric(df_merge_commits['merged_pr_number'], errors='coerce')
elif 'title' in df_merge_commits.columns:
    df_merge_commits['pr_number'] = df_merge_commits['title'].str.extract(r'#(\d+)')[0].astype(float)
elif 'message' in df_merge_commits.columns:
    df_merge_commits['pr_number'] = df_merge_commits['message'].str.extract(r'#(\d+)')[0].astype(float)
else:
    raise ValueError("Merge commits dataset does not contain 'merged_pr_number', 'title', or 'message'.")

merge_commits = df_merge_commits.dropna(subset=['pr_number']).copy()
merge_commits['pr_number'] = merge_commits['pr_number'].astype(int)

# In case of duplicate merge entries for same PR, keep the earliest valid merge commit
merge_commits = merge_commits.sort_values(by=['pr_number', 'date']).drop_duplicates(subset=['pr_number'], keep='first')


# JOIN PRs and Merge Commits
merged_data = pd.merge(
    prs, 
    merge_commits, 
    on='pr_number', 
    suffixes=('_pr', '_merge')
)

# Calculate Time-to-Merge (Commit Date - PR Creation Date)
merged_data['time_to_merge_hours'] = (merged_data['date_merge'] - merged_data['date_pr']).dt.total_seconds() / 3600.0
merged_data['time_to_merge_days'] = merged_data['time_to_merge_hours'] / 24.0

# Filter valid positive durations (guard against clock discrepancies)
valid_ttm = merged_data[merged_data['time_to_merge_days'] >= 0].copy()

# Statistical Analysis
count_matched = len(valid_ttm)
mean_days = valid_ttm['time_to_merge_days'].mean()
std_days = valid_ttm['time_to_merge_days'].std()
min_days = valid_ttm['time_to_merge_days'].min()
p25_days = valid_ttm['time_to_merge_days'].quantile(0.25)
median_days = valid_ttm['time_to_merge_days'].median()
p75_days = valid_ttm['time_to_merge_days'].quantile(0.75)
p90_days = valid_ttm['time_to_merge_days'].quantile(0.90)
p95_days = valid_ttm['time_to_merge_days'].quantile(0.95)
max_days = valid_ttm['time_to_merge_days'].max()

# Resolution latency buckets
b_under_24h = (valid_ttm['time_to_merge_days'] < 1).sum()
b_1_to_7d = ((valid_ttm['time_to_merge_days'] >= 1) & (valid_ttm['time_to_merge_days'] < 7)).sum()
b_7_to_30d = ((valid_ttm['time_to_merge_days'] >= 7) & (valid_ttm['time_to_merge_days'] < 30)).sum()
b_30_to_90d = ((valid_ttm['time_to_merge_days'] >= 30) & (valid_ttm['time_to_merge_days'] < 90)).sum()
b_over_90d = (valid_ttm['time_to_merge_days'] >= 90).sum()



# Merge Commit contirbutors
print("\n" + "-" * 65)
print("             USERS WHO PERFORMED MERGE COMMITS               ")
print("-" * 65)
unique_mergers = sorted(set(df_merge_commits['author'].dropna().unique()).union(set(df_merge_commits['committer'].dropna().unique())))
print(f"Unique Maintainers: {', '.join(unique_mergers)}\n")

print("Merge Commits by Contributor:")
for user, count in df_merge_commits['author'].value_counts().items():
    print(f"  {user:<15} {count:>5} merges ({count/len(df_merge_commits)*100:5.1f}%)")


print("=" * 65)
print(f"Total Pull Requests in dataset:          {len(prs):,}")
print(f"Total Merge Commits identified:          {len(df_merge_commits):,}")
print(f"Successfully matched PRs:                {count_matched:,} ({count_matched/len(prs)*100:.1f}%)")
print("-" * 65)
print(f"Mean:                                   {mean_days:.2f} days ({mean_days*24:.1f} hours)")
print(f"Median:                                  {median_days:.2f} days ({median_days*24:.1f} hours)")
print(f"Standard Deviation:                      {std_days:.2f} days")
print(f"25th Percentile (Fast Track):            {p25_days:.2f} days ({p25_days*24:.1f} hours)")
print(f"75th Percentile (Delayed Review):        {p75_days:.2f} days")
print(f"90th Percentile (Stagnant / Long-Tail):  {p90_days:.2f} days")
print(f"95th Percentile:                         {p95_days:.2f} days")
print(f"Fastest Merge:                           {min_days*24:.2f} hours")
print(f"Slowest Merge:                           {max_days:.1f} days")


# Combine PR with Merge Commit, compute Time to merge
user_stats_file = OUTPUTS_DIR / "user_stats.csv"
if user_stats_file.exists() and 'canonical_user' in prs.columns:
    user_stats = pd.read_csv(user_stats_file)
    
    # Mark which PRs were successfully merged
    merged_pr_set = set(valid_ttm['pr_number'].unique())
    prs['is_merged'] = prs['pr_number'].isin(merged_pr_set)
    
    prs_cat = pd.merge(prs, user_stats[['canonical_user', 'category']], on='canonical_user', how='left')
    valid_ttm_cat = pd.merge(valid_ttm, user_stats[['canonical_user', 'category']], on='canonical_user', how='left')
    
    total_prs = prs_cat.groupby('category').size()
    merged_prs = prs_cat[prs_cat['is_merged']].groupby('category').size()
    unmerged_prs = prs_cat[~prs_cat['is_merged']].groupby('category').size()
    
    ttm_metrics = valid_ttm_cat.groupby('category')['time_to_merge_days'].agg(
        Median_Days='median',
        Mean_Days='mean',
        P75_Days=lambda x: x.quantile(0.75),
        P90_Days=lambda x: x.quantile(0.90)
    )
    
    cat_summary = pd.DataFrame({
        'Total PRs': total_prs,
        'Merged PRs': merged_prs,
        'Unmerged PRs': unmerged_prs,
        'Merge %': (merged_prs / total_prs) * 100,
        'Unmerged %': (unmerged_prs / total_prs) * 100,
        'Median TtM': ttm_metrics['Median_Days'],
        'Mean TtM': ttm_metrics['Mean_Days'],
        'P75 TtM': ttm_metrics['P75_Days'],
        'P90 TtM': ttm_metrics['P90_Days']
    }).fillna(0)
    
    tot_row = pd.DataFrame({
        'Total PRs': [len(prs)],
        'Merged PRs': [len(valid_ttm)],
        'Unmerged PRs': [len(prs) - len(valid_ttm)],
        'Merge %': [(len(valid_ttm) / len(prs)) * 100],
        'Unmerged %': [((len(prs) - len(valid_ttm)) / len(prs)) * 100],
        'Median TtM': [valid_ttm['time_to_merge_days'].median()],
        'Mean TtM': [valid_ttm['time_to_merge_days'].mean()],
        'P75 TtM': [valid_ttm['time_to_merge_days'].quantile(0.75)],
        'P90 TtM': [valid_ttm['time_to_merge_days'].quantile(0.90)]
    }, index=['Overall'])
    
    full_cat_summary = pd.concat([cat_summary, tot_row])
    
    print("\n" + "-" * 85)
    print("      PULL REQUEST RESOLUTION & TIME-TO-MERGE BY CONTRIBUTOR CATEGORY       ")
    print("-" * 85)
    print(full_cat_summary.to_string(formatters={
        'Total PRs': lambda x: f"{int(x):,}",
        'Merged PRs': lambda x: f"{int(x):,}",
        'Unmerged PRs': lambda x: f"{int(x):,}",
        'Merge %': lambda x: f"{x:.1f}%",
        'Unmerged %': lambda x: f"{x:.1f}%",
        'Median TtM': lambda x: f"{x:.2f} days",
        'Mean TtM': lambda x: f"{x:.2f} days",
        'P75 TtM': lambda x: f"{x:.2f} days",
        'P90 TtM': lambda x: f"{x:.2f} days"
    }))
    
    output_cat_resolution = OUTPUTS_DIR / "pr_resolution_by_category.csv"
    full_cat_summary.to_csv(output_cat_resolution)

# 5. Users who performed merge commits
print("\n Merge Commits by Committer:")
for user, count in df_merge_commits['author'].value_counts().items():
    print(f"  {user:<15} {count:>5} merges ({count/len(df_merge_commits)*100:5.1f}%)")



output_ttm_details = OUTPUTS_DIR / "pr_time_to_merge_details.csv"
export_cols = [c for c in [
    'pr_number', 'title_pr', 'user_pr', 'canonical_user',
    'date_pr', 'date_merge', 'time_to_merge_days', 'time_to_merge_hours',
    'committer', 'identifier_merge'
] if c in valid_ttm.columns]
valid_ttm[export_cols].to_csv(output_ttm_details, index=False)

# Export Summary Stats
stats_df = pd.DataFrame([{
    'metric': 'Total Matched PRs', 'value': count_matched
}, {
    'metric': 'Mean TtM (days)', 'value': round(mean_days, 2)
}, {
    'metric': 'Median TtM (days)', 'value': round(median_days, 2)
}, {
    'metric': '25th Percentile (days)', 'value': round(p25_days, 2)
}, {
    'metric': '75th Percentile (days)', 'value': round(p75_days, 2)
}, {
    'metric': '90th Percentile (days)', 'value': round(p90_days, 2)
}, {
    'metric': 'Min TtM (days)', 'value': round(min_days, 2)
}, {
    'metric': 'Max TtM (days)', 'value': round(max_days, 2)
}])
output_ttm_stats = OUTPUTS_DIR / "time_to_merge_statistics.csv"
stats_df.to_csv(output_ttm_stats, index=False)

print(f"Details exported to: {output_ttm_details}")
print(f"Summary exported to: {output_ttm_stats}")