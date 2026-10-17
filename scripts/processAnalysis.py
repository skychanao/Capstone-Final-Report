import pandas as pd
from pathlib import Path

# Resolve outputs directory whether run from repo root or scripts directory
if Path("outputs").is_dir():
    OUTPUTS_DIR = Path("outputs")
elif (Path(__file__).resolve().parent.parent / "outputs").is_dir():
    OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
else:
    OUTPUTS_DIR = Path("outputs")

input_file = OUTPUTS_DIR / "activity_filtered.csv"
if not input_file.exists():
    input_file = OUTPUTS_DIR / "godot_individual_activity_filtered.csv"

df = pd.read_csv(input_file)

# Filter for Pull Requests
df_prs = df[df['activity_type'] == 'pull_request'].copy()
print("Total Number of PRs:", len(df_prs))

# Ensure date column is datetime object
if 'date' in df_prs.columns:
    df_prs['date'] = pd.to_datetime(df_prs['date'], utc=True)
    df_prs['month_created'] = df_prs['date'].dt.tz_localize(None).dt.to_period('M')


if 'state' in df_prs.columns:
    state_counts = df_prs['state'].value_counts()
    state_pcts = df_prs['state'].value_counts(normalize=True) * 100
    print("\nState of PRs:")
    for state, count in state_counts.items():
        print(f"  {state}: {count} ({state_pcts[state]:.1f}%)")


if 'date' in df_prs.columns:
    # Total PRs by month
    print("\nTotal Pull Requests by month:")
    grouped_total_prs = df_prs.groupby('month_created').size()
    for month, count in grouped_total_prs.items():
        print(f"  {month}: {count}")

    # Open PRs by month
    if 'state' in df_prs.columns:
        open_PRs = df_prs[df_prs['state'] == 'open'].copy()
        
        # Calculate days open (assuming extraction was end of September 2026)
        extraction_date = pd.to_datetime('2026-09-30', utc=True)
        open_PRs['days_open'] = (extraction_date - open_PRs['date']).dt.days
        
        print("\nOpen Pull Request by month:")
        grouped_open_prs = open_PRs.groupby('month_created').size()
        for month, count in grouped_open_prs.items():
            print(f"  {month}: {count}")

        # Summary Table of Total vs Open vs Closed per Month
        monthly_state_df = df_prs.pivot_table(
            index='month_created',
            columns='state',
            values='identifier',
            aggfunc='count',
            fill_value=0
        )
        for s in ['open', 'closed']:
            if s not in monthly_state_df.columns:
                monthly_state_df[s] = 0
                
        monthly_state_df['Total_PRs'] = monthly_state_df.sum(axis=1)
        monthly_state_df['Open_Pct'] = (monthly_state_df['open'] / monthly_state_df['Total_PRs']) * 100

        print("\n=== MONTHLY PULL REQUEST SUMMARY TABLE ===")
        print(f"{'Month':<10} {'Total PRs':<12} {'Open PRs':<10} {'Closed PRs':<12} {'% Open':<8}")
        print("-" * 54)
        for m, row in monthly_state_df.iterrows():
            print(f"{str(m):<10} {int(row['Total_PRs']):<12} {int(row['open']):<10} {int(row['closed']):<12} {row['Open_Pct']:<7.1f}%")
        print("-" * 54)
        tot_prs = len(df_prs)
        tot_open = len(open_PRs)
        tot_closed = tot_prs - tot_open
        print(f"{'Total':<10} {tot_prs:<12} {tot_open:<10} {tot_closed:<12} {tot_open/tot_prs*100:<7.1f}%\n")


if 'comments' in df_prs.columns:
    zero_comments = (df_prs['comments'] == 0).sum()
    has_comments = (df_prs['comments'] > 0).sum()
    total_prs = len(df_prs)
    print("Comment Counts:")
    print(f"  PRs with 0 comments (Unreviewed): {zero_comments} ({zero_comments/total_prs*100:.1f}%)")
    print(f"  PRs with 1+ comments (Reviewed):   {has_comments} ({has_comments/total_prs*100:.1f}%)")