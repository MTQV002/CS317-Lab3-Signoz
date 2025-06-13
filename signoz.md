#  Hướng dẫn setup Dashboard và Alerts trong SigNoz

## Phần 1: Kiểm tra dữ liệu có sẵn

### 1.1 Verify API đang gửi metrics
```bash
# Kiểm tra API running
curl http://localhost:8000/health

# Generate test data
python scripts/traffic_generator.py 

# Đợi 2-3 phút để có data trong SigNoz
```

### 1.2 Check SigNoz UI
- Mở http://localhost:8080
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
1. **Add Panel** → **Number** (Stat)
2. **Panel Configuration**:
   - **Panel Name**: `System Disk Usage`
   - **Description**: `Current disk usage percentage`

3. **Query Builder**:
   ```
   Metrics: system_disk_usage_percent
   Aggregation: Latest (hoặc Avg)
   Legend Format: Disk Usage
   ```

4. **Panel Options** (right sidebar):
   - **Panel Type**: Number/Stat
   - **Unit**: Percent (%)
   - **Display**: Big Number with Gauge

5. **Thresholds**:
   - **Value**: 70, **Color**: Yellow (Warning)
   - **Value**: 85, **Color**: Red (Critical)

6. **Visualization Settings**:
   - **Show Gauge**: Enable
   - **Value Display**: Show percentage

#### Panel 4: Network I/O
1. **Add Panel** → **Time Series**
2. **Multi-query setup**:
   ```
   Query A: 
   - Metrics: system_network_bytes_sent
   - Aggregation: Avg
   - Legend Format: Network Sent
   
   Query B:
   - Metrics: system_network_bytes_recv  
   - Aggregation: Avg
   - Legend Format: Network Received
   ```
3. **Panel Options**:
   - **Y Axis Unit**: Bytes
   - **Panel Name**: `Network I/O`
   - **Description**: `Network bytes sent and received`

4. **Add queries step by step**:
   - **Query A**: system_network_bytes_sent
   - **Click "+"** để add Query B
   - **Query B**: system_network_bytes_recv

5. **Visualization Settings**:
   - **Chart Type**: Line Chart
   - **Display both series** with different colors

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

#### Panel 9: Model Confidence
1. **Add Panel** → **Time Series**
2. **Multi-query**:
   ```
   Query A: avg(model_confidence_score) - Average
   Query B: min(model_confidence_score) - Minimum  
   Query C: max(model_confidence_score) - Maximum
   Y Axis: 0 to 1, Unit: Score
   ```

#### Panel 10: Inference Speed
1. **Add Panel** → **Time Series**
2. **Query**: `prediction_duration_seconds`
3. **Functions**:
   ```
   Query A: avg(prediction_duration_seconds) - Average
   Query B: percentile(prediction_duration_seconds, 0.95) - P95
   Unit: seconds
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


### 4.3 Setup Notification Channels

####  Email Notifications
1. **Go to Settings** → **Notification Channels**
2. **Add Channel** → **Email**
3. **Configuration**:
   ```
   Channel Name: Email Alerts
   Email Addresses: your-email@example.com
   SMTP Settings: (if using custom SMTP)
   ```

