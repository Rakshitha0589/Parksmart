
from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# Project paths
BASE_DIR = Path(__file__).resolve().parents[3]

DATA_FILE = BASE_DIR / "datasets" / "processed" / "parking_cleaned.csv"

MODEL_DIR = BASE_DIR / "backend" / "saved_models"
MODEL_FILE = MODEL_DIR / "anomaly_detection_model.joblib"

OUTPUT_FILE = BASE_DIR / "datasets" / "processed" / "parking_anomalies.csv"


# Features used by the anomaly detection model
FEATURES = [
    "Capacity",
    "Occupancy",
    "AvailableSpaces",
    "OccupancyRate",
    "Hour",
    "DayOfWeek",
    "IsWeekend"
]


def train_anomaly_model():

    print("Loading cleaned parking dataset...")

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_FILE}"
        )

    df = pd.read_csv(DATA_FILE)

    required_columns = FEATURES + [
        "SystemCodeNumber",
        "LastUpdated"
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    print("Preparing data...")

    for column in FEATURES:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna(
        subset=FEATURES
    ).copy()

    if len(df) < 20:
        raise ValueError(
            "At least 20 valid records are required."
        )

    print(f"Valid records: {len(df)}")

    X = df[FEATURES]

    print("Training Isolation Forest model...")

    model = Pipeline([
        ("scaler", StandardScaler()),
        (
            "isolation_forest",
            IsolationForest(
                n_estimators=150,
                contamination=0.05,
                random_state=42,
                n_jobs=-1
            )
        )
    ])

    model.fit(X)

    print("Detecting unusual occupancy patterns...")

    predictions = model.predict(X)

    df["AnomalyScore"] = predictions

    df["AnomalyStatus"] = df["AnomalyScore"].map({
        1: "Normal",
        -1: "Unusual Occupancy"
    })

    anomalies = df[
        df["AnomalyScore"] == -1
    ].copy()

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    joblib.dump(
        {
            "model": model,
            "features": FEATURES
        },
        MODEL_FILE
    )

    anomalies.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\nAnomaly Detection Training Completed!")

    print(f"Total records: {len(df)}")
    print(f"Normal records: {(predictions == 1).sum()}")
    print(f"Unusual records: {(predictions == -1).sum()}")

    print(f"\nModel saved: {MODEL_FILE}")
    print(f"Anomaly report saved: {OUTPUT_FILE}")

    print(
        "\nNote: An anomaly is an unusual data pattern, "
        "not proof of a parking incident."
    )


if __name__ == "__main__":
    train_anomaly_model()
