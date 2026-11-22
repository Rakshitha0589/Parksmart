
from pathlib import Path

import pandas as pd
import joblib

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# Project paths
BASE_DIR = Path(__file__).resolve().parents[3]

DATA_FILE = BASE_DIR / "datasets" / "processed" / "parking_cleaned.csv"
MODEL_DIR = BASE_DIR / "backend" / "saved_models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_FILE = MODEL_DIR / "peak_hours_model.joblib"

print("Loading parking dataset...")

df = pd.read_csv(DATA_FILE)
df["LastUpdated"] = pd.to_datetime(df["LastUpdated"])

# Aggregate occupancy by parking location and hour
df["Date"] = df["LastUpdated"].dt.date

hourly = (
    df.groupby(
        ["SystemCodeNumber", "Date", "Hour"],
        as_index=False
    )
    .agg(
        OccupancyRate=("OccupancyRate", "mean"),
        Capacity=("Capacity", "mean"),
        DayOfWeek=("DayOfWeek", "first"),
        Month=("Month", "first"),
        IsWeekend=("IsWeekend", "first"),
        LastUpdated=("LastUpdated", "max")
    )
)

# Sort chronologically
hourly = hourly.sort_values("LastUpdated").reset_index(drop=True)

# Chronological train-test split
split_index = int(len(hourly) * 0.8)

train = hourly.iloc[:split_index].copy()
test = hourly.iloc[split_index:].copy()

# Calculate peak threshold from training data
thresholds = train.groupby(
    "SystemCodeNumber"
)["OccupancyRate"].quantile(0.80)

global_threshold = train["OccupancyRate"].quantile(0.80)

# Label peak hours
train["IsPeakHour"] = [
    int(rate >= thresholds.get(location, global_threshold))
    for location, rate in zip(
        train["SystemCodeNumber"],
        train["OccupancyRate"]
    )
]

test["IsPeakHour"] = [
    int(rate >= thresholds.get(location, global_threshold))
    for location, rate in zip(
        test["SystemCodeNumber"],
        test["OccupancyRate"]
    )
]

# Features
features = [
    "SystemCodeNumber",
    "Hour",
    "DayOfWeek",
    "Month",
    "IsWeekend"
]

X_train = train[features]
y_train = train["IsPeakHour"]

X_test = test[features]
y_test = test["IsPeakHour"]

# Preprocessing
preprocessor = ColumnTransformer(
    transformers=[
        (
            "location",
            OneHotEncoder(handle_unknown="ignore"),
            ["SystemCodeNumber"]
        )
    ],
    remainder="passthrough"
)

# Model
model = Pipeline([
    ("preprocessor", preprocessor),
    (
        "classifier",
        RandomForestClassifier(
            n_estimators=150,
            random_state=42,
            class_weight="balanced",
            n_jobs=-1
        )
    )
])

print("Training peak-hour prediction model...")

model.fit(X_train, y_train)

# Evaluation
predictions = model.predict(X_test)

print("\n========== PEAK-HOUR MODEL RESULTS ==========")
print("Accuracy:", round(accuracy_score(y_test, predictions), 4))

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        predictions,
        target_names=["Non-Peak", "Peak"],
        zero_division=0
    )
)

# Save model and metadata
joblib.dump(
    {
        "model": model,
        "peak_thresholds": thresholds.to_dict(),
        "global_threshold": global_threshold,
        "features": features
    },
    MODEL_FILE
)

print("\nPEAK-HOUR MODEL TRAINING COMPLETED")
print("Model saved at:", MODEL_FILE)
print("Peak threshold:", round(global_threshold, 3))
print("Training records:", len(train))
print("Testing records:", len(test))
