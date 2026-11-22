
from pathlib import Path

import pandas as pd
import joblib

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score


# Project paths
BASE_DIR = Path(__file__).resolve().parents[3]

DATA_FILE = BASE_DIR / "datasets" / "processed" / "parking_cleaned.csv"
MODEL_DIR = BASE_DIR / "backend" / "saved_models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_FILE = MODEL_DIR / "location_prediction_model.joblib"


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

TARGET = "NextOccupancy"


def train_location_model():

    print("Loading parking dataset...")

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            "Processed parking dataset not found."
        )

    df = pd.read_csv(DATA_FILE)

    # Validate dataset columns
    required_columns = FEATURES + [TARGET, "LastUpdated"]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing dataset columns: {missing_columns}"
        )

    # Clean data
    df["LastUpdated"] = pd.to_datetime(
        df["LastUpdated"],
        errors="coerce"
    )

    df = df.dropna(
        subset=required_columns
    ).copy()

    df = df.sort_values(
        "LastUpdated"
    ).reset_index(drop=True)

    if len(df) < 20:
        raise ValueError(
            "At least 20 valid records are required for training."
        )

    # Prepare features and target
    X = df[FEATURES].copy()
    y = df[TARGET].copy()

    # Chronological train-test split
    split_index = int(len(df) * 0.8)

    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]

    y_train = y.iloc[:split_index]
    y_test = y.iloc[split_index:]

    if X_train.empty or X_test.empty:
        raise ValueError(
            "Not enough records for training and testing."
        )

    # Encode parking locations
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

    # Random Forest model
    model = Pipeline([
        ("preprocessor", preprocessor),
        (
            "regressor",
            RandomForestRegressor(
                n_estimators=150,
                random_state=42,
                n_jobs=-1,
                min_samples_leaf=2
            )
        )
    ])

    print("Training location-wise prediction model...")

    model.fit(X_train, y_train)

    # Evaluate model
    predictions = model.predict(X_test)

    mae = mean_absolute_error(
        y_test,
        predictions
    )

    r2 = r2_score(
        y_test,
        predictions
    )

    # Save model
    joblib.dump(model, MODEL_FILE)

    results = {
        "training_records": len(X_train),
        "testing_records": len(X_test),
        "parking_locations": int(
            df["SystemCodeNumber"].nunique()
        ),
        "mae": round(float(mae), 2),
        "r2_score": round(float(r2), 4),
        "model_file": str(MODEL_FILE)
    }

    print("\n========== LOCATION PREDICTION RESULTS ==========")

    print("Training records:", results["training_records"])
    print("Testing records:", results["testing_records"])
    print("Parking locations:", results["parking_locations"])
    print("MAE:", results["mae"], "vehicles")
    print("R2 Score:", results["r2_score"])

    print("\nModel saved at:", MODEL_FILE)

    print(
        "\nNote: This model predicts parking-location occupancy,"
    )
    print(
        "not actual zone-level occupancy."
    )

    return results


if __name__ == "__main__":
    train_location_model()
