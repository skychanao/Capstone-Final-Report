import pandas as pd

# Load the dataset
df = pd.read_csv(r"outputs\godot_individual_activity_filtered.csv")

"""Compre emails"""

# Remove rows where email or user is missing
df_valid = df.dropna(subset=['user', 'email']).copy()

# # Standardize formatting (strip whitespace and lowercase emails)
df_valid['user'] = df_valid['user'].str.strip()
df_valid['email'] = df_valid['email'].str.strip().str.lower()


# # Group by the GitHub username and get all unique emails tied to it
user_groups = df_valid.groupby('user')['email'].unique()

# # Filter for users that have MORE than 1 distinct email address
shared_accounts = user_groups[user_groups.apply(len) > 1]

print(f"Found {len(shared_accounts)} accounts associated with multiple emails.\n")

# # Print the first 15 results to review manually
count = 0
for user, emails in shared_accounts.items():
    print(f"Account: '{user}' -> Emails: {list(emails)}")
    count += 1
    if count >= 15:
        break
print("\n")

"""Compare Name"""


# Look for usernames containing business/team words
keywords = ['studio']
studios = df[df['user'].str.lower().str.contains('|'.join(keywords), na=False)]

print(studios['user'].unique())