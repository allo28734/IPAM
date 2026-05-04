FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY . .

# Ensure entrypoint is executable and has unix line endings
RUN chmod +x entrypoint.sh && \
    sed -i 's/\r$//' entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
