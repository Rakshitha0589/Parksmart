
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import joblib


# Project paths
BASE_DIR = Path(__file__).resolve().parents[3]

DATA_FILE = BASE_DIR / "datasets" / "processed" / "parking_cleaned.csv"
MODEL_FILE = BASE_DIR / "backend" / "saved_models" / "availability_model.joblib"


FEATURES = [
    "SystemCodeNumber",
    "Capacity",
    "Occupancy",
    "Hour",
    "Minute",
    "DayOfWeek",
    "Month",
    "IsWeekend"
]


def recommend_best_time(
    parking_location: str,
    start_time: datetime,
    end_time: datetime,
    step_minutes: int = 15
):
    """
    Recommend the arrival time with the highest
    predicted parking availability.

    Uses the latest historical occupancy observation
    for the selected parking location.

    This is a historical ML estimate, not live availability.
    """

    # Validate inputs
    if start_time >= end_time:
        raise ValueError("End time must be after start time.")

    if step_minutes <= 0:
        raise ValueError("Step minutes must be positive.")

    if not parking_location.strip():
        raise ValueError("Parking location cannot be empty.")

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            "Processed parking dataset not found."
        )

    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            "Availability model not found. Train Model 1 first."
        )

    # Load dataset
    df = pd.read_csv(DATA_FILE)

    required_columns = [
        "SystemCodeNumber",
        "Capacity",
        "Occupancy",
        "LastUpdated"
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Dataset is missing columns: {missing_columns}"
        )

    df["LastUpdated"] = pd.to_datetime(
        df["LastUpdated"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["SystemCodeNumber", "Capacity", "Occupancy", "LastUpdated"]
    )

    # Filter selected parking location
    location_data = df[
        df["SystemCodeNumber"].astype(str) == parking_location
    ].copy()

    if location_data.empty:
        raise ValueError(
            "Parking location not found in dataset."
        )

    # Get latest recorded occupancy
    latest = location_data.sort_values(
        "LastUpdated"
    ).iloc[-1]

    capacity = int(latest["Capacity"])
    occupancy = int(latest["Occupancy"])

    if capacity <= 0:
        raise ValueError("Invalid parking capacity.")

    if occupancy < 0 or occupancy > capacity:
        raise ValueError("Invalid recorded occupancy.")

    # Load trained availability model
    model = joblib.load(MODEL_FILE)

    # Generate candidate arrival times
    candidates = []
    current_time = start_time

    while current_time <= end_time:

        candidates.append({
            "SystemCodeNumber": parking_location,
            "Capacity": capacity,
            "Occupancy": occupancy,
            "Hour": current_time.hour,
            "Minute": current_time.minute,
            "DayOfWeek": current_time.weekday(),
            "Month": current_time.month,
            "IsWeekend": int(current_time.weekday() >= 5)
        })

        current_time += timedelta(
            minutes=step_minutes
        )

    if not candidates:
        raise ValueError("No candidate arrival times generated.")

    # Predict availability for every candidate
    candidate_df = pd.DataFrame(
        candidates
    )[FEATURES]

    predictions = model.predict(candidate_df)

    results = []

    for candidate, prediction in zip(candidates, predictions):

        predicted_spaces = max(
            0,
            min(capacity, int(round(float(prediction))))
        )

        results.append({
            "recommended_time": (
                f'{candidate["Hour"]:02d}:'
                f'{candidate["Minute"]:02d}'
            ),
            "predicted_available_spaces": predicted_spaces,
            "capacity": capacity
        })

    # Sort highest predicted availability first
    results.sort(
        key=lambda item: item["predicted_available_spaces"],
        reverse=True
    )

    best = results[0]

    return {
        "status": "success",
        "parking_location": parking_location,
        "best_time": best["recommended_time"],
        "predicted_available_spaces": (
            best["predicted_available_spaces"]
        ),
        "capacity": capacity,
        "all_recommendations": results,
        "prediction_type": "historical ML estimate",
        "message": (
            "This recommendation uses the latest recorded "
            "occupancy. It is not confirmed live availability."
        )
    }


if __name__ == "__main__":

    df = pd.read_csv(DATA_FILE)

    location = str(
        df["SystemCodeNumber"].dropna().iloc[0]
    )

    today = datetime.now().replace(
        hour=8,
        minute=0,
        second=0,
        microsecond=0
    )

    start = today
    end = today.replace(hour=12)

    result = recommend_best_time(
        parking_location=location,
        start_time=start,
        end_time=end,
        step_minutes=15
    )

    print("\nBEST PARKING TIME")
    print("-----------------")
    print("Location:", result["parking_location"])
    print("Best time:", result["best_time"])
    print(
        "Predicted spaces:",
        result["predicted_available_spaces"]
    )

    print("\nAll recommendations:")

    for item in result["all_recommendations"]:
        print(item)
