import re
import pandas as pd

# ==========================================
# MULTIPLE ACCOUNT DETECTION (Identity Aliasing)
# ==========================================
# We apply two distinct measures to group multiple accounts belonging to the same human.

df = pd.read_csv(r"outputs\godot_individual_activity_filtered.csv", parse_dates=['date'])
df['date'] = pd.to_datetime(df['date'], utc=True)

def is_bot(user_str):
    user_lower = str(user_str).lower()
    return '[bot]' in user_lower or user_lower == 'ghost' 

# Separate bots from humans
df_bot = df[df['user'].apply(is_bot)].copy()
df_filtered = df[~df['user'].apply(is_bot)].copy()

# Measure 1: Exact Email Matching
df_valid = df.dropna(subset=['email', 'user']).copy()
df_invalid = df_filtered['email'].isna()
print(len(df_valid))
print(len(df_invalid))

df_valid['email'] = df_valid['email'].str.strip().str.lower()
df_valid['user'] = df_valid['user'].str.strip()
email_groups = df_valid.groupby('email')['user'].unique()
shared_emails = email_groups[email_groups.apply(len) > 1]
print(f"Found {len(shared_emails)} emails associated with multiple distinct usernames.")
for email, users in shared_emails.items():
    print(f"Email: {email} -> Usernames: {list(users)}")

email_to_user = df_filtered.dropna(subset=['email']).groupby('email')['user'].first().to_dict()
df_filtered['canonical_user'] = df_filtered['email'].map(email_to_user).fillna(df_filtered['user'])

# Measure 2: Username String Normalization
def normalize_username(name):
    # Strip all non-alphanumeric characters and convert to lowercase
    return re.sub(r'[^a-zA-Z0-9]', '', str(name)).lower()

# Create a temporary column with the simplified names
df_filtered['simplified_name'] = df_filtered['canonical_user'].apply(normalize_username)

# Create a mapping from the simplified name to the primary canonical_user
simplified_to_canonical = df_filtered.groupby('simplified_name')['canonical_user'].first().to_dict()

df_filtered['canonical_user'] = df_filtered['simplified_name'].map(simplified_to_canonical)

# Clean up the temporary column
df_filtered = df_filtered.drop(columns=['simplified_name'])

merged_accounts = df_filtered.groupby('canonical_user')['user'].unique()

# Filter for cases where one canonical user has more than 1 original username
aliased_users = merged_accounts[merged_accounts.apply(len) > 1]

print(f"\nAccount normalization complete.")
print(f"Found {len(aliased_users)} developers using multiple accounts.\n")

print("=== EXAMPLES OF MERGED ACCOUNTS ===")

# Print the first 10 examples to use in your report
for canonical, originals in aliased_users.head(10).items():
    print(f"Canonical User: '{canonical}' is used by accounts: {list(originals)}")