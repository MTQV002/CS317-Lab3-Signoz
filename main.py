from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import joblib
import pandas as pd
import os
import time
import random
import logging
from datetime import datetime
import requests
import json
from typing import Dict, Any

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.metrics import Observation
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "service": "titanic-api"}',
    handlers=[
        logging.FileHandler('/app/logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure OpenTelemetry
resource = Resource.create({"service.name": "titanic-api", "service.version": "1.0.0"})

# Tracing
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer_provider = trace.get_tracer_provider()
otlp_exporter = OTLPSpanExporter(
    endpoint="http://signoz-otel-collector:4317",  # Fixed: sử dụng service name trong Docker network
    insecure=True,
)
span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)

# Metrics
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(
        endpoint="http://signoz-otel-collector:4317",  # Fixed: sử dụng service name
        insecure=True,
    ),
    export_interval_millis=5000,
)
metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

# Get tracer and meter
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Create custom metrics
prediction_counter = meter.create_counter(
    name="predictions_total",
    description="Total number of predictions made",
)

prediction_duration = meter.create_histogram(
    name="prediction_duration_seconds",
    description="Time spent processing predictions",
    unit="s",
)

model_confidence = meter.create_histogram(
    name="model_confidence_score",
    description="Model confidence scores",
    unit="1",
)

# Fixed: Observable gauge callbacks - trả về Observation objects
def get_cpu_usage(options):
    """Fixed callback function for CPU usage"""
    try:
        cpu_percent = psutil.cpu_percent(interval=None)
        return [Observation(cpu_percent)]
    except Exception as e:
        logger.error(f"Error getting CPU usage: {e}")
        return [Observation(0.0)]

def get_memory_usage(options):
    """Fixed callback function for memory usage"""
    try:
        memory_percent = psutil.virtual_memory().percent
        return [Observation(memory_percent)]
    except Exception as e:
        logger.error(f"Error getting memory usage: {e}")
        return [Observation(0.0)]

# System metrics with fixed callbacks
system_cpu_gauge = meter.create_observable_gauge(
    name="system_cpu_usage_percent",
    description="System CPU usage percentage",
    unit="%",
    callbacks=[get_cpu_usage]
)

system_memory_gauge = meter.create_observable_gauge(
    name="system_memory_usage_percent", 
    description="System memory usage percentage",
    unit="%",
    callbacks=[get_memory_usage]
)

# FastAPI app
app = FastAPI(
    title="Titanic Survival Prediction API with Monitoring",
    description="API dự đoán khả năng sống sót trên Titanic với monitoring và logging",
    version="1.0.0"
)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
RequestsInstrumentor().instrument()

MODEL_PATH = "best_rf_model.pkl"

# Load model
if not os.path.exists(MODEL_PATH):
    logger.error(f"Model file '{MODEL_PATH}' not found")
    raise RuntimeError(f"Model file '{MODEL_PATH}' not found")

try:
    model = joblib.load(MODEL_PATH)
    logger.info("Model loaded successfully")
except Exception as e:
    logger.error(f"Could not load model: {e}")
    raise RuntimeError(f"Could not load model: {e}")

class Passenger(BaseModel):
    Pclass: int = Field(..., ge=1, le=3, description="Passenger class (1, 2, or 3)")
    Sex: str = Field(..., description="Gender (male or female)")
    Age: float = Field(..., ge=0, le=100, description="Age in years")
    SibSp: int = Field(..., ge=0, description="Number of siblings/spouses aboard")
    Parch: int = Field(..., ge=0, description="Number of parents/children aboard")
    Fare: float = Field(..., ge=0, description="Passenger fare")
    Embarked: str = Field(..., description="Port of embarkation (C, Q, or S)")

@app.get("/")
def root():
    logger.info("Root endpoint accessed")
    return {"message": "Titanic Survival Prediction API", "status": "running"}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    with tracer.start_as_current_span("health_check") as span:
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            span.set_attribute("cpu_usage", cpu_percent)
            span.set_attribute("memory_usage", memory.percent)
            span.set_attribute("disk_usage", disk.percent)
            
            logger.info(f"Health check - CPU: {cpu_percent}%, Memory: {memory.percent}%")
            
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "cpu_usage": f"{cpu_percent}%",
                    "memory_usage": f"{memory.percent}%",
                    "disk_usage": f"{disk.percent}%"
                }
            }
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {
                "status": "degraded",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

@app.get("/metrics/system")
def get_system_metrics():
    """Get detailed system metrics"""
    with tracer.start_as_current_span("system_metrics"):
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            metrics_data = {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            }
            
            logger.info(f"System metrics collected: CPU {cpu_percent}%, Memory {memory.percent}%")
            return metrics_data
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            raise HTTPException(status_code=500, detail=f"Error collecting metrics: {e}")

# Global variables for tracking metrics
request_count = 0
error_count = 0
recent_predictions = []

def get_current_error_rate():
    """Calculate current error rate"""
    global request_count, error_count
    if request_count == 0:
        return 0.0
    return (error_count / request_count) * 100

# Fixed alerting metrics callbacks
def get_error_rate(options):
    """Fixed callback for error rate"""
    try:
        error_rate = get_current_error_rate()
        return [Observation(error_rate)]
    except Exception as e:
        logger.error(f"Error getting error rate: {e}")
        return [Observation(0.0)]

def get_high_error_alert(options):
    """Fixed callback for high error rate alert"""
    try:
        global request_count
        error_rate = get_current_error_rate()
        alert_value = 1.0 if error_rate > 50 and request_count >= 10 else 0.0
        return [Observation(alert_value)]
    except Exception as e:
        logger.error(f"Error getting high error alert: {e}")
        return [Observation(0.0)]

# Add alerting metrics that SigNoz can use for alerts
error_rate_gauge = meter.create_observable_gauge(
    name="api_error_rate",
    description="API error rate percentage",
    unit="%",
    callbacks=[get_error_rate]
)

low_confidence_counter = meter.create_counter(
    name="low_confidence_predictions",
    description="Number of predictions with confidence < 0.6",
)

high_error_rate_gauge = meter.create_observable_gauge(
    name="high_error_rate_alert",
    description="Alert when error rate > 50%",
    unit="1",
    callbacks=[get_high_error_alert]
)

@app.post("/predict")
def predict(passenger: Passenger):
    """Predict survival probability with SigNoz alerting metrics"""
    global request_count, error_count, recent_predictions
    
    with tracer.start_as_current_span("prediction") as span:
        start_time = time.time()
        request_count += 1
        
        try:
            # Add passenger data to span
            span.set_attribute("passenger.class", passenger.Pclass)
            span.set_attribute("passenger.sex", passenger.Sex)
            span.set_attribute("passenger.age", passenger.Age)
            
            # Convert to DataFrame
            X = pd.DataFrame([passenger.dict()])
            
            # Make prediction
            pred = model.predict(X)[0]
            pred_proba = model.predict_proba(X)[0]
            
            # Calculate confidence (max probability)
            confidence = float(max(pred_proba))
            
            # Processing time
            processing_time = time.time() - start_time
            
            # Record metrics
            prediction_counter.add(1, {"model": "random_forest", "result": str(pred)})
            prediction_duration.record(processing_time)
            model_confidence.record(confidence)
            
            # Add to span
            span.set_attribute("prediction.result", int(pred))
            span.set_attribute("prediction.confidence", confidence)
            span.set_attribute("prediction.processing_time", processing_time)
            
            result = "Sống sót" if pred == 1 else "Không sống sót"
            
            logger.info(f"Prediction made: {result}, confidence: {confidence:.3f}, processing_time: {processing_time:.3f}s")
            
            # Check for low confidence
            if confidence < 0.6:
                low_confidence_counter.add(1)
                recent_predictions.append(confidence)
                recent_predictions = recent_predictions[-10:]  # Keep only last 10
            
            return {
                "prediction": result,
                "confidence": round(confidence, 3),
                "processing_time": round(processing_time, 3),
                "probabilities": {
                    "not_survived": round(float(pred_proba[0]), 3),
                    "survived": round(float(pred_proba[1]), 3)
                }
            }
            
        except Exception as e:
            error_count += 1
            span.set_attribute("error", str(e))
            span.set_attribute("error.type", type(e).__name__)
            logger.error(f"Prediction error: {e}")
            raise HTTPException(status_code=400, detail=f"Prediction error: {e}")

@app.get("/simulate_error")
def simulate_error():
    """Simulate an error for testing"""
    global error_count
    error_count += 1
    
    with tracer.start_as_current_span("simulate_error") as span:
        span.set_attribute("error.simulated", True)
        span.set_attribute("error.type", "SimulatedError")
        logger.error("Simulated error endpoint called")
        raise HTTPException(status_code=500, detail="This is a simulated error for testing")

@app.get("/simulate_slow")
def simulate_slow():
    """Simulate a slow response for testing"""
    with tracer.start_as_current_span("simulate_slow") as span:
        sleep_time = random.uniform(2, 5)
        span.set_attribute("sleep_time", sleep_time)
        logger.warning(f"Simulating slow response: {sleep_time:.2f}s")
        time.sleep(sleep_time)
        return {"message": f"Slow response after {sleep_time:.2f} seconds"}

@app.get("/metrics/alerts")
def get_alert_metrics():
    """Get current metrics that SigNoz uses for alerting"""
    global request_count, error_count, recent_predictions
    
    current_error_rate = get_current_error_rate()
    avg_confidence = sum(recent_predictions) / len(recent_predictions) if recent_predictions else 1.0
    
    return {
        "timestamp": datetime.now().isoformat(),
        "error_rate": current_error_rate,
        "request_count": request_count,
        "error_count": error_count,
        "average_confidence": round(avg_confidence, 3),
        "recent_predictions_count": len(recent_predictions),
        "alerting_metrics": {
            "api_error_rate": current_error_rate,
            "low_confidence_predictions": sum(1 for c in recent_predictions if c < 0.6),
            "high_error_rate_alert": 1.0 if current_error_rate > 50 and request_count >= 10 else 0.0
        }
    }

@app.post("/reset-metrics")
def reset_metrics():
    """Reset metrics for testing"""
    global request_count, error_count, recent_predictions
    request_count = 0
    error_count = 0
    recent_predictions = []
    logger.info("Metrics reset for testing")
    return {"message": "Metrics reset successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)