FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user first
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Copy Earth Engine credentials
RUN mkdir -p /home/appuser/.config/earthengine
COPY ee-credentials /home/appuser/.config/earthengine/credentials
RUN chown -R appuser:appuser /home/appuser/.config

USER appuser

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
