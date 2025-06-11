# Lab 3: Monitoring và Logging với SigNoz

## Giới thiệu

Dự án Lab 3 triển khai hệ thống monitoring, logging và alerting cho API dự đoán Titanic sử dụng **SigNoz** - một platform observability all-in-one. SigNoz thay thế cho combo Prometheus + Grafana + ELK Stack với giao diện tích hợp.

## Công nghệ sử dụng

### Monitoring Stack
- **SigNoz v0.87.0**: All-in-one observability platform
- **ClickHouse 24.1.2**: Database lưu trữ metrics, logs, traces
- **OpenTelemetry**: Instrumentation library
- **Zookeeper 3.7.1**: Service coordination

### Application Stack
- **FastAPI 0.104.1**: Web framework với OpenTelemetry integration
- **Scikit-learn 1.3.2**: ML model (Random Forest pre-trained)
- **Docker 20.10+**: Container runtime
- **Docker Compose 2.0+**: Container orchestration

## Yêu cầu hệ thống

- **Docker**: >= 20.10.0
- **Docker Compose**: >= 2.0.0
- **RAM**: Tối thiểu 4GB (khuyến nghị 8GB)
- **Disk**: Tối thiểu 5GB free space
- **Network**: Internet để download images lần đầu
- **Git**: Để clone repositories
- **Python**: 3.11+ (cho traffic generator scripts)

## Cài đặt môi trường

### 1. Clone Project

```bash
# Clone project chính
git clone https://github.com/MTQV002/CS317-Lab3-SigNoz.git
cd CS317-Lab3-SigNoz

# Cấu trúc project
CS317-Lab3-SigNoz/
├── docker-compose.yml      # API service configuration
├── main.py                 # FastAPI application với OpenTelemetry
├── requirements.txt        # Python dependencies với version cụ thể
├── Dockerfile             # API container image
├── best_rf_model.pkl      # Pre-trained Random Forest model
├── scripts/               # Traffic generators và utilities
│   ├── traffic_generator.py
│   └── error_simulator.py
├── logs/                  # Application logs directory
└── README.md             # Documentation
```

### 2. Setup SigNoz (One-time)

```bash
# Clone SigNoz repository
git clone -b main https://github.com/SigNoz/signoz.git

# Verify SigNoz structure
ls signoz/deploy/docker/
# Should show: docker-compose.yaml, otel-collector-config.yaml, etc.
```

### 3. Phiên bản thư viện cụ thể

#### Python Dependencies (requirements.txt):
```txt
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
scikit-learn==1.3.2
pandas==2.1.4
joblib==1.3.2
psutil==5.9.6
requests==2.31.0

# OpenTelemetry packages
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-instrumentation==0.42b0
opentelemetry-instrumentation-fastapi==0.42b0
opentelemetry-instrumentation-requests==0.42b0
opentelemetry-exporter-otlp-proto-grpc==1.21.0
opentelemetry-exporter-otlp-proto-http==1.21.0
```

#### Docker Images với version cụ thể:
```yaml
# SigNoz Services
signoz/signoz:v0.87.0                        # Query service + Web UI
signoz/signoz-otel-collector:v0.111.42       # OpenTelemetry Collector
clickhouse/clickhouse-server:24.1.2-alpine   # Database
bitnami/zookeeper:3.7.1                      # Coordination service

# Application  
python:3.11-slim                             # Base image cho API
```

## Khởi chạy hệ thống

### Bước 1: Start SigNoz Backend Services

```bash
# Di chuyển vào thư mục SigNoz
cd signoz

# Start SigNoz services (first time takes 2-3 minutes)
docker-compose -f deploy/docker/docker-compose.yaml up -d

# Verify SigNoz startup
echo "Waiting for SigNoz to fully start..."
sleep 120

# Check SigNoz services
docker-compose -f deploy/docker/docker-compose.yaml ps

# Expected output:
# NAME                    STATUS                   PORTS
# signoz                  Up (healthy)            0.0.0.0:8080->8080/tcp
# signoz-clickhouse       Up (healthy)            8123/tcp, 9000/tcp
# signoz-otel-collector   Up                      0.0.0.0:4317-4318->4317-4318/tcp
# signoz-zookeeper-1      Up (healthy)            2181/tcp, 2888/tcp, 3888/tcp

# Return to project directory
cd ..
```

### Bước 2: Start Titanic API

```bash
# Build và start API service
docker-compose up -d

# Verify API startup
sleep 30
docker-compose ps

# Expected output:
# NAME                    STATUS                   PORTS
# titanic-api             Up (healthy)            0.0.0.0:8000->8000/tcp
```

### Bước 3: Verify Complete Setup

```bash
# Check all running containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Expected complete setup:
# NAME                    STATUS                   PORTS
# titanic-api             Up (healthy)            0.0.0.0:8000->8000/tcp
# signoz                  Up (healthy)            0.0.0.0:8080->8080/tcp
# signoz-otel-collector   Up                      0.0.0.0:4317-4318->4317-4318/tcp
# signoz-clickhouse       Up (healthy)            8123/tcp, 9000/tcp
# signoz-zookeeper-1      Up (healthy)            2181/tcp, 2888/tcp, 3888/tcp
```

### Bước 4: Test Connectivity

```bash
# Test API health
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2024-06-11T...",
#   "service": "titanic-api",
#   "version": "1.0.0",
#   "system": {...}
# }

# Test SigNoz Web UI
curl -s http://localhost:8080 | head -10

# Should return HTML content
```

## Access Interfaces

| Service | URL | Description | Status |
|---------|-----|-------------|--------|
| **🎯 SigNoz Dashboard** | http://localhost:8080 | Complete monitoring interface | ✅ Main Interface |
| **📚 API Documentation** | http://localhost:8000/docs | FastAPI Swagger UI | ✅ Working |
| **❤️ Health Check** | http://localhost:8000/health | API status endpoint | ✅ Working |
| **🗄️ ClickHouse** | http://localhost:8123 | Database interface | ✅ Working |

## Architecture Overview

```
Final Architecture (Simplified)
┌─────────────────────────────────────────────────────────────┐
│                    SigNoz Platform                         │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────┐│
│  │   ClickHouse    │◄───│  OTel Collector  │◄───│ Signoz  ││
│  │   (Database)    │    │   (Port 4317)    │    │Web UI   ││
│  │                 │    │                  │    │Port 8080││
│  └─────────────────┘    └──────────────────┘    └─────────┘│
└─────────────────────────────────────────┬───────────────────┘
                                          │
                              ┌───────────▼───────────┐
                              │     Titanic API       │
                              │     (Port 8000)       │
                              │   OpenTelemetry       │
                              │   Instrumented        │
                              └───────────────────────┘
```

**Existing SigNoz Services (from signoz/ folder):**
- signoz (Query Service + Web UI - port 8080) 
- `signoz-clickhouse` (Database storage)
- `signoz-otel-collector` (Metrics/Traces/Logs collector - port 4317)
- `signoz-zookeeper-1` (Service coordination)

**Added API Service (from main docker-compose.yml):**
- `titanic-api` (FastAPI application - port 8000)

## Demo và Testing

### 1. Manual API Testing

```bash
# Test single prediction
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "Pclass": 3,
    "Sex": "male", 
    "Age": 25,
    "SibSp": 0,
    "Parch": 0,
    "Fare": 7.25,
    "Embarked": "S"
  }'

# Expected response:
# {
#   "prediction": "Không sống sót",
#   "confidence": 0.892,
#   "processing_time": 0.045,
#   "probabilities": {
#     "not_survived": 0.892,
#     "survived": 0.108
#   },
#   "service": "titanic-api",
#   "timestamp": "2024-06-11T..."
# }
```

### 2. Traffic Generator Script

```bash
# Install dependencies (phiên bản cụ thể)
pip install requests==2.31.0

# Run traffic generator
python scripts/traffic_generator.py

# Script configuration:
# - Duration: 5 minutes
# - Rate: ~3 requests/second
# - Mix: 80% normal predictions, 10% errors, 10% slow requests
# - Real-time progress display
# - Auto-stop after duration
```

**Script output sample:**
```
🚀 Starting Traffic Generator...
📊 Configuration:
   - Duration: 300 seconds
   - Rate: 3 requests/second
   - Target: http://localhost:8000

⏱️  [00:15] Requests: 45 | Success: 36 (80%) | Errors: 5 (11%) | Slow: 4 (9%)
⏱️  [00:30] Requests: 90 | Success: 72 (80%) | Errors: 9 (10%) | Slow: 9 (10%)
...
✅ Traffic generation completed!
```

### 3. Error Simulation Script

```bash
# Run error simulator
python scripts/error_simulator.py

# Script behavior:
# - Generates 50+ error requests rapidly
# - Triggers /simulate_error endpoint
# - Causes error rate spike >50%
# - Monitors dashboard response
```

## SigNoz Dashboard Guide

### 1. Accessing Dashboard

1. **Open**: http://localhost:8080
2. **Wait**: Few seconds for complete loading
3. **No Login**: Required for local setup

### 2. Dashboard Navigation

#### 📊 Services Tab
- **Overview**: Service health và performance metrics
- **Metrics displayed**:
  - Throughput (requests/second)
  - Error Rate (percentage)
  - Latency (P99, P95, P50 percentiles)
  - Service dependencies map

#### 📈 Metrics Tab
**Custom Metrics được thu thập:**
- `predictions_total`: Total number of predictions made
- `prediction_duration_seconds`: Time spent processing predictions  
- `model_confidence_score`: ML model confidence scores
- `system_cpu_usage_percent`: System CPU utilization
- `system_memory_usage_percent`: System memory utilization
- `api_error_rate`: API error rate percentage

#### 🔍 Traces Tab
- **Distributed Tracing**: Individual request traces
- **Trace Details**: Click vào trace để xem chi tiết
- **Flamegraph**: Visual representation of request flow
- **Error Traces**: Failed requests với error details

#### 📋 Logs Tab
- **Application Logs**: JSON formatted logs từ API
- **System Logs**: Container và infrastructure logs
- **Filter Options**:
  - `level="ERROR"` - Error logs only
  - `message contains "prediction"` - Prediction-related logs
  - `service="titanic-api"` - API service logs only

### 3. Expected Dashboard Behavior

#### Normal Operation (sau khi chạy traffic generator):
- **Services Tab**: `titanic-api` service visible với healthy metrics
- **Request Rate**: ~3 requests/second
- **Error Rate**: ~10%
- **Latency**: P95 < 100ms

#### During Error Simulation:
- **Error Rate**: Spike to >50%
- **Error Logs**: Increased error entries trong Logs tab
- **Error Traces**: Failed requests visible trong Traces tab

## Video Demo Requirements

### 📹 Dashboard Overview Section (30 seconds)
- **Show**: SigNoz dashboard initial state
- **Highlight**: Services, Metrics, Traces, Logs tabs
- **Demonstrate**: Navigation through different sections

### 📹 Traffic Generation Section (60 seconds)
- **Command**: `python scripts/traffic_generator.py`
- **Show**: Real-time script output
- **Dashboard**: Live metrics updating
- **Highlight**: Request rate, latency metrics

### 📹 Error Simulation Section (45 seconds)
- **Command**: `python scripts/error_simulator.py`
- **Show**: Error rate spike trong dashboard
- **Logs**: Error entries appearing trong Logs tab
- **Traces**: Error traces với stack trace details

### 📹 Log Analysis Section (30 seconds)
- **Filter**: `level="ERROR"` trong Logs tab
- **Show**: JSON structured logs
- **Highlight**: Error messages và timestamps

## Management Commands

### Daily Operations

```bash
# Start services (if not running)
cd signoz && docker-compose -f deploy/docker/docker-compose.yaml start && cd ..
docker-compose start

# Stop services (keep data)
docker-compose stop
cd signoz && docker-compose -f deploy/docker/docker-compose.yaml stop && cd ..

# Restart after code changes
docker-compose down
docker-compose build --no-cache titanic-api
docker-compose up -d

# Check logs
docker-compose logs -f titanic-api
cd signoz && docker-compose -f deploy/docker/docker-compose.yaml logs signoz && cd ..
```

### Health Checks

```bash
# Check all container status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# API health check
curl http://localhost:8000/health

# System metrics
curl http://localhost:8000/metrics/system

# Test prediction endpoint
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"Pclass":1,"Sex":"female","Age":25,"SibSp":0,"Parch":0,"Fare":50,"Embarked":"S"}'
```

## Performance Baseline

### Expected Metrics (Normal Operation)
- **Throughput**: 3 requests/second
- **Error Rate**: ~10%
- **P95 Latency**: <100ms
- **CPU Usage**: <20%
- **Memory Usage**: <50%

### Resource Usage
- **Total RAM**: ~2-3GB
- **Disk Space**: ~1GB for logs/data
- **Network**: Minimal (local containers)