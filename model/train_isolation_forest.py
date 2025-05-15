# model/train_isolation_forest.py

import glob
import os
import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import silhouette_score
from sklearn.model_selection import ParameterGrid
from sklearn.preprocessing import StandardScaler

# 1) Find all matching files in data/NAB/realAWSCloudwatch
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir   = os.path.join(script_dir, os.pardir, "data", "NAB", "realAWSCloudwatch")
pattern    = os.path.join(data_dir, "ec2_cpu_utilization_*.csv")

print(f"Looking for files in: {pattern!r}")

files = glob.glob(pattern)
if not files:
    raise FileNotFoundError(f"No files match {pattern}")

# 2) Read, concat & sort
dfs = []
for fn in files:
    df = pd.read_csv(fn, parse_dates=["timestamp"])
    dfs.append(df[["timestamp", "value"]].dropna())
data = pd.concat(dfs, ignore_index=True).sort_values("timestamp")

# 3) Feature engineering: value, hour, dayofweek
data["hour"]       = data["timestamp"].dt.hour
data["dayofweek"]  = data["timestamp"].dt.dayofweek
feature_cols = ["value", "hour", "dayofweek"]
X = data[feature_cols].values

# 4) Scale features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 5) Hyperparameter grid search (silhouette score)
param_grid = {
    "n_estimators": [50, 100, 200],
    "max_samples": [0.5, 0.75, 1.0],
    "contamination": [0.01, 0.05, 0.1, 0.2],
    "max_features": [1.0, 0.8],
}

best_score  = -np.inf
best_params = None

for params in ParameterGrid(param_grid):
    model = IsolationForest(
        n_estimators=params["n_estimators"],
        max_samples=params["max_samples"],
        contamination=params["contamination"],
        max_features=params["max_features"],
        random_state=42,
    )
    preds = model.fit_predict(X_scaled)  # 1=inlier, -1=anomaly

    # silhouette_score needs at least two distinct labels
    if len(np.unique(preds)) < 2:
        continue

    score = silhouette_score(X_scaled, preds)
    if score > best_score:
        best_score  = score
        best_params = params

print("Best silhouette score:", best_score)
print("Best hyperparameters:", best_params)

BEST_PARAMS = {'contamination': 0.2, 'max_features': 0.8, 'max_samples': 1.0, 'n_estimators': 50} 

# 6) Refit the best model on the full scaled dataset
best_model = IsolationForest(**BEST_PARAMS, random_state=42)
best_model.fit(X_scaled)

# 7) Serialize model + scaler + feature list
os.makedirs("model", exist_ok=True)
with open("model/isolation_forest.pkl", "wb") as f:
    # we’ll pickle a dict for clarity
    pickle.dump({
        "model": best_model,
        "scaler": scaler,
        "feature_cols": feature_cols
    }, f)

print(f"✅ Trained & saved model with params {best_params} to model/isolation_forest.pkl")
