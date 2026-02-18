FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for psycopg2 (if using postgres)
RUN apt-get update && apt-get install -y libpq-dev gcc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run defaults to port 8080
ENV PORT=8080

CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT
