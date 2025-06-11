# Lab 3: Monitoring và Logging với SigNoz

## Giới thiệu

Dự án Lab 3 triển khai hệ thống monitoring, logging và alerting cho API dự đoán Titanic sử dụng **SigNoz** - một platform observability all-in-one. SigNoz thay thế cho combo Prometheus + Grafana + ELK Stack với giao diện tích hợp.

## Công nghệ sử dụng

### Monitoring Stack
- **SigNoz**: All-in-one observability platform
- **ClickHouse**: Database lưu trữ metrics, logs, traces
- **OpenTelemetry**: Instrumentation library

### Application Stack
- **FastAPI**: Web framework với OpenTelemetry integration
- **Scikit-learn**: ML model đã train từ lab 1 sẵn (Random Forest)
- **Docker & Docker Compose**: Container orchestration

## Yêu cầu hệ thống

- **Docker**: >= 20.10.0
- **Docker Compose**: >= 2.0.0
- **RAM**: Tối thiểu 4GB (khuyến nghị 8GB)
- **Disk**: Tối thiểu 5GB free space
- **Network**: Internet để download images lần đầu
- **Git**: Để clone SigNoz repository

## Hướng dẫn cài đặt và chạy

### 1. Clone repositories

```bash
# Clone Lab 3 project
git clone https://github.com/MTQV002/CS317-Lab3-SigNoz.git
cd CS317-Lab3-SigNoz

# Clone SigNoz riêng biệt (QUAN TRỌNG!)
git clone https://github.com/SigNoz/signoz.git
```

**Cấu trúc thư mục sau khi clone:**
```
CS317-Lab3-SigNoz/
├── app/                    # FastAPI application
├── scripts/               # Traffic generator, error simulator
├── docker-compose.yml     # Main services
├── requirements.txt       # Python dependencies
├── signoz/               # SigNoz repository (git cloned)
│   ├── deploy/
│   ├── docker/
│   └── ...
└── README.md
```

### 2. Setup SigNoz

```bash
# Di chuyển vào thư mục SigNoz
cd signoz

# Chạy SigNoz setup script
./deploy/docker/clickhouse-setup/deploy.sh

# Quay lại thư mục chính
cd ..
```

**⏱️ Thời gian setup SigNoz**: 5-10 phút (download images + setup database)

### 3. Khởi chạy Titanic API

```bash
# Khởi động API services
docker-compose up -d

# Theo dõi quá trình khởi động
docker-compose logs -f
```

### 4. Kiểm tra services đang chạy

```bash
# Kiểm tra SigNoz services
cd signoz && docker-compose ps

# Kiểm tra API services  
cd .. && docker-compose ps

# Kiểm tra health của API
curl http://localhost:8000/health
```

### 5. Truy cập các interfaces

| Service | URL | Mô tả |
|---------|-----|-------|
| **SigNoz Dashboard** | http://localhost:3301 | Main monitoring interface |
| **API Docs** | http://localhost:8000/docs | FastAPI Swagger UI |
| **Health Check** | http://localhost:8000/health | API status |
| **ClickHouse** | http://localhost:8123 | Database interface (optional) |

## Demo và Testing

### 1. Kiểm tra API hoạt động

```bash
# Test prediction endpoint
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
```

### 2. Chạy Traffic Generator

```bash
# Cài đặt dependencies
pip install requests

# Chạy traffic generator
python scripts/traffic_generator.py
```

**Script sẽ:**
- Gửi ~3 requests/second trong 5 phút
- 80% normal predictions, 10% errors, 10% slow requests
- Hiển thị realtime progress
- Tự động dừng sau 5 phút

### 3. Chạy Error Simulator

```bash
# Chạy error simulator
python scripts/error_simulator.py
```

**Monitoring trong Dashboard:**
1. **Error Rate Panel**: Sẽ spike lên >50%
2. **Error Logs**: Filter level="ERROR" trong Logs tab
3. **Alert Triggers**: Nếu đã cấu hình alerts
4. **Trace Analysis**: Error traces visible trong Traces tab

## SigNoz Dashboard Guide

### 1. Truy cập Dashboard
1. Mở http://localhost:3301
2. Đợi vài giây để SigNoz khởi động hoàn toàn
3. Không cần login cho local setup

### 2. Các tab chính

#### Services Tab
- Hiển thị `titanic-api` service
- Metrics: Throughput, Error Rate, Latency (P99, P95, P50)
- Service map: Dependencies giữa các services

#### Metrics Tab  
Các metrics được thu thập:
- `predictions_total`: Tổng số predictions
- `prediction_duration_seconds`: Thời gian xử lý
- `model_confidence_score`: Confidence của model
- `system_cpu_usage_percent`: CPU usage
- `system_memory_usage_percent`: Memory usage
- `api_error_rate`: Tỷ lệ lỗi API

#### Traces Tab
- Distributed tracing cho từng request
- Click vào trace để xem chi tiết
- Flamegraph visualization

#### Logs Tab
- Application logs với JSON format
- Filter theo level: INFO, WARNING, ERROR
- Search và query logs

### 3. Tạo Custom Dashboard

1. Đi tới **Dashboards** → **New Dashboard**
2. Add Panel với queries:

```promql
# Request Rate
rate(predictions_total[5m])

# Error Rate  
api_error_rate

# Average Confidence
avg(model_confidence_score)

# CPU Usage
system_cpu_usage_percent
```

## Alert Configuration

### 1. Tạo Alert Rules

Đi tới **Alerts** → **New Rule**:

#### High Error Rate Alert
```yaml
Name: high_error_rate
Query: api_error_rate > 30
Evaluation: Every 1m for 2m
Severity: critical
```

#### Low Model Confidence Alert
```yaml
Name: low_confidence
Query: avg(model_confidence_score) < 0.6  
Evaluation: Every 2m for 5m
Severity: warning
```

### 2. Notification Channels

Setup trong **Settings** → **Notification Channels**:
- Email SMTP
- Slack Webhook
- Custom Webhook

## Testing Scenarios

### Scenario 1: Normal Operation
```bash
# Start traffic generator
python scripts/traffic_generator.py

# Monitor dashboard metrics realtime
# Check logs flowing trong SigNoz Logs tab
```

### Scenario 2: Error Spike  
```bash
# Trigger error simulation
python scripts/error_simulator.py

# Watch error rate spike trong dashboard
# Check error logs trong Logs tab
```

### Scenario 3: Manual Testing
```bash
# Manual error trigger
for i in {1..10}; do
  curl http://localhost:8000/simulate_error
  sleep 1
done

# Manual slow requests
for i in {1..5}; do
  curl http://localhost:8000/simulate_slow
  sleep 2
done
```

## Troubleshooting

### SigNoz không khởi động

```bash
# Kiểm tra Docker resources
docker system df
docker system prune  # Nếu thiếu disk space

# Restart SigNoz
cd signoz
docker-compose down
./deploy/docker/clickhouse-setup/deploy.sh
```

### Services conflict

```bash
# Kiểm tra port conflicts
netstat -tulpn | grep :3301  # SigNoz port
netstat -tulpn | grep :8000  # API port

# Stop conflicting services nếu có
sudo lsof -ti:3301 | xargs kill -9
```

### API không connect được tới SigNoz

```bash
# Kiểm tra network
docker network ls | grep signoz

# Kiểm tra SigNoz OTel Collector
cd signoz && docker-compose logs otel-collector

# Restart API để reconnect
cd .. && docker-compose restart
```

## Log Analysis

### 1. Docker logs

```bash
# API logs
docker-compose logs -f titanic-api

# SigNoz logs
cd signoz && docker-compose logs -f
```

### 2. SigNoz UI logs

1. **Logs** tab → Filter by service="titanic-api"
2. Search queries:
   - `level="ERROR"` - Chỉ errors
   - `message contains "prediction"` - Prediction logs
   - `timestamp > "2024-01-01"` - Time range

## Cleanup

```bash
# Stop API services
docker-compose down

# Stop SigNoz services
cd signoz && docker-compose down

# Remove volumes (delete all data)
docker-compose down -v
cd signoz && docker-compose down -v

# Remove SigNoz folder (nếu cần)
cd .. && rm -rf signoz
```

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Titanic API   │───▶│  OTel Collector  │───▶│   ClickHouse    │
│   (FastAPI)     │    │   (Metrics,      │    │   (Database)    │
│                 │    │ Traces, Logs)    │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │                        ▼                        │
         │              ┌──────────────────┐              │
         │              │ SigNoz Frontend  │              │
         │              │   (Dashboard)    │              │
         │              └──────────────────┘              │
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  ▼
                        ┌──────────────────┐
                        │ SigNoz Query     │
                        │    Service       │
                        └──────────────────┘
```

## Quick Start Commands

```bash
# 1. Clone repositories
git clone <repo-url>
cd CS317-Lab3-SigNoz
git clone https://github.com/SigNoz/signoz.git

# 2. Setup SigNoz
cd signoz
./deploy/docker/clickhouse-setup/deploy.sh
cd ..

# 3. Start API
docker-compose up -d

# 4. Test
curl http://localhost:8000/health

# 5. Generate traffic
pip install requests
python scripts/traffic_generator.py

# 6. Open dashboard
# Browser: http://localhost:3301
```

## Alternative: Lightweight Setup (Nếu SigNoz quá nặng)

Nếu SigNoz quá tốn resources, có thể dùng stack nhẹ hơn:

```bash
# Chạy alternative stack
docker-compose -f docker-compose-lite.yml up -d

# Access:
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
```

## Video Demo Checklist

- [ ] **Setup**: Show clone SigNoz + deploy process
- [ ] **Dashboard Overview**: SigNoz UI với metrics panels
- [ ] **Traffic Generation**: `python scripts/traffic_generator.py`
- [ ] **Error Simulation**: `python scripts/error_simulator.py` 
- [ ] **Log Analysis**: Filter logs trong SigNoz
- [ ] **Trace Deep Dive**: Click trace details
- [ ] **Alert Setup**: Create và test alert rules

## Support

**Common Issues:**
- **Port 3301 đã được sử dụng**: `sudo lsof -ti:3301 | xargs kill -9`
- **Out of memory**: Tăng Docker memory limit hoặc dùng lightweight setup
- **SigNoz không hiển thị data**: Restart API services để reconnect

**Folder structure check:**
```bash
ls -la
# Should see: app/, scripts/, signoz/, docker-compose.yml
```

---

**Note**: 
- SigNoz setup cần 4GB+ RAM
- Lần đầu chạy sẽ download ~2GB Docker images
- Project đã có sẵn model và scripts, chỉ cần clone SigNoz thêm!