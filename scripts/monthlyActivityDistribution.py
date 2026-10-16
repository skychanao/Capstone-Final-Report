import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ==========================================
# 0. CONFIGURATION & PATH RESOLUTION
# ==========================================
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

# ==========================================
# 1. INTRA-MONTH AGGREGATION & TABLE
# ==========================================
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

# Ensure standardized column order
for col in ['commit', 'pull_request', 'issue']:
    if col not in monthly_pivot.columns:
        monthly_pivot[col] = 0
monthly_pivot = monthly_pivot[['commit', 'pull_request', 'issue']]

# Monthly total
monthly_pivot['total'] = monthly_pivot.sum(axis=1)

# Calculate distribution WITHIN each month (percentages summing to 100% per month)
monthly_pivot['commit_pct'] = (monthly_pivot['commit'] / monthly_pivot['total']) * 100
monthly_pivot['pr_pct'] = (monthly_pivot['pull_request'] / monthly_pivot['total']) * 100
monthly_pivot['issue_pct'] = (monthly_pivot['issue'] / monthly_pivot['total']) * 100

# Prepare formatted display table
display_df = pd.DataFrame({
    'Commits': monthly_pivot['commit'],
    'Commits (%)': monthly_pivot['commit_pct'],
    'Pull Requests': monthly_pivot['pull_request'],
    'PR (%)': monthly_pivot['pr_pct'],
    'Issues': monthly_pivot['issue'],
    'Issues (%)': monthly_pivot['issue_pct'],
    'Total Activities': monthly_pivot['total']
}, index=monthly_pivot.index)

# Summary Total / Overall row
overall_commits = monthly_pivot['commit'].sum()
overall_prs = monthly_pivot['pull_request'].sum()
overall_issues = monthly_pivot['issue'].sum()
overall_total = monthly_pivot['total'].sum()

total_row = pd.DataFrame({
    'Commits': [overall_commits],
    'Commits (%)': [(overall_commits / overall_total) * 100],
    'Pull Requests': [overall_prs],
    'PR (%)': [(overall_prs / overall_total) * 100],
    'Issues': [overall_issues],
    'Issues (%)': [(overall_issues / overall_total) * 100],
    'Total Activities': [overall_total]
}, index=['Overall'])

full_table = pd.concat([display_df, total_row])

# Display table
print("\n" + "=" * 80)
print("     INTRA-MONTH ACTIVITY DISTRIBUTION TABLE (Godot Repository)     ")
print("=" * 80)
formatters = {
    'Commits': lambda x: f"{int(x):,}",
    'Commits (%)': lambda x: f"{x:.2f}%",
    'Pull Requests': lambda x: f"{int(x):,}",
    'PR (%)': lambda x: f"{x:.2f}%",
    'Issues': lambda x: f"{int(x):,}",
    'Issues (%)': lambda x: f"{x:.2f}%",
    'Total Activities': lambda x: f"{int(x):,}"
}
print(full_table.to_string(formatters=formatters))
print("=" * 80 + "\n")

# Export to CSV
csv_output_path = OUTPUTS_DIR / "monthly_activity_distribution.csv"
full_table.to_csv(csv_output_path)
print(f"Table successfully saved to: {csv_output_path}")

# ==========================================
# 2. IMAGE 1: Bar CHART (PROPORTIONS WITHIN MONTH)
# ==========================================
months = monthly_pivot.index.tolist()
commit_pcts = monthly_pivot['commit_pct'].values
pr_pcts = monthly_pivot['pr_pct'].values
issue_pcts = monthly_pivot['issue_pct'].values

# Palette definition
color_commits = "#2b5c8f"    # Deep Blue
color_prs = "#389f70"        # Green
color_issues = "#e67e22"     # Orange

fig1, ax1 = plt.subplots(figsize=(12, 7))

x = np.arange(len(months))
width = 0.55

# Stacked bar plot
rects_pr = ax1.bar(x, pr_pcts, width, label='Pull Requests (%)', color=color_prs, alpha=0.95)
rects_issue = ax1.bar(x, issue_pcts, width, bottom=pr_pcts, label='Issues (%)', color=color_issues, alpha=0.95)
rects_commit = ax1.bar(x, commit_pcts, width, bottom=pr_pcts + issue_pcts, label='Commits (%)', color=color_commits, alpha=0.95)

# Annotate percentage labels centered within each stacked segment
for i in range(len(months)):
    # PR segment center
    y_pr = pr_pcts[i] / 2
    ax1.annotate(f"{pr_pcts[i]:.1f}%", xy=(x[i], y_pr), ha='center', va='center',
                 fontsize=8, fontweight='bold', color='white')

    # Issue segment center
    y_issue = pr_pcts[i] + (issue_pcts[i] / 2)
    ax1.annotate(f"{issue_pcts[i]:.1f}%", xy=(x[i], y_issue), ha='center', va='center',
                 fontsize=8, fontweight='bold', color='white')

    # Commit segment center
    y_commit = pr_pcts[i] + issue_pcts[i] + (commit_pcts[i] / 2)
    ax1.annotate(f"{commit_pcts[i]:.1f}%", xy=(x[i], y_commit), ha='center', va='center',
                 fontsize=8, fontweight='bold', color='white')

# Styling and Labels
ax1.set_title("Intra-Month Activity Distribution Trends\n(Godot Repository: Sep 2025 - Sep 2026)", 
              fontsize=13, fontweight='bold', pad=15)
ax1.set_xlabel("Month (Year-Month)", fontsize=11, fontweight='semibold', labelpad=10)
ax1.set_ylabel("Share of Monthly Activities (%)", fontsize=11, fontweight='semibold')

# Axis limits and ticks (100% total height for stacked proportions)
ax1.set_ylim(0, 105)
ax1.set_yticks(np.arange(0, 101, 10))
ax1.set_yticklabels([f"{y}%" for y in np.arange(0, 101, 10)])

ax1.set_xticks(x)
ax1.set_xticklabels(months, rotation=45)
ax1.legend(loc='upper right', frameon=True, facecolor='#f8f9fa', edgecolor='#d1d5db', fontsize=10)
ax1.grid(True, linestyle='--', alpha=0.5, axis='y')

plt.tight_layout()

# Save single image
image1_path = OUTPUTS_DIR / "monthly_activity_distribution.png"
fig1.savefig(image1_path, dpi=300, bbox_inches='tight')
plt.close(fig1)

print(f"Image (Stacked Bar Chart) saved to: {image1_path}")

# ==========================================
# 3. IMAGE 2: LINE CHART (ACTIVITY COUNTS WITHIN MONTH)
# ==========================================

fig2, ax2 = plt.subplots(figsize=(12, 7))

# Multi-line plot showing raw activity counts across months
ax2.plot(months, monthly_pivot['pull_request'], marker='o', markersize=6, linewidth=2.5,
         color=color_prs, label='Pull Requests', alpha=0.95)
ax2.plot(months, monthly_pivot['issue'], marker='s', markersize=6, linewidth=2.5,
         color=color_issues, label='Issues', alpha=0.95)
ax2.plot(months, monthly_pivot['commit'], marker='^', markersize=6, linewidth=2.5,
         color=color_commits, label='Commits', alpha=0.95)

# Annotate counts at each data point for easy reading
for i, m in enumerate(months):
    pr_val = int(monthly_pivot['pull_request'].iloc[i])
    issue_val = int(monthly_pivot['issue'].iloc[i])
    commit_val = int(monthly_pivot['commit'].iloc[i])
    
    ax2.annotate(f"{pr_val}", xy=(i, pr_val), xytext=(0, 6),
                 textcoords="offset points", ha='center', fontsize=8, fontweight='bold', color=color_prs)
    ax2.annotate(f"{issue_val}", xy=(i, issue_val), xytext=(0, 6),
                 textcoords="offset points", ha='center', fontsize=8, fontweight='bold', color=color_issues)
    ax2.annotate(f"{commit_val}", xy=(i, commit_val), xytext=(0, -12),
                 textcoords="offset points", ha='center', fontsize=8, fontweight='bold', color=color_commits)

ax2.set_title("Monthly Activity Volume Trends by Type\n(Godot Repository: Sep 2025 - Sep 2026)", 
              fontsize=13, fontweight='bold', pad=15)
ax2.set_xlabel("Month (Year-Month)", fontsize=11, fontweight='semibold', labelpad=10)
ax2.set_ylabel("Number of Activities (Count)", fontsize=11, fontweight='semibold')
ax2.set_ylim(0, monthly_pivot['pull_request'].max() * 1.15)
ax2.legend(loc='lower left', frameon=True, facecolor='#f8f9fa', edgecolor='#d1d5db', fontsize=10)
ax2.grid(True, linestyle='--', alpha=0.5)
ax2.tick_params(axis='x', rotation=45)

plt.tight_layout()
image2_path = OUTPUTS_DIR / "monthly_activity_distribution_counts.png"
fig2.savefig(image2_path, dpi=300, bbox_inches='tight')
plt.close(fig2)
print(f"Image 2 (Line Chart Counts) saved to: {image2_path}")
