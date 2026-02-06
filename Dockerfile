FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

# Install git and other dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . ./

ENV PYTHONPATH="/app"

EXPOSE 8501

CMD ["python", "app/run_pipeline.py", "--dashboard", "--port", "8501"]
