import pandas as pd
from github import Github, Auth
from datetime import datetime, timezone
from tqdm import tqdm
import time

# ==========================================
# 0. CONFIGURATION & SETUP
# ==========================================
# Replace with your actual GitHub Personal Access Token
GITHUB_TOKEN = ""
REPO_NAME = "godotengine/godot"

START_DATE = datetime(2025, 9, 23, tzinfo=timezone.utc)
END_DATE = datetime(2026, 9, 23, tzinfo=timezone.utc)

auth = Auth.Token(GITHUB_TOKEN)
g = Github(auth=auth)
repo = g.get_repo(REPO_NAME)

# ==========================================
# 1. FETCHING DATA FROM GITHUB
# ==========================================
def fetch_activities():
    data = []
    
    print("Fetching Commits...")
    commits = repo.get_commits(since=START_DATE, until=END_DATE)
    # Wrap the commits iterator in tqdm for a progress bar
    for commit in tqdm(commits, total=commits.totalCount, desc="Commits"):
        try:
            login = commit.author.login if commit.author else commit.commit.author.name
            email = commit.commit.author.email
            date = commit.commit.author.date
            
            if len(commit.parents) <= 1:
                data.append({"user": login, "email": email, "activity_type": "commit", "date": date})
        except Exception:
            continue

    print("Fetching Issues and PRs...")
    issues = repo.get_issues(state="all", since=START_DATE)
    # Wrap the issues iterator in tqdm
    for issue in tqdm(issues, total=issues.totalCount, desc="Issues & PRs"):
        if issue.created_at > END_DATE:
            continue
            
        login = issue.user.login if issue.user else "Unknown"
        act_type = "pull_request" if issue.pull_request else "issue"
        
        data.append({"user": login, "email": None, "activity_type": act_type, "date": issue.created_at})

    df = pd.DataFrame(data)
    df.to_csv(r"outputs\godot_individual_activity.csv", index=False)
    print("\nData saved to outputs\godot_individual_activity.csv")
    return df

df = fetch_activities()

fetch_activities()