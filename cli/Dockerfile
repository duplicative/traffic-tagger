FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY cli/ /app/cli/
COPY shared/ /app/shared/

ENV PYTHONPATH=/app

WORKDIR /app/cli

ENTRYPOINT ["python", "main.py"]
CMD []
