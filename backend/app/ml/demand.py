
from pathlib import Path

import pandas as pd
import joblib

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# Project paths
BASE_DIR = Path(__file__).resolve().parents[3]

DATA_FILE = BASE_DIR / "datasets" / "processed" / "parking_cleaned.csv"
MODEL_DIR = BASE_DIR / "backend" / "saved_models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_FILE = MODEL_DIR / "demand_model.joblib"

print("Loading processed parking dataset...")

df = pd.read_csv(DATA_FILE)

# Calculate next-observation occupancy rate
df["NextOccupancyRate"] = (
    df["NextOccupancy"] / df["Capacity"]
)

# Create demand categories
def classify_demand(rate):
    if rate <= 0.25:
        return "Low"
    elif rate <= 0.50:
        return "Medium"
    elif rate <= 0.75:
        return "High"
    else:
        return "Very High"

df["DemandLevel"] = df["NextOccupancyRate"].apply(
    classify_demand
)

# Input features
features = [
    "SystemCodeNumber",
    "Capacity",
    "Occupancy",
    "OccupancyRate",
    "Hour",
    "Minute",
    "DayOfWeek",
    "Month",
    "IsWeekend"
]

X = df[features]
y = df["DemandLevel"]

# Chronological train-test split
df = df.sort_values("LastUpdated").reset_index(drop=True)

X = df[features]
y = df["DemandLevel"]

split_index = int(len(df) * 0.8)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]

# Encode parking location
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

# Random Forest classifier
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

print("Training demand prediction model...")

model.fit(X_train, y_train)

# Evaluate model
predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print("\n========== DEMAND MODEL RESULTS ==========")
print(f"Accuracy: {accuracy:.4f}")

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        predictions,
        zero_division=0
    )
)

print("\nConfusion Matrix:")
print(confusion_matrix(
    y_test,
    predictions,
    labels=["Low", "Medium", "High", "Very High"]
))

# Save model
joblib.dump(model, MODEL_FILE)

print("\nDEMAND MODEL TRAINING COMPLETED")
print("Model saved at:", MODEL_FILE)
