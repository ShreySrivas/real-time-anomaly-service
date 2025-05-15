FROM python:3.10-slim

# install build deps for scikit-learn
RUN apt-get update && \
    apt-get install -y build-essential python3-dev libatlas-base-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy the trained model (from repo-root/model)
COPY model/ /app/model/

# copy all three service scripts (from repo-root/service/)
COPY service/producer.py     /app/producer.py
COPY service/consumer.py     /app/consumer.py
COPY service/alert_subscriber.py /app/alert_subscriber.py

RUN pip install --no-cache-dir \
    kafka-python \
    pandas \
    scikit-learn>=1.0 \
    redis \
    prometheus-client \
    requests

# default entrypoint: start the consumer
CMD ["python", "consumer.py"]
