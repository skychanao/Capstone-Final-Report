import pandas as pd

# Load the required datasets
activity_df = pd.read_csv(r'outputs/activity_filtered.csv')
merge_df = pd.read_csv(r'outputs/godot_merge_commits.csv')
user_stats_df = pd.read_csv(r'outputs/user_stats.csv')
ttm_df = pd.read_csv(r'outputs/pr_time_to_merge_details.csv')

# Format dates
activity_df['date'] = pd.to_datetime(activity_df['date'], utc=True)
extraction_date = pd.to_datetime('2026-09-30', utc=True)

# Merge contributory category with activities
activity_df = pd.merge(
    activity_df, 
    user_stats_df[['canonical_user', 'category']], 
    on='canonical_user', 
    how='left'
)

# Select Pull Requests 
prs_only = activity_df[activity_df['activity_type'] == 'pull_request'].copy()
prs_only['pr_url'] = 'https://github.com/godotengine/godot/pull/' + prs_only['identifier'].astype(str)
prs_only['days_open'] = (extraction_date - prs_only['date']).dt.days




# 1: Newcomer PR Reject
# Set of merged PR IDs that are closed but unmerged PRs

merged_pr_ids = set(merge_df['merged_pr_number'].dropna().astype(str).tolist())

newcomer_rejections = prs_only[
    (prs_only['category'] == 'Newcomer') & 
    (~prs_only['identifier'].astype(str).isin(merged_pr_ids)) & 
    (prs_only['state'] == 'closed') & 
    (prs_only['comments'] >= 2) 
]


print("Newcomer Rejections ")
for idx, row in newcomer_rejections.sample(3, random_state=42).iterrows():
    print(f"URL: {row['pr_url']} | Comments: {row['comments']} | Title: {row['title']}")


# 2: Drive-Thru Pull Requests
# Open Pull Requests, more than 90th percentile of all PRs
drivethru_deadlock = prs_only[
    (prs_only['category'] == 'Drive-thru') & 
    (prs_only['state'] == 'open') & 
    (prs_only['days_open'] > 56)
]

print("\n Drive-Thru open PRs")
for idx, row in drivethru_deadlock.sample(3, random_state=10).iterrows():
    print(f"URL: {row['pr_url']} | Age: {row['days_open']} days | Title: {row['title']}")


# 3. PR Bottelneck
# Merged PR, by Repiteo, TtM > 90th percntile
repiteo_bottleneck = ttm_df[
    (ttm_df['committer'] == 'Repiteo') & 
    (ttm_df['time_to_merge_days'] > 56)
].copy()
repiteo_bottleneck['pr_url'] = 'https://github.com/godotengine/godot/pull/' + repiteo_bottleneck['pr_number'].astype(str)

print("\n ")
for idx, row in repiteo_bottleneck.sample(3, random_state=12).iterrows():
    print(f"URL: {row['pr_url']} | TtM: {row['time_to_merge_days']:.1f} days | Title: {row['title_pr']}")