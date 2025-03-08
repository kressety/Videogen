FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y \
    libjpeg-dev zlib1g-dev \
    && pip install --no-cache-dir --break-system-packages -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY . /app
RUN apt-get update && apt-get install -y \
    libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHONUNBUFFERED=1
EXPOSE 7860
CMD ["python", "main.py"]