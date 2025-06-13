<p align="center">
  <a href="https://www.uit.edu.vn/" title="Trường Đại học Công nghệ Thông tin" style="border: 5;">
    <img src="https://i.imgur.com/WmMnSRt.png" alt="Trường Đại học Công nghệ Thông tin | University of Information Technology">
  </a>
</p>


<!-- Title -->
<h1 align="center"><b>CS317.P21 - PHÁT TRIỂN VÀ VẬN HÀNH HỆ THỐNG MÁY HỌC</b></h1>

## COURSE INTRODUCTION
<a name="gioithieumonhoc"></a>
* *Course Title*: Phát triển và vận hành hệ thống máy học
* *Course Code*: CS317.P21
* *Year*: 2024-2025

## ACADEMIC ADVISOR
<a name="giangvien"></a>
* *Đỗ Văn Tiến* - tiendv@uit.edu.vn
* *Lê Trần Trọng Khiêm* - khiemltt@uit.edu.vn

## MEMBERS
<a name="thanhvien"></a>
* Từ Minh Phi - 22521080
* Lê Thành Tiến - 22521467
* Dương Thành Trí - 22521516
* Nguyễn Minh Thiện  - 22521391
* Nguyễn Quốc Vinh - 22521674






# Lab 3: Monitoring và Logging với SigNoz


## Giới thiệu

Dự án Lab 3 triển khai hệ thống monitoring, logging và alerting cho API dự đoán Titanic sử dụng **SigNoz** - một platform observability all-in-one.

## Công nghệ sử dụng

### Monitoring Stack
- **SigNoz v0.87.0**: All-in-one observability platform
- **ClickHouse 24.1.2**: Database lưu trữ metrics, logs, traces
- **OpenTelemetry**: Instrumentation library



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


## Khởi chạy hệ thống

### Bước 1: Start SigNoz Backend Services

```bash
# Di chuyển vào thư mục SigNoz
cd signoz

# Start SigNoz services (first time takes 2-3 minutes)
docker-compose -f deploy/docker/docker-compose.yaml up -d

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
| **🎯 SigNoz UI** | http://localhost:8080 | Complete monitoring interface | ✅ Main Interface |
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


### 1. Traffic Generator Script

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

## SigNoz Guide

### 1. Accessing Signoz

1. **Open**: http://localhost:8080
2. **Wait**: Few seconds for complete loading
3. **No Login**: Required for local setup

### 2. Setup
- You can read signoz.md to setup dashboard & Alert

## Video Demo Requirements


- **link** :

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

