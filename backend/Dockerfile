# Installing Python Dependencies
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Lean image of python, serves our purpose
FROM python:3.12-slim
WORKDIR /app

# Copying installed packages from builder
COPY --from=builder /install /usr/local

# Copying application source
COPY app/ ./app/
COPY agent/ ./agent/

# Writable directory for the SQLite volume mount
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
