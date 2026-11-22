
from pathlib import Path

import pandas as pd
import joblib

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder


# Project paths
BASE_DIR = Path(__file__).resolve().parents[3]

DATA_FILE = BASE_DIR / "datasets" / "processed" / "waiting_time_data.csv"
MODEL_DIR = BASE_DIR / "backend" / "saved_models"
MODEL_FILE = MODEL_DIR / "waiting_time_model.joblib"

MODEL_DIR.mkdir(parents=True, exist_ok=True)


# Input features
FEATURES = [
    "ParkingLocation",
    "Hour",
    "DayOfWeek",
    "QueueLength",
    "AvailableSpaces"
]

TARGET = "WaitingTimeMinutes"

# Dataset columns
REQUIRED_COLUMNS = FEATURES + [TARGET]


# Check dataset
if not DATA_FILE.exists():
    raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")

print("Loading waiting-time dataset...")

df = pd.read_csv(DATA_FILE)

missing = set(REQUIRED_COLUMNS) - set(df.columns)

if missing:
    raise ValueError(f"Missing columns: {sorted(missing)}")


# Clean parking locations
df["ParkingLocation"] = (
    df["ParkingLocation"]
    .astype(str)
    .str.strip()
    .str.upper()
)


# Convert numeric columns
numeric_columns = [
    "Hour",
    "DayOfWeek",
    "QueueLength",
    "AvailableSpaces",
    TARGET
]

for column in numeric_columns:
    df[column] = pd.to_numeric(df[column], errors="coerce")


# Remove invalid records
df = df.dropna(subset=REQUIRED_COLUMNS).copy()

df = df[
    df["Hour"].between(0, 23) &
    df["DayOfWeek"].between(0, 6) &
    (df["QueueLength"] >= 0) &
    (df["AvailableSpaces"] >= 0) &
    (df[TARGET] >= 0)
].copy()


print("Valid records:", len(df))


# Display data source
if "DataSource" in df.columns:
    print("\nData sources:")
    print(df["DataSource"].value_counts())


# Minimum records for demo training
if len(df) < 20:
    raise ValueError(
        f"Only {len(df)} records available. "
        "At least 20 records are needed for demo training."
    )


X = df[FEATURES]
y = df[TARGET]


# Split training and testing data
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)


# Preprocessing
preprocessor = ColumnTransformer([
    (
        "location",
        OneHotEncoder(handle_unknown="ignore"),
        ["ParkingLocation"]
    )
], remainder="passthrough")


# Random Forest model
model = Pipeline([
    ("preprocessor", preprocessor),
    (
        "regressor",
        RandomForestRegressor(
            n_estimators=150,
            random_state=42,
            n_jobs=-1
        )
    )
])


# Train
print("\nTraining waiting-time prediction model...")

model.fit(X_train, y_train)


# Evaluate
predictions = model.predict(X_test)

mae = mean_absolute_error(y_test, predictions)


# Save model
joblib.dump(model, MODEL_FILE)


print("\n====================================")
print("WAITING-TIME MODEL TRAINED")
print("====================================")
print("Training records:", len(X_train))
print("Testing records:", len(X_test))
print(f"Mean Absolute Error: {mae:.2f} minutes")
print("Model saved:", MODEL_FILE)
print("Data status: SIMULATED DEMO")
print("Note: This model is a prototype.")
