
from pathlib import Path
from datetime import datetime
import csv

BASE_DIR = Path(__file__).resolve().parents[2]

OUTPUT_FILE = (
    BASE_DIR
    / "datasets"
    / "processed"
    / "waiting_time_data.csv"
)

COLUMNS = [
    "ParkingLocation",
    "Hour",
    "DayOfWeek",
    "QueueLength",
    "AvailableSpaces",
    "WaitingTimeMinutes",
    "DataSource"
]


def collect_demo_record():
    print("\n--- Demo Waiting Time Data Collection ---")

    location = input("Parking location: ").strip()
    hour = int(input("Arrival hour (0-23): "))
    day = int(input("Day of week (0-6): "))
    queue = int(input("Queue length: "))
    spaces = int(input("Available spaces: "))
    waiting = int(input("Waiting time in minutes: "))

    if not location:
        raise ValueError("Parking location cannot be empty.")

    if not 0 <= hour <= 23:
        raise ValueError("Hour must be between 0 and 23.")

    if not 0 <= day <= 6:
        raise ValueError("Day must be between 0 and 6.")

    if queue < 0 or spaces < 0 or waiting < 0:
        raise ValueError("Queue, spaces and waiting time cannot be negative.")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    file_exists = OUTPUT_FILE.exists()

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)

        if not file_exists or OUTPUT_FILE.stat().st_size == 0:
            writer.writeheader()

        writer.writerow({
            "ParkingLocation": location,
            "Hour": hour,
            "DayOfWeek": day,
            "QueueLength": queue,
            "AvailableSpaces": spaces,
            "WaitingTimeMinutes": waiting,
            "DataSource": "SIMULATED_DEMO"
        })

    print("\nDemo record saved successfully!")
    print(f"Saved to: {OUTPUT_FILE}")
    print("Data source: SIMULATED_DEMO")


if __name__ == "__main__":
    collect_demo_record()
