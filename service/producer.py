import json
import time
import glob
import pandas as pd
from kafka import KafkaProducer, errors

# retry parameters
RETRIES    = 10
DELAY_SEC  = 5

# attempt to connect to Kafka with backoff
producer = None
for attempt in range(1, RETRIES + 1):
    try:
        producer = KafkaProducer(
            bootstrap_servers=["kafka:9092"],
            value_serializer=lambda v: json.dumps(v).encode()
        )
        print(f"[+] Connected to Kafka on attempt {attempt}")
        break
    except errors.NoBrokersAvailable:
        print(f"[!] Kafka not available (attempt {attempt}/{RETRIES}), retrying in {DELAY_SEC}s…")
        time.sleep(DELAY_SEC)

if not producer:
    raise RuntimeError("Could not connect to Kafka after multiple attempts")

# load & sort your EC2 CPU CSVs
files = glob.glob("data/NAB/realAWSCloudwatch/rds_cpu_utilization_*.csv")
df = pd.concat([pd.read_csv(fp, parse_dates=["timestamp"]) for fp in files])
df.sort_values("timestamp", inplace=True)

# stream events
if __name__ == "__main__":
    for _, row in df.iterrows():
        evt = {
            "timestamp": row["timestamp"].timestamp(),
            "value": row["value"]
        }
        producer.send("raw-events", evt)
        print("Sent:", evt)
        time.sleep(1)  # adjust to control replay speed
