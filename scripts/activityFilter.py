import pandas as pd
from datetime import datetime, timezone

# Activites Queried contains activites that are more than a year ago, this script filters those out

START_DATE = datetime(2025, 9, 23, tzinfo=timezone.utc)
END_DATE = datetime(2026, 9, 23, tzinfo=timezone.utc)

activity_raw_df = pd.read_csv(r"outputs\godot_individual_activity.csv")

activity_raw_df['date'] = pd.to_datetime(activity_raw_df['date'], utc=True)

# Filter the entire dataframe to keep only rows within the date range
activity_filtered_df = activity_raw_df[
    (activity_raw_df['date'] >= START_DATE) & 
    (activity_raw_df['date'] <= END_DATE)
].copy()

activity_filtered_df.to_csv(r"outputs\godot_individual_activity_filtered.csv")