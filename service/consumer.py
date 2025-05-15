# service/consumer.py

import json
import pickle
import time
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
import redis
from prometheus_client import Counter, start_http_server
from datetime import datetime

# --- Load pipeline artifacts ---
with open("model/isolation_forest.pkl", "rb") as f:
    artefacts    = pickle.load(f)
    model        = artefacts["model"]
    scaler       = artefacts["scaler"]
    feature_cols = artefacts["feature_cols"]  # ["value","hour","dayofweek"]

# --- Redis & Prometheus setup ---
r = redis.Redis(host="redis", port=6379, db=0)
EVENTS = Counter("events_processed_total",   "Total events processed")
ANOMS  = Counter("anomalies_detected_total", "Total anomalies detected")
start_http_server(8000)

# --- Wait for Kafka to be ready ---
bootstrap = ["kafka:9092"]
while True:
    try:
        consumer = KafkaConsumer(
            "raw-events",
            bootstrap_servers=bootstrap,
            value_deserializer=lambda m: json.loads(m.decode()),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        print("✅ Connected to Kafka broker")
        break
    except NoBrokersAvailable:
        print("⏳ Kafka broker not available yet, retrying in 5s...")
        time.sleep(5)

CACHE_TTL = 3600  # seconds

for msg in consumer:
    evt = msg.value
    EVENTS.inc()

    # reconstruct timestamp features
    ts = datetime.fromtimestamp(evt["timestamp"])
    feat = [evt["value"], ts.hour, ts.weekday()]

    # scale & score
    Xs     = scaler.transform([feat])
    score  = model.decision_function(Xs)[0]
    is_anom = model.predict(Xs)[0] == -1

    # cache
    key     = f"anomaly:{evt['timestamp']:.3f}"
    payload = {"event": evt, "score": float(score), "anomaly": bool(is_anom)}
    r.set(key, json.dumps(payload), ex=CACHE_TTL)

    # publish alerts
    if is_anom:
        ANOMS.inc()
        r.publish("anomalies", json.dumps({
            "timestamp": evt["timestamp"],
            "score":     float(score)
        }))

    print(f"{ts} → score={score:.3f}, anom={is_anom}")
