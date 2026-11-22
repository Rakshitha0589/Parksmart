
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[3]

DATA_FILE = BASE_DIR / "datasets" / "processed" / "waiting_time_data.csv"

# Additional simulated demo records
new_data = [
    ["DEMO_PARKING_A", 12, 6, 7, 1, 30, "SIMULATED_DEMO"],
    ["DEMO_PARKING_B", 13, 6, 9, 0, 40, "SIMULATED_DEMO"],
    ["DEMO_PARKING_A", 14, 6, 11, 0, 45, "SIMULATED_DEMO"],
    ["DEMO_PARKING_B", 15, 6, 5, 3, 18, "SIMULATED_DEMO"],
    ["DEMO_PARKING_A", 16, 6, 13, 0, 55, "SIMULATED_DEMO"],
    ["DEMO_PARKING_B", 17, 6, 8, 1, 35, "SIMULATED_DEMO"],
    ["DEMO_PARKING_A", 18, 6, 15, 0, 60, "SIMULATED_DEMO"],
    ["DEMO_PARKING_B", 19, 6, 4, 4, 10, "SIMULATED_DEMO"],
    ["DEMO_PARKING_A", 9, 0, 6, 1, 25, "SIMULATED_DEMO"],
    ["DEMO_PARKING_B", 10, 0, 7, 2, 22, "SIMULATED_DEMO"],
    ["DEMO_PARKING_A", 11, 0, 10, 0, 40, "SIMULATED_DEMO"],
    ["DEMO_PARKING_B", 12, 0, 3, 5, 8, "SIMULATED_DEMO"],
    ["DEMO_PARKING_A", 13, 0, 12, 0, 48, "SIMULATED_DEMO"],
    ["DEMO_PARKING_B", 14, 0, 6, 2, 26, "SIMULATED_DEMO"],
    ["DEMO_PARKING_A", 15, 0, 9, 1, 36, "SIMULATED_DEMO"],
    ["DEMO_PARKING_B", 16, 0, 11, 0, 44, "SIMULATED_DEMO"],
    ["DEMO_PARKING_A", 17, 0, 5, 3, 16, "SIMULATED_DEMO"],
]

columns = [
    "ParkingLocation",
    "Hour",
    "DayOfWeek",
    "QueueLength",
    "AvailableSpaces",
    "WaitingTimeMinutes",
    "DataSource",
]

df = pd.DataFrame(new_data, columns=columns)

# Preserve existing records
if DATA_FILE.exists():
    existing = pd.read_csv(DATA_FILE)
    df = pd.concat([existing, df], ignore_index=True)

DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(DATA_FILE, index=False)

print("Batch data saved successfully!")
print("Total records:", len(df))
print("Data source: SIMULATED_DEMO")
print("File:", DATA_FILE)
