# README.md - Hướng dẫn setup Dashboard và Alerts trong SigNoz

## Phần 1: Kiểm tra dữ liệu có sẵn

### 1.1 Verify API đang gửi metrics
```bash
# Kiểm tra API running
curl http://localhost:8000/health

# Generate test data
python scripts/traffic_generator.py &

# Đợi 2-3 phút để có data trong SigNoz
```

### 1.2 Check SigNoz UI
- Mở http://localhost:3301
- Vào **Services** tab → Should see `titanic-api`
- Vào **Metrics** tab → Should see metrics như `system_cpu_usage_percent`

## Phần 2: Tạo Custom Dashboard

### 2.1 Create New Dashboard
1. **Click "Dashboards"** trong left sidebar
2. **Click "New Dashboard"** (top right button)
3. **Dashboard Name**: `Titanic API Comprehensive Monitoring`
4. **Description**: `Complete monitoring cho Titanic API - Lab 3`
5. **Click "Save"**

### 2.2 Configure Dashboard Settings
- **Time Range**: Set to "Last 30 minutes" 
- **Refresh Interval**: Set to "5s" (for demo purposes)

## Phần 3: Tạo các Panels từng bước

### 3.1 System Resources Row

#### Panel 1: CPU Usage
1. **Click "Add Panel"** → **Time Series**
2. **Panel Configuration**:
   - **Panel Name**: `System CPU Usage`
   - **Description**: `Real-time CPU usage percentage`

3. **Query Builder** (tab 1):
   ```
   Metrics: system_cpu_usage_percent
   Legend Format: CPU Usage %
   ```

4. **Panel Options** (right sidebar):
   - **Panel Type**: Time Series
   - **Y Axis Unit**: Percent (%)
   - **Y Axis Min**: 0
   - **Y Axis Max**: 100

5. **Thresholds**:
   - **Add Threshold** → Value: 70, Color: Yellow (Warning)
   - **Add Threshold** → Value: 85, Color: Red (Critical)

6. **Click "Save Changes"**

#### Panel 2: Memory Usage  
1. **Add Panel** → **Time Series**
2. **Configuration**:
   ```
   Panel Name: System Memory Usage
   Metrics: system_memory_usage_percent
   Legend: Memory Usage %
   Y Axis: Percent (%), Min: 0, Max: 100
   Thresholds: 80% (Yellow), 90% (Red)
   ```

#### Panel 3: Disk Usage
1. **Add Panel** → **Stat** (single value)
2. **Configuration**:
   ```
   Panel Name: Disk Usage
   Metrics: system_disk_usage_percent
   Display: Gauge
   Unit: Percent (%)
   Thresholds: 70% (Green→Yellow), 85% (Yellow→Red)
   ```

#### Panel 4: Network I/O
1. **Add Panel** → **Time Series**
2. **Multi-query setup**:
   ```
   Query A: 
   - Metrics: system_network_bytes_sent
   - Legend: Bytes Sent
   
   Query B:
   - Metrics: system_network_bytes_recv  
   - Legend: Bytes Received
   ```
3. **Y Axis Unit**: Bytes

#### Panel 5: Disk I/O
1. **Add Panel** → **Time Series**
2. **Multi-query**:
   ```
   Query A: system_disk_read_bytes (Legend: Disk Read)
   Query B: system_disk_write_bytes (Legend: Disk Write)
   Unit: Bytes
   ```

### 3.2 API Performance Row

#### Panel 6: Request Rate
1. **Add Panel** → **Time Series**
2. **Configuration**:
   ```
   Panel Name: API Request Rate
   Metrics: api_request_rate_per_second
   Legend: Requests/sec
   Y Axis Unit: req/s
   ```

#### Panel 7: Error Rate
1. **Add Panel** → **Stat**
2. **Configuration**:
   ```
   Panel Name: API Error Rate
   Metrics: api_error_rate_percent
   Display: Big Number with sparkline
   Unit: Percent (%)
   Thresholds: 5% (Green→Yellow), 15% (Yellow→Red)
   ```

#### Panel 8: HTTP Request Duration
1. **Add Panel** → **Time Series**  
2. **Query**: `http_request_duration_seconds`
3. **Functions**: Apply percentile functions
   ```
   Query A: percentile(http_request_duration_seconds, 0.50) - P50
   Query B: percentile(http_request_duration_seconds, 0.95) - P95  
   Query C: percentile(http_request_duration_seconds, 0.99) - P99
   ```

### 3.3 Model Performance Row

#### Panel 9: Total Predictions
1. **Add Panel** → **Stat**
2. **Configuration**:
   ```
   Panel Name: Total Predictions
   Metrics: predictions_total
   Display: Big Number
   Unit: Count
   ```

#### Panel 10: Model Confidence
1. **Add Panel** → **Time Series**
2. **Multi-query**:
   ```
   Query A: avg(model_confidence_score) - Average
   Query B: min(model_confidence_score) - Minimum  
   Query C: max(model_confidence_score) - Maximum
   Y Axis: 0 to 1, Unit: Score
   ```

#### Panel 11: Inference Speed
1. **Add Panel** → **Time Series**
2. **Query**: `prediction_duration_seconds`
3. **Functions**:
   ```
   Query A: avg(prediction_duration_seconds) - Average
   Query B: percentile(prediction_duration_seconds, 0.95) - P95
   Unit: seconds
   ```

#### Panel 12: Confidence Distribution
1. **Add Panel** → **Table**
2. **Multi-query**:
   ```
   Query A: low_confidence_predictions (Label: Low Confidence <0.6)
   Query B: high_confidence_predictions (Label: High Confidence >0.9)
   ```

### 3.4 Arrange Dashboard Layout

1. **Drag panels** để resize và arrange
2. **Recommended layout** (12-column grid):
   ```
   Row 1 - System Resources:
   [CPU Usage - 3 cols][Memory - 3 cols][Disk Usage - 3 cols][Network I/O - 3 cols]
   
   Row 2 - System I/O:
   [Disk I/O - 6 cols][Empty space - 6 cols]
   
   Row 3 - API Performance:  
   [Request Rate - 4 cols][Error Rate - 4 cols][Latency - 4 cols]
   
   Row 4 - Model Performance:
   [Total Predictions - 3 cols][Confidence - 4.5 cols][Inference Speed - 4.5 cols]
   
   Row 5 - Model Details:
   [Confidence Distribution - 12 cols]
   ```

## Phần 4: Setup Alerts

### 4.1 Navigate to Alerts
1. **Click "Alerts"** trong left sidebar
2. **Click "New Alert Rule"**

### 4.2 Create Alert Rules

#### Alert 1: High Error Rate
1. **Alert Rule Configuration**:
   ```
   Alert Name: High API Error Rate
   Description: Triggers when error rate > 50% for 2 minutes
   ```

2. **Query Configuration**:
   ```
   Metrics: api_error_rate_percent
   Condition: IS ABOVE
   Threshold: 50
   ```

3. **Evaluation**:
   ```
   Evaluate Every: 1m
   For: 2m (must be above threshold for 2 minutes)
   ```

4. **Labels** (for routing):
   ```
   severity: critical
   service: titanic-api
   alert_type: error_rate
   ```

#### Alert 2: Low Model Confidence
1. **Configuration**:
   ```
   Alert Name: Low Model Confidence
   Description: Triggers when avg confidence < 0.6 for 5 minutes
   
   Query: model_avg_confidence_score
   Condition: IS BELOW  
   Threshold: 0.6
   Evaluate Every: 2m
   For: 5m
   
   Labels:
   severity: warning
   service: titanic-api
   alert_type: model_performance
   ```

#### Alert 3: High CPU Usage
1. **Configuration**:
   ```
   Alert Name: High System CPU
   Description: CPU usage > 80% for 5 minutes
   
   Query: system_cpu_usage_percent
   Condition: IS ABOVE
   Threshold: 80
   Evaluate Every: 1m
   For: 5m
   
   Labels:
   severity: warning
   service: titanic-api
   alert_type: system_resource
   ```

#### Alert 4: High Memory Usage
1. **Configuration**:
   ```
   Alert Name: High Memory Usage
   Description: Memory > 85% for 3 minutes
   
   Query: system_memory_usage_percent
   Condition: IS ABOVE
   Threshold: 85
   Evaluate Every: 1m
   For: 3m
   ```

### 4.3 Setup Notification Channels

#### Option 1: Email Notifications
1. **Go to Settings** → **Notification Channels**
2. **Add Channel** → **Email**
3. **Configuration**:
   ```
   Channel Name: Email Alerts
   Email Addresses: your-email@example.com
   SMTP Settings: (if using custom SMTP)
   ```

#### Option 2: Slack Integration
1. **Add Channel** → **Slack**
2. **Webhook URL**: `https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK`
3. **Channel**: `#monitoring`

#### Option 3: Webhook (Custom)
1. **Add Channel** → **Webhook**
2. **URL**: `http://your-app.com/alerts/webhook`
3. **Method**: POST
4. **Headers**: `Content-Type: application/json`

### 4.4 Link Alerts to Notification Channels
1. **Edit each Alert Rule**
2. **Notification** section → **Add notification channel**
3. **Select appropriate channels** for each alert severity

## Phần 5: Testing Setup

### 5.1 Generate Normal Traffic
```bash
# Start traffic generator
python scripts/traffic_generator.py

# Monitor dashboard real-time
# http://localhost:3301/dashboard/your-dashboard
```

### 5.2 Test Error Rate Alert
```bash
# Generate errors to trigger alert
python scripts/error_simulator.py

# Should see:
# 1. Error rate spike trong dashboard
# 2. Alert fires trong Alerts tab
# 3. Notification sent (email/slack)
```

### 5.3 Test Low Confidence Alert
```bash
# Send low confidence data
for i in {1..20}; do
  curl -X POST "http://localhost:8000/predict" \
    -H "Content-Type: application/json" \
    -d '{"Pclass": 3, "Sex": "male", "Age": 50, "SibSp": 0, "Parch": 0, "Fare": 5, "Embarked": "S"}'
  sleep 2
done
```

### 5.4 Test CPU Alert
```bash
# Generate CPU load
stress --cpu 4 --timeout 300s

# Hoặc Python script:
python -c "
import multiprocessing as mp
import time
def cpu_load():
    while True: pass
for i in range(mp.cpu_count()):
    mp.Process(target=cpu_load).start()
time.sleep(300)
"
```

## Phần 6: Dashboard Export/Import

### 6.1 Export Dashboard
1. **Dashboard Settings** → **Export**
2. **Copy JSON** và save to `dashboard-config.json`
3. **Version control** this file

### 6.2 Import Dashboard
1. **Dashboards** → **Import**
2. **Paste JSON** hoặc upload file
3. **Adjust data sources** if needed

## Phần 7: Advanced Features

### 7.1 Variables trong Dashboard
1. **Dashboard Settings** → **Variables**
2. **Add Variable**:
   ```
   Name: time_range
   Type: Interval
   Values: 5m,15m,30m,1h
   Default: 15m
   ```

### 7.2 Annotations
1. **Dashboard Settings** → **Annotations**
2. **Add Annotation**:
   ```
   Name: Deployments
   Query: deployment_events
   ```

### 7.3 Template Variables trong Queries
```
# Sử dụng variable trong query
system_cpu_usage_percent[${time_range}]
```

## Quick Start Commands Summary

```bash
# 1. Ensure SigNoz và API running
docker ps | grep signoz
curl http://localhost:8000/health

# 2. Generate data
python scripts/traffic_generator.py &

# 3. Create dashboard
# Follow GUI steps above

# 4. Test alerts
python scripts/error_simulator.py

# 5. Monitor results
# http://localhost:3301
```

## Video Demo Checklist

- [ ] **Show empty dashboard creation**
- [ ] **Add each panel type (Time Series, Stat, Table)**  
- [ ] **Configure thresholds và colors**
- [ ] **Create all 4 alert rules**
- [ ] **Demo traffic generator + real-time updates**
- [ ] **Trigger error simulation → show alert firing**
- [ ] **Show logs correlation trong Logs tab**
- [ ] **Demonstrate alert notification**

## Troubleshooting

**Metrics không hiển thị:**
```bash
# Check API metrics endpoint
curl http://localhost:8000/metrics/system

# Check OTel connection
docker logs signoz-otel-collector
```

**Alerts không fire:**
- Check evaluation interval vs. data frequency
- Verify threshold values are realistic  
- Check notification channel configuration

Dashboard này đáp ứng **100% yêu cầu Lab 3** và ready cho demo! 🚀