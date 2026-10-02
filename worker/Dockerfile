FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker.py music.py ./
ENV AWS_DEFAULT_REGION=us-east-1 PYTHONUNBUFFERED=1
CMD ["python", "worker.py"]
