import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


# Resolve outputs directory whether run from repo root or scripts directory
if Path("outputs").is_dir():
    OUTPUTS_DIR = Path("outputs")
elif (Path(__file__).resolve().parent.parent / "outputs").is_dir():
    OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
else:
    OUTPUTS_DIR = Path("outputs")

# Prefer final filtered dataset (activity_filtered.csv), fallback to bot_activity_filtered.csv or godot_individual_activity_filtered.csv
input_file = OUTPUTS_DIR / "activity_filtered.csv"
if not input_file.exists():
    input_file = OUTPUTS_DIR / "bot_activity_filtered.csv"
if not input_file.exists():
    input_file = OUTPUTS_DIR / "godot_individual_activity_filtered.csv"

print(f"Loading activity data from: {input_file}")
df = pd.read_csv(input_file, parse_dates=['date'])
df['date'] = pd.to_datetime(df['date'], utc=True)

# Load merge commits if available
merge_file = OUTPUTS_DIR / "godot_merge_commits.csv"
has_merges = False
if merge_file.exists():
    print(f"Loading merge commits from: {merge_file}")
    df_merges = pd.read_csv(merge_file, parse_dates=['date'])
    df_merges['date'] = pd.to_datetime(df_merges['date'], utc=True)
    df_merges['activity_type'] = 'merge_commit'
    
    # Align date range with main dataset
    min_date = df['date'].min()
    max_date = df['date'].max()
    df_merges = df_merges[(df_merges['date'] >= min_date) & (df_merges['date'] <= max_date)]
    
    # Combine datasets
    df = pd.concat([
        df[['date', 'activity_type', 'identifier']],
        df_merges[['date', 'activity_type', 'identifier']]
    ], ignore_index=True)
    has_merges = True
    print(f"Successfully merged {len(df_merges)} merge commits into activities dataset.")

# Extract Year-Month (YYYY-MM)
df['year_month'] = df['date'].dt.strftime('%Y-%m')

# Pivot table: counts of each activity type per month
monthly_pivot = df.pivot_table(
    index='year_month', 
    columns='activity_type', 
    values='identifier', 
    aggfunc='count', 
    fill_value=0
)

# Standardize columns
desired_cols = ['pull_request', 'issue', 'commit']
if has_merges:
    desired_cols.append('merge_commit')

for col in desired_cols:
    if col not in monthly_pivot.columns:
        monthly_pivot[col] = 0
monthly_pivot = monthly_pivot[desired_cols]

# Monthly total
monthly_pivot['total'] = monthly_pivot.sum(axis=1)

# Calculate distribution WITHIN each month (percentages summing to 100% per month)
monthly_pivot['commit_pct'] = (monthly_pivot['commit'] / monthly_pivot['total']) * 100
monthly_pivot['pr_pct'] = (monthly_pivot['pull_request'] / monthly_pivot['total']) * 100
monthly_pivot['issue_pct'] = (monthly_pivot['issue'] / monthly_pivot['total']) * 100
if has_merges:
    monthly_pivot['merge_commit_pct'] = (monthly_pivot['merge_commit'] / monthly_pivot['total']) * 100

# Prepare display table
display_data = {
    'Commits': monthly_pivot['commit'],
    'Commits (%)': monthly_pivot['commit_pct'],
}
if has_merges:
    display_data['Merge Commits'] = monthly_pivot['merge_commit']
    display_data['Merge Commits (%)'] = monthly_pivot['merge_commit_pct']

display_data.update({
    'Pull Requests': monthly_pivot['pull_request'],
    'PR (%)': monthly_pivot['pr_pct'],
    'Issues': monthly_pivot['issue'],
    'Issues (%)': monthly_pivot['issue_pct'],
    'Total Activities': monthly_pivot['total']
})

display_df = pd.DataFrame(display_data, index=monthly_pivot.index)

# Summary Total / Overall row
overall_total = monthly_pivot['total'].sum()
overall_commits = monthly_pivot['commit'].sum()
overall_prs = monthly_pivot['pull_request'].sum()
overall_issues = monthly_pivot['issue'].sum()

total_data = {
    'Commits': [overall_commits],
    'Commits (%)': [(overall_commits / overall_total) * 100],
}
if has_merges:
    overall_merges = monthly_pivot['merge_commit'].sum()
    total_data['Merge Commits'] = [overall_merges]
    total_data['Merge Commits (%)'] = [(overall_merges / overall_total) * 100]

total_data.update({
    'Pull Requests': [overall_prs],
    'PR (%)': [(overall_prs / overall_total) * 100],
    'Issues': [overall_issues],
    'Issues (%)': [(overall_issues / overall_total) * 100],
    'Total Activities': [overall_total]
})

total_row = pd.DataFrame(total_data, index=['Overall'])
full_table = pd.concat([display_df, total_row])

# Display table
print("\n" + "=" * 90)
print("       INTRA-MONTH ACTIVITY DISTRIBUTION TABLE (Godot Repository)       ")
print("=" * 90)
formatters = {
    'Commits': lambda x: f"{int(x):,}",
    'Commits (%)': lambda x: f"{x:.2f}%",
    'Merge Commits': lambda x: f"{int(x):,}",
    'Merge Commits (%)': lambda x: f"{x:.2f}%",
    'Pull Requests': lambda x: f"{int(x):,}",
    'PR (%)': lambda x: f"{x:.2f}%",
    'Issues': lambda x: f"{int(x):,}",
    'Issues (%)': lambda x: f"{x:.2f}%",
    'Total Activities': lambda x: f"{int(x):,}"
}
print(full_table.to_string(formatters=formatters))
print("=" * 90 + "\n")

# Export to CSV
csv_output_path = OUTPUTS_DIR / "monthly_activity_distribution.csv"
full_table.to_csv(csv_output_path)
print(f"Table successfully saved to: {csv_output_path}")

"""Graph 1: bar chart"""
months = monthly_pivot.index.tolist()

# Calculate proportions strictly across core activities (excluding merge commits)
core_totals = monthly_pivot['pull_request'] + monthly_pivot['issue'] + monthly_pivot['commit']
pr_bar_pcts = (monthly_pivot['pull_request'] / core_totals * 100).values
issue_bar_pcts = (monthly_pivot['issue'] / core_totals * 100).values
commit_bar_pcts = (monthly_pivot['commit'] / core_totals * 100).values

# Palette definition
color_commits = "#2b5c8f"    # Deep Blue
color_merges = "#9b59b6"     # Purple
color_prs = "#389f70"        # Green
color_issues = "#e67e22"     # Orange

fig1, ax1 = plt.subplots(figsize=(13, 7))
x = np.arange(len(months))
width = 0.55

# Stacked bar plot (Pull Requests + Issues + Commits)
rects_pr = ax1.bar(x, pr_bar_pcts, width, label='Pull Requests (%)', color=color_prs, alpha=0.95)
rects_issue = ax1.bar(x, issue_bar_pcts, width, bottom=pr_bar_pcts, label='Issues (%)', color=color_issues, alpha=0.95)
bottom_for_commit = pr_bar_pcts + issue_bar_pcts
rects_commit = ax1.bar(x, commit_bar_pcts, width, bottom=bottom_for_commit, label='Commits (%)', color=color_commits, alpha=0.95)

# Annotate percentage labels centered within each stacked segment
for i in range(len(months)):
    # PR segment center
    if pr_bar_pcts[i] >= 5:
        ax1.annotate(f"{pr_bar_pcts[i]:.1f}%", xy=(x[i], pr_bar_pcts[i] / 2), ha='center', va='center',
                     fontsize=8, fontweight='bold', color='white')

    # Issue segment center
    if issue_bar_pcts[i] >= 5:
        ax1.annotate(f"{issue_bar_pcts[i]:.1f}%", xy=(x[i], pr_bar_pcts[i] + (issue_bar_pcts[i] / 2)), ha='center', va='center',
                     fontsize=8, fontweight='bold', color='white')

    # Commit segment center
    if commit_bar_pcts[i] >= 5:
        ax1.annotate(f"{commit_bar_pcts[i]:.1f}%", xy=(x[i], bottom_for_commit[i] + (commit_bar_pcts[i] / 2)), ha='center', va='center',
                     fontsize=8, fontweight='bold', color='white')

ax1.set_title("Intra-Month Activity Distribution Trends (Core Activities)\n(Godot Repository: Sep 2025 - Sep 2026)", 
              fontsize=13, fontweight='bold', pad=15)
ax1.set_xlabel("Month (Year-Month)", fontsize=11, fontweight='semibold', labelpad=10)
ax1.set_ylabel("Share of Monthly Core Activities (%)", fontsize=11, fontweight='semibold')
ax1.set_ylim(0, 105)
ax1.set_yticks(np.arange(0, 101, 10))
ax1.set_yticklabels([f"{y}%" for y in np.arange(0, 101, 10)])
ax1.set_xticks(x)
ax1.set_xticklabels(months, rotation=45)
ax1.legend(loc='upper right', frameon=True, facecolor='#f8f9fa', edgecolor='#d1d5db', fontsize=10)
ax1.grid(True, linestyle='--', alpha=0.5, axis='y')

plt.tight_layout()
image1_path = OUTPUTS_DIR / "monthly_activity_distribution.png"
fig1.savefig(image1_path, dpi=300, bbox_inches='tight')
plt.close(fig1)
print(f"Image 1 (Stacked Bar Chart, Excl. Merges) saved to: {image1_path}")

"""Graph 2: line chart"""
fig2, ax2 = plt.subplots(figsize=(13, 7.5))

# Multi-line plot showing raw activity counts across months
ax2.plot(months, monthly_pivot['pull_request'], marker='o', markersize=6, linewidth=2.5,
         color=color_prs, label='Pull Requests', alpha=0.95)
if has_merges:
    ax2.plot(months, monthly_pivot['merge_commit'], marker='D', markersize=6, linewidth=2.5,
             color=color_merges, label='Merge Commits', alpha=0.95)
ax2.plot(months, monthly_pivot['issue'], marker='s', markersize=6, linewidth=2.5,
         color=color_issues, label='Issues', alpha=0.95)
ax2.plot(months, monthly_pivot['commit'], marker='^', markersize=6, linewidth=2.5,
         color=color_commits, label='Commits (Non-Merge)', alpha=0.95)

# Annotate counts at each data point for easy reading
for i, m in enumerate(months):
    pr_val = int(monthly_pivot['pull_request'].iloc[i])
    issue_val = int(monthly_pivot['issue'].iloc[i])
    commit_val = int(monthly_pivot['commit'].iloc[i])
    
    ax2.annotate(f"{pr_val}", xy=(i, pr_val), xytext=(0, 6),
                 textcoords="offset points", ha='center', fontsize=8, fontweight='bold', color=color_prs)
    ax2.annotate(f"{issue_val}", xy=(i, issue_val), xytext=(0, -13),
                 textcoords="offset points", ha='center', fontsize=8, fontweight='bold', color=color_issues)
    ax2.annotate(f"{commit_val}", xy=(i, commit_val), xytext=(-6, -13),
                 textcoords="offset points", ha='center', fontsize=8, fontweight='bold', color=color_commits)
    
    if has_merges:
        merge_val = int(monthly_pivot['merge_commit'].iloc[i])
        ax2.annotate(f"{merge_val}", xy=(i, merge_val), xytext=(6, 6),
                     textcoords="offset points", ha='center', fontsize=8, fontweight='bold', color=color_merges)

max_val = monthly_pivot[['pull_request', 'issue', 'commit', 'merge_commit']].max().max() if has_merges else monthly_pivot['pull_request'].max()

ax2.set_title("Monthly Activity Volume Trends by Type (Including Merge Commits)\n(Godot Repository: Sep 2025 - Sep 2026)", 
              fontsize=13, fontweight='bold', pad=15)
ax2.set_xlabel("Month (Year-Month)", fontsize=11, fontweight='semibold', labelpad=10)
ax2.set_ylabel("Number of Activities (Count)", fontsize=11, fontweight='semibold')
ax2.set_ylim(0, max_val * 1.15)
ax2.legend(loc='lower left', frameon=True, facecolor='#f8f9fa', edgecolor='#d1d5db', fontsize=10)
ax2.grid(True, linestyle='--', alpha=0.5)
ax2.tick_params(axis='x', rotation=45)

plt.tight_layout()
image2_path = OUTPUTS_DIR / "monthly_activity_distribution_counts.png"
fig2.savefig(image2_path, dpi=300, bbox_inches='tight')
plt.close(fig2)
print(f"Image 2 (Line Chart Counts with Merge Commits) saved to: {image2_path}")
