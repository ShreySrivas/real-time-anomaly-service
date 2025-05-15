# service/alert_subscriber.py

import os
import json
import time
import threading
import redis
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# ─── Redis & Pub/Sub ──────────────────────────────────────────────────────────
r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
pubsub = r.pubsub()
pubsub.subscribe("anomalies")

# ─── Gmail settings ────────────────────────────────────────────────────────────
GMAIL_USER      = os.environ["GMAIL_USER"]
GMAIL_PASS      = os.environ["GMAIL_PASS"]
ALERT_RECIPIENT = os.environ.get("ALERT_RECIPIENT", GMAIL_USER)

def send_email(subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = ALERT_RECIPIENT
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(GMAIL_USER, GMAIL_PASS)
        smtp.send_message(msg)

# ─── Reporter thread: batch every 60s ─────────────────────────────────────────
def reporter():
    while True:
        time.sleep(60)
        now = time.time()
        window_start = now - 60

        # fetch by ingestion time score
        entries = r.zrangebyscore("anomalies", window_start, now)
        if not entries:
            print("⏳ No anomalies in the last minute.")
            continue

        # remove them so next window is clean
        r.zremrangebyscore("anomalies", window_start, now)

        # parse payloads
        batch = [json.loads(e) for e in entries]
        scores = [item["score"] for item in batch]
        count     = len(scores)
        avg_score = sum(scores) / count
        max_score = max(scores)
        min_score = min(scores)

        # time span of original events (optional)
        ev_ts = [item["timestamp"] for item in batch]
        start_str = datetime.fromtimestamp(min(ev_ts)).strftime("%Y-%m-%d %H:%M:%S")
        end_str   = datetime.fromtimestamp(max(ev_ts)).strftime("%Y-%m-%d %H:%M:%S")

        subject = f"[Anomaly Summary] {datetime.utcnow():%Y-%m-%d %H:%M} UTC"
        body = (
            f"Window (ingested): {datetime.fromtimestamp(window_start):%H:%M:%S} – "
            f"{datetime.fromtimestamp(now):%H:%M:%S}\n"
            f"Events (orig ts): {start_str} → {end_str}\n"
            f"Total anomalies: {count}\n"
            f"Avg score: {avg_score:.3f}\n"
            f"Min score: {min_score:.3f}\n"
            f"Max score: {max_score:.3f}\n\n"
            f"Sample payload:\n{json.dumps(batch[0], indent=2)}"
        )

        try:
            send_email(subject, body)
            print(f"📧 Sent summary: {subject}")
        except Exception as e:
            print("❌ Email send failed:", e)

# ─── Consumer loop: ingest & buffer ────────────────────────────────────────────
def consumer_loop():
    for msg in pubsub.listen():
        if msg.get("type") != "message":
            continue
        payload = json.loads(msg["data"])
        ingest_ts = time.time()
        # score by ingestion time, but keep original data in the JSON
        to_store = {
            "timestamp": payload["timestamp"],
            "score":     payload["score"],
            "ingest_ts": ingest_ts
        }
        r.zadd("anomalies", {json.dumps(to_store): ingest_ts})

if __name__ == "__main__":
    threading.Thread(target=reporter, daemon=True).start()
    print("🔔 Alert subscriber running—batching anomalies in Redis every minute…")
    consumer_loop()
