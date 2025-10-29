FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY watcher/ /app/watcher/
COPY shared/ /app/shared/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

WORKDIR /app/watcher

CMD ["python", "main.py"]
