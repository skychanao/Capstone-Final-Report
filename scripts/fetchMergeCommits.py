import os
import re
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from tqdm import tqdm
from github import Github, Auth


REPO_NAME = "godotengine/godot"

# 1-year scope matching project baseline
START_DATE = datetime(2025, 9, 23, tzinfo=timezone.utc)
END_DATE = datetime(2026, 9, 23, tzinfo=timezone.utc)

# Resolve outputs directory whether run from repo root or scripts directory
if Path("outputs").is_dir():
    OUTPUTS_DIR = Path("outputs")
elif (Path(__file__).resolve().parent.parent / "outputs").is_dir():
    OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
else:
    OUTPUTS_DIR = Path("outputs")

# Locate GitHub Token (checks token.txt in workspace, env var, or fallback)
GITHUB_TOKEN = ""
token_locations = [
    Path("token.txt"),
    Path(__file__).resolve().parent / "token.txt",
    Path(__file__).resolve().parent.parent / "token.txt",
    Path(r"E:\TUE\Y3\2IRR80 Capstone\token.txt")
]
for loc in token_locations:
    if loc.exists():
        GITHUB_TOKEN = loc.read_text().strip()
        break

if not GITHUB_TOKEN:
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Authenticate with GitHub API
auth = Auth.Token(GITHUB_TOKEN) if GITHUB_TOKEN else None
g = Github(auth=auth) if auth else Github()
repo = g.get_repo(REPO_NAME)

# Check and display API rate limit
rl = g.get_rate_limit()
print(f"Connected to repo: {REPO_NAME}")
print(f"GitHub API Rate Limit: {rl.rate.remaining}/{rl.rate.limit} requests remaining.\n")


def fetch_merge_commits():
    data = []
    print(f"Fetching merge commits between {START_DATE.date()} and {END_DATE.date()}...")
    
    commits = repo.get_commits(since=START_DATE, until=END_DATE)
    
    # Iterate through commits with tqdm progress bar
    for commit in tqdm(commits, total=commits.totalCount, desc="Scanning Commits for Merges"):
        try:
            # Condition: A merge commit in Git has more than 1 parent
            if len(commit.parents) > 1:
                author_login = commit.author.login if commit.author else commit.commit.author.name
                author_email = commit.commit.author.email
                
                # Committer is often the maintainer executing the merge
                committer_login = commit.committer.login if commit.committer else commit.commit.committer.name
                committer_email = commit.commit.committer.email
                
                title = commit.commit.message.split('\n')[0]
                
                # Extract PR number if title follows standard 'Merge pull request #12345' format
                pr_match = re.search(r'Merge pull request #(\d+)', title)
                pr_number = int(pr_match.group(1)) if pr_match else None

                parent_shas = [p.sha for p in commit.parents]

                data.append({
                    "identifier": commit.sha,
                    "date": commit.commit.author.date,
                    "user": committer_login or author_login,
                    "author": author_login,
                    "author_email": author_email,
                    "committer": committer_login,
                    "committer_email": committer_email,
                    "activity_type": "merge_commit",
                    "title": title,
                    "parents_count": len(commit.parents),
                    "parent_shas": ";".join(parent_shas),
                    "merged_pr_number": pr_number,
                    "comments": 0,
                    "state": "merged"
                })
        except Exception as e:
            continue

    df = pd.DataFrame(data)
    
    output_path = OUTPUTS_DIR / "godot_merge_commits.csv"
    df.to_csv(output_path, index=False)
    
    print("\n" + "=" * 60)
    print("           MERGE COMMITS EXTRACTION SUMMARY                ")
    print("=" * 60)
    print(f"Total merge commits fetched: {len(df)}")
    if not df.empty:
        print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        print("\nTop maintainers merging PRs:")
        print(df['committer'].value_counts().head(10).to_string())
    print("=" * 60)
    print(f"Saved merge commits to: {output_path}")
    
    return df

if __name__ == "__main__":
    fetch_merge_commits()
