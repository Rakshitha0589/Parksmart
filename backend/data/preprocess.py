
from pathlib import Path
import pandas as pd

# Project directories
BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "datasets" / "raw"
PROCESSED_DIR = BASE_DIR / "datasets" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

INPUT_FILE = RAW_DIR / "data.csv"
OUTPUT_FILE = PROCESSED_DIR / "parking_cleaned.csv"

# 1. Load dataset
print("Loading parking dataset...")

df = pd.read_csv(INPUT_FILE)

# 2. Clean column names
df.columns = df.columns.str.strip()

required_columns = [
    "SystemCodeNumber",
    "Capacity",
    "Occupancy",
    "LastUpdated"
]

if not set(required_columns).issubset(df.columns):
    raise ValueError(f"Unexpected columns: {df.columns.tolist()}")

# 3. Convert data types
df["Capacity"] = pd.to_numeric(df["Capacity"], errors="coerce")
df["Occupancy"] = pd.to_numeric(df["Occupancy"], errors="coerce")
df["LastUpdated"] = pd.to_datetime(
    df["LastUpdated"], errors="coerce"
)

# 4. Remove invalid and duplicate records
df = df.drop_duplicates()

df = df.dropna(subset=required_columns)

df = df[
    (df["Capacity"] > 0) &
    (df["Occupancy"] >= 0) &
    (df["Occupancy"] <= df["Capacity"])
].copy()

# 5. Sort by parking location and time
df = df.sort_values(
    ["SystemCodeNumber", "LastUpdated"]
).reset_index(drop=True)

# 6. Create parking availability features
df["AvailableSpaces"] = (
    df["Capacity"] - df["Occupancy"]
)

df["OccupancyRate"] = (
    df["Occupancy"] / df["Capacity"]
)

# 7. Create time-based features
df["Hour"] = df["LastUpdated"].dt.hour
df["Minute"] = df["LastUpdated"].dt.minute
df["DayOfWeek"] = df["LastUpdated"].dt.dayofweek
df["Day"] = df["LastUpdated"].dt.day
df["Month"] = df["LastUpdated"].dt.month

df["IsWeekend"] = (
    df["DayOfWeek"] >= 5
).astype(int)

# 8. Create next-observation prediction targets
grouped = df.groupby("SystemCodeNumber", sort=False)

df["NextOccupancy"] = grouped["Occupancy"].shift(-1)
df["NextAvailableSpaces"] = grouped["AvailableSpaces"].shift(-1)

# Remove final observations without a future target
df = df.dropna(
    subset=["NextOccupancy", "NextAvailableSpaces"]
).copy()

df["NextOccupancy"] = df["NextOccupancy"].astype(int)
df["NextAvailableSpaces"] = (
    df["NextAvailableSpaces"].astype(int)
)

# 9. Save processed dataset
df.to_csv(OUTPUT_FILE, index=False)

# 10. Display results
print("\n========== PREPROCESSING COMPLETED ==========")
print("Original dataset: data.csv")
print("Processed records:", len(df))
print("Number of parking locations:", df["SystemCodeNumber"].nunique())
print("Total features:", len(df.columns))
print("\nProcessed columns:")
print(df.columns.tolist())

print("\nFirst five processed records:")
print(df.head().to_string())

print("\nSaved processed dataset:")
print(OUTPUT_FILE)
