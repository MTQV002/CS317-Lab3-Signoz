FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies first
COPY requirements.txt .
# Nâng cấp scikit-learn lên phiên bản phù hợp với model
RUN pip install --no-cache-dir -r requirements.txt 

# Copy application code and model
COPY main.py .
COPY best_rf_model.pkl .

# Create logs and models directories
RUN mkdir -p /app/logs /app/models

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]