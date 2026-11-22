
from pathlib import Path
import pandas as pd
import joblib

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Project paths
BASE_DIR = Path(__file__).resolve().parents[3]

DATA_FILE = BASE_DIR / "datasets" / "processed" / "parking_cleaned.csv"
MODEL_DIR = BASE_DIR / "backend" / "saved_models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_FILE = MODEL_DIR / "availability_model.joblib"

print("Loading processed parking dataset...")

df = pd.read_csv(DATA_FILE)

# Features used for prediction
features = [
    "SystemCodeNumber",
    "Capacity",
    "Occupancy",
    "Hour",
    "Minute",
    "DayOfWeek",
    "Month",
    "IsWeekend"
]

target = "NextAvailableSpaces"

X = df[features]
y = df[target]

# Chronological train-test split
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

print("Training availability prediction model...")

model.fit(X_train, y_train)

# Evaluate model
predictions = model.predict(X_test)

mae = mean_absolute_error(y_test, predictions)
rmse = mean_squared_error(y_test, predictions) ** 0.5
r2 = r2_score(y_test, predictions)

# Save model
joblib.dump(model, MODEL_FILE)

print("\n========== MODEL TRAINING COMPLETED ==========")
print("Training records:", len(X_train))
print("Testing records:", len(X_test))
print(f"Mean Absolute Error: {mae:.2f} spaces")
print(f"Root Mean Squared Error: {rmse:.2f} spaces")
print(f"R2 Score: {r2:.4f}")
print("\nModel saved at:", MODEL_FILE)
