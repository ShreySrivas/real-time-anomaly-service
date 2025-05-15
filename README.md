# 🚀 Real‑Time Anomaly Detection Service

A lightweight microservice for streaming event anomaly detection using Isolation Forest, Redis caching, and Gmail alerts, with observability via Prometheus & Grafana.

## 🚀 Features

* **Kafka producer/consumer:** Efficient event ingestion and anomaly scoring.
* **IsolationForest model training:** Includes hyperparameter tuning.
* **Redis cache:** Stores recent scores and buffers Pub/Sub alerts.
* **Gmail notifications:** Batches and sends anomaly summaries.
* **Prometheus & Grafana:** Real-time monitoring and dashboards.

---

## 📁 Repository Structure

```bash
real-time-anomaly-service/
├── data/                            # NAB EC2 CPU utilization CSVs
│   └── NAB/realAWSCloudwatch/
│       └── ec2_cpu_utilization_*.csv
├── model/
│   └── train_isolation_forest.py    # Offline training + tuning script
├── service/
│   ├── producer.py                  # Replays CSVs to Kafka
│   ├── consumer.py                  # Scores events + caches in Redis + metrics
│   ├── alert_subscriber.py          # Batches & emails anomaly summaries
│   └── Dockerfile                   # Builds all three service containers
├── prom/
│   └── prometheus.yml               # Prometheus scrape configs
├── docker-compose.yml               # Orchestrates Kafka, Redis, services, Prometheus, Grafana
└── README.md                        # This file
```

---

## 🔧 Prerequisites

* **Docker & Docker Compose**
* **Python 3.10+ (for local training)**
* **A Gmail account with an App Password**

---

## 🛠️ Local Training

1. **Create a virtual environment:**

```bash
python3 -m venv venv
source venv/bin/activate
```

2. **Install dependencies:**

```bash
pip install pandas numpy scikit-learn
```

3. **Train the model:** (reads data/NAB/realAWSCloudwatch/\*.csv)

```bash
python model/train_isolation_forest.py
```

* Outputs: `model/isolation_forest.pkl` with model, scaler, feature list

4. **Deactivate:**

```bash
deactivate
```

---

## 🐳 Docker Compose

1. **Create a `.env` file in the project root:**

```env
GMAIL_USER=you@gmail.com
GMAIL_PASS=<app_password>
ALERT_RECIPIENT=alerts@domain.com  # Optional
```

2. **Build and launch services:**

```bash
docker-compose up --build
```

### Services

* `zookeeper`, `kafka` for event bus
* `redis` for caching & Pub/Sub
* `consumer` for scoring & metrics
* `producer` to replay CSVs
* `alert_subscriber` for Gmail summaries
* `prometheus` & `grafana` for observability

---

## 📊 Access UIs

* **Prometheus:** [http://localhost:9090](http://localhost:9090)

  * Query metrics: `events_processed_total`, `anomalies_detected_total`

* **Grafana:** [http://localhost:3000](http://localhost:3000)

  * Login: `admin` / `admin`
  * Add data source: Prometheus at `http://prometheus:9090`
  * Import or build dashboards (e.g., anomaly rate, cache hit rate)

---

## 🐞 Troubleshooting

* **No brokers:** Ensure Kafka is up before the consumer; the consumer will retry every 5s.
* **No alerts:** Verify alert\_subscriber logs, Redis Pub/Sub, and correct Gmail credentials.
* **Metrics missing:** Check Prometheus targets in the UI and container logs.
