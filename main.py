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
import syslog
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

# Environment variables
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://signoz-otel-collector:4317")
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "titanic-api")
SERVICE_VERSION = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")

# Create logs directory
os.makedirs('/app/logs', exist_ok=True)

# Configure syslog logging (if available)
try:
    syslog.openlog("titanic-api", syslog.LOG_PID, syslog.LOG_USER)
    SYSLOG_AVAILABLE = True
except:
    SYSLOG_AVAILABLE = False

# Configure logging với JSON format cho SigNoz
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "service": "' + SERVICE_NAME + '", "version": "' + SERVICE_VERSION + '"}',
    handlers=[
        logging.FileHandler('/app/logs/app.log'),
        logging.StreamHandler()  # stdout logs
    ]
)
logger = logging.getLogger(__name__)

def log_to_syslog(message, priority=syslog.LOG_INFO):
    """Log to syslog if available"""
    if SYSLOG_AVAILABLE:
        try:
            syslog.syslog(priority, f"titanic-api: {message}")
        except:
            pass

# Configure OpenTelemetry
resource = Resource.create({
    "service.name": SERVICE_NAME, 
    "service.version": SERVICE_VERSION,
    "deployment.environment": "development"
})

# Tracing setup
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer_provider = trace.get_tracer_provider()
otlp_exporter = OTLPSpanExporter(
    endpoint=OTEL_ENDPOINT,
    insecure=True,
)
span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)

# Metrics setup
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(
        endpoint=OTEL_ENDPOINT,
        insecure=True,
    ),
    export_interval_millis=5000,  # 5 seconds for faster updates
)
metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

# Get tracer and meter
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Core prediction metrics
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

# HTTP request metrics
http_requests_total = meter.create_counter(
    name="http_requests_total",
    description="Total HTTP requests",
)

http_request_duration = meter.create_histogram(
    name="http_request_duration_seconds", 
    description="HTTP request duration",
    unit="s",
)

http_errors_total = meter.create_counter(
    name="http_errors_total",
    description="Total HTTP errors",
)

# System metrics callbacks với error handling
def get_cpu_usage(options):
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        return [Observation(cpu_percent)]
    except Exception as e:
        logger.error(f"Error getting CPU usage: {e}")
        return [Observation(0.0)]

def get_memory_usage(options):
    try:
        memory_percent = psutil.virtual_memory().percent
        return [Observation(memory_percent)]
    except Exception as e:
        logger.error(f"Error getting memory usage: {e}")
        return [Observation(0.0)]

def get_disk_usage(options):
    try:
        disk_percent = psutil.disk_usage('/').percent
        return [Observation(disk_percent)]
    except Exception as e:
        logger.error(f"Error getting disk usage: {e}")
        return [Observation(0.0)]

def get_disk_read_bytes(options):
    try:
        disk_io = psutil.disk_io_counters()
        if disk_io:
            return [Observation(disk_io.read_bytes)]
        return [Observation(0.0)]
    except Exception as e:
        logger.error(f"Error getting disk read bytes: {e}")
        return [Observation(0.0)]

def get_disk_write_bytes(options):
    try:
        disk_io = psutil.disk_io_counters()
        if disk_io:
            return [Observation(disk_io.write_bytes)]
        return [Observation(0.0)]
    except Exception as e:
        logger.error(f"Error getting disk write bytes: {e}")
        return [Observation(0.0)]

def get_network_sent(options):
    try:
        network = psutil.net_io_counters()
        return [Observation(network.bytes_sent)]
    except Exception as e:
        logger.error(f"Error getting network sent: {e}")
        return [Observation(0.0)]

def get_network_recv(options):
    try:
        network = psutil.net_io_counters()
        return [Observation(network.bytes_recv)]
    except Exception as e:
        logger.error(f"Error getting network received: {e}")
        return [Observation(0.0)]

# System metrics (No GPU)
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

system_disk_gauge = meter.create_observable_gauge(
    name="system_disk_usage_percent",
    description="System disk usage percentage", 
    unit="%",
    callbacks=[get_disk_usage]
)

system_disk_read = meter.create_observable_counter(
    name="system_disk_read_bytes",
    description="Disk read bytes",
    unit="bytes",
    callbacks=[get_disk_read_bytes]
)

system_disk_write = meter.create_observable_counter(
    name="system_disk_write_bytes",
    description="Disk write bytes",
    unit="bytes",
    callbacks=[get_disk_write_bytes]
)

system_network_sent = meter.create_observable_counter(
    name="system_network_bytes_sent",
    description="System network bytes sent",
    unit="bytes",
    callbacks=[get_network_sent]
)

system_network_recv = meter.create_observable_counter(
    name="system_network_bytes_recv", 
    description="System network bytes received",
    unit="bytes",
    callbacks=[get_network_recv]
)

# Global variables for tracking metrics
request_count = 0
error_count = 0
recent_predictions = []
service_start_time = time.time()

def get_current_error_rate():
    global request_count, error_count
    if request_count == 0:
        return 0.0
    return (error_count / request_count) * 100

def get_requests_per_second():
    global request_count, service_start_time
    elapsed = time.time() - service_start_time
    if elapsed == 0:
        return 0.0
    return request_count / elapsed

def get_error_rate(options):
    try:
        error_rate = get_current_error_rate()
        return [Observation(error_rate)]
    except Exception as e:
        logger.error(f"Error getting error rate: {e}")
        return [Observation(0.0)]

def get_request_rate(options):
    try:
        request_rate = get_requests_per_second()
        return [Observation(request_rate)]
    except Exception as e:
        logger.error(f"Error getting request rate: {e}")
        return [Observation(0.0)]

def get_avg_confidence(options):
    global recent_predictions
    try:
        if len(recent_predictions) > 0:
            avg_confidence = sum(recent_predictions) / len(recent_predictions)
            return [Observation(avg_confidence)]
        return [Observation(1.0)]
    except Exception as e:
        logger.error(f"Error getting average confidence: {e}")
        return [Observation(1.0)]

api_error_rate_gauge = meter.create_observable_gauge(
    name="api_error_rate_percent",
    description="API error rate percentage",
    unit="%",
    callbacks=[get_error_rate]
)

api_request_rate_gauge = meter.create_observable_gauge(
    name="api_request_rate_per_second",
    description="API request rate per second",
    unit="req/s",
    callbacks=[get_request_rate]
)

model_avg_confidence_gauge = meter.create_observable_gauge(
    name="model_avg_confidence_score",
    description="Average model confidence score",
    unit="1",
    callbacks=[get_avg_confidence]
)

low_confidence_counter = meter.create_counter(
    name="low_confidence_predictions",
    description="Number of predictions with confidence < 0.6",
)

high_confidence_counter = meter.create_counter(
    name="high_confidence_predictions", 
    description="Number of predictions with confidence > 0.9",
)

app = FastAPI(
    title="Titanic Survival Prediction API with SigNoz Monitoring",
    description="API dự đoán khả năng sống sót trên Titanic với monitoring và logging đầy đủ",
    version=SERVICE_VERSION
)

@app.on_event("startup")
async def startup_event():
    startup_message = f"🚀 Starting {SERVICE_NAME} v{SERVICE_VERSION}"
    logger.info(startup_message)
    log_to_syslog(startup_message)
    logger.info(f"📡 OpenTelemetry endpoint: {OTEL_ENDPOINT}")
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        health_message = f"💻 System health - CPU: {cpu_percent}%, Memory: {memory_percent}%, Disk: {disk_percent}%"
        logger.info(health_message)
        log_to_syslog(health_message)
        if 'model' in globals():
            model_message = "🤖 ML Model loaded successfully"
            logger.info(model_message)
            log_to_syslog(model_message)
        else:
            error_message = "❌ ML Model not loaded"
            logger.error(error_message)
            log_to_syslog(error_message, syslog.LOG_ERR)
    except Exception as e:
        error_message = f"❌ Startup check failed: {e}"
        logger.error(error_message)
        log_to_syslog(error_message, syslog.LOG_ERR)

@app.on_event("shutdown")
async def shutdown_event():
    global request_count, error_count, service_start_time
    shutdown_message = f"🛑 Shutting down {SERVICE_NAME}"
    logger.info(shutdown_message)
    log_to_syslog(shutdown_message)
    uptime = time.time() - service_start_time
    avg_rps = request_count / uptime if uptime > 0 else 0
    stats_message = f"📊 Final stats - Requests: {request_count}, Errors: {error_count}, Uptime: {uptime:.1f}s, Avg RPS: {avg_rps:.2f}"
    logger.info(stats_message)
    log_to_syslog(stats_message)

FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
RequestsInstrumentor().instrument()

MODEL_PATH = "best_rf_model.pkl"

if not os.path.exists(MODEL_PATH):
    error_message = f"❌ Model file '{MODEL_PATH}' not found"
    logger.error(error_message)
    log_to_syslog(error_message, syslog.LOG_ERR)
    raise RuntimeError(f"Model file '{MODEL_PATH}' not found")

try:
    model = joblib.load(MODEL_PATH)
    success_message = f"✅ Model loaded successfully from {MODEL_PATH}"
    logger.info(success_message)
    log_to_syslog(success_message)
except Exception as e:
    error_message = f"❌ Could not load model: {e}"
    logger.error(error_message)
    log_to_syslog(error_message, syslog.LOG_ERR)
    raise RuntimeError(f"Could not load model: {e}")

class Passenger(BaseModel):
    Pclass: int = Field(..., ge=1, le=3, description="Passenger class (1, 2, or 3)")
    Sex: str = Field(..., description="Gender (male or female)")
    Age: float = Field(..., ge=0, le=100, description="Age in years")
    SibSp: int = Field(..., ge=0, description="Number of siblings/spouses aboard")
    Parch: int = Field(..., ge=0, description="Number of parents/children aboard")
    Fare: float = Field(..., ge=0, description="Passenger fare")
    Embarked: str = Field(..., description="Port of embarkation (C, Q, or S)")

@app.middleware("http")
async def track_requests(request, call_next):
    global request_count, error_count
    request_start_time = time.time()
    request_count += 1
    http_requests_total.add(1, {
        "method": request.method,
        "endpoint": request.url.path
    })
    try:
        response = await call_next(request)
        duration = time.time() - request_start_time
        http_request_duration.record(duration, {
            "method": request.method,
            "endpoint": request.url.path,
            "status_code": str(response.status_code)
        })
        if response.status_code >= 400:
            error_count += 1
            http_errors_total.add(1, {
                "method": request.method,
                "endpoint": request.url.path,
                "status_code": str(response.status_code)
            })
            error_message = f"HTTP {response.status_code} error on {request.method} {request.url.path}"
            log_to_syslog(error_message, syslog.LOG_WARNING)
        return response
    except Exception as e:
        error_count += 1
        duration = time.time() - request_start_time
        http_errors_total.add(1, {
            "method": request.method,
            "endpoint": request.url.path,
            "error": type(e).__name__
        })
        error_message = f"❌ Unhandled request error: {e}"
        logger.error(error_message)
        log_to_syslog(error_message, syslog.LOG_ERR)
        raise

@app.get("/")
def root():
    logger.info("📍 Root endpoint accessed")
    return {
        "message": "Titanic Survival Prediction API", 
        "status": "running",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "monitoring": {
            "syslog": SYSLOG_AVAILABLE,
            "tracing": True,
            "metrics": True
        },
        "endpoints": {
            "predict": "/predict",
            "health": "/health",
            "docs": "/docs",
            "metrics": "/metrics/system"
        }
    }

@app.get("/health")
def health_check():
    global request_count, error_count, service_start_time
    with tracer.start_as_current_span("health_check") as span:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            network = psutil.net_io_counters()
            span.set_attribute("cpu_usage", cpu_percent)
            span.set_attribute("memory_usage", memory.percent)
            span.set_attribute("disk_usage", disk.percent)
            uptime = time.time() - service_start_time
            rps = request_count / uptime if uptime > 0 else 0
            error_rate = get_current_error_rate()
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": SERVICE_NAME,
                "version": SERVICE_VERSION,
                "uptime_seconds": round(uptime, 1),
                "system": {
                    "cpu_usage_percent": round(cpu_percent, 1),
                    "memory_usage_percent": round(memory.percent, 1),
                    "disk_usage_percent": round(disk.percent, 1),
                    "disk_io": {
                        "read_bytes": disk_io.read_bytes if disk_io else 0,
                        "write_bytes": disk_io.write_bytes if disk_io else 0
                    },
                    "network": {
                        "bytes_sent": network.bytes_sent,
                        "bytes_recv": network.bytes_recv
                    }
                },
                "api": {
                    "total_requests": request_count,
                    "total_errors": error_count,
                    "error_rate_percent": round(error_rate, 2),
                    "requests_per_second": round(rps, 2)
                },
                "model": {
                    "status": "loaded",
                    "recent_predictions": len(recent_predictions)
                },
                "logging": {
                    "syslog_available": SYSLOG_AVAILABLE,
                    "file_logging": True,
                    "stdout_logging": True
                }
            }
            health_message = f"💚 Health check OK - CPU: {cpu_percent:.1f}%, Memory: {memory.percent:.1f}%, RPS: {rps:.2f}"
            logger.info(health_message)
            log_to_syslog(health_message)
            return health_data
        except Exception as e:
            span.set_attribute("error", str(e))
            error_message = f"❌ Health check error: {e}"
            logger.error(error_message)
            log_to_syslog(error_message, syslog.LOG_ERR)
            return {
                "status": "degraded",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "service": SERVICE_NAME
            }

@app.post("/predict")
def predict(passenger: Passenger):
    global recent_predictions
    with tracer.start_as_current_span("prediction") as span:
        prediction_start_time = time.time()
        try:
            if passenger.Sex.lower() not in ['male', 'female']:
                raise ValueError("Sex must be 'male' or 'female'")
            if passenger.Embarked.upper() not in ['C', 'Q', 'S']:
                raise ValueError("Embarked must be 'C', 'Q', or 'S'")
            span.set_attribute("passenger.class", passenger.Pclass)
            span.set_attribute("passenger.sex", passenger.Sex)
            span.set_attribute("passenger.age", passenger.Age)
            span.set_attribute("passenger.fare", passenger.Fare)
            input_data = {
                'Pclass': passenger.Pclass,
                'Sex': 1 if passenger.Sex.lower() == 'male' else 0,
                'Age': passenger.Age,
                'SibSp': passenger.SibSp,
                'Parch': passenger.Parch,
                'Fare': passenger.Fare,
                'Embarked_Q': 1 if passenger.Embarked.upper() == 'Q' else 0,
                'Embarked_S': 1 if passenger.Embarked.upper() == 'S' else 0
            }
            X = pd.DataFrame([input_data])
            pred = model.predict(X)[0]
            pred_proba = model.predict_proba(X)[0]
            confidence = float(max(pred_proba))
            processing_time = time.time() - prediction_start_time
            result = "Sống sót" if pred == 1 else "Không sống sót"
            prediction_counter.add(1, {
                "model": "random_forest", 
                "result": str(pred),
                "passenger_class": str(passenger.Pclass)
            })
            prediction_duration.record(processing_time)
            model_confidence.record(confidence)
            if confidence < 0.6:
                low_confidence_counter.add(1)
                warning_message = f"⚠️ Low confidence prediction: {confidence:.3f}"
                logger.warning(warning_message)
                log_to_syslog(warning_message, syslog.LOG_WARNING)
            elif confidence > 0.9:
                high_confidence_counter.add(1)
            recent_predictions.append(confidence)
            recent_predictions = recent_predictions[-20:]
            span.set_attribute("prediction.result", int(pred))
            span.set_attribute("prediction.confidence", confidence)
            span.set_attribute("prediction.processing_time", processing_time)
            span.set_attribute("prediction.text", result)
            log_data = {
                "event": "prediction_made",
                "result": result,
                "confidence": round(confidence, 3),
                "processing_time": round(processing_time, 3),
                "passenger_class": passenger.Pclass,
                "passenger_age": passenger.Age,
                "passenger_sex": passenger.Sex
            }
            logger.info(json.dumps(log_data))
            syslog_message = f"Prediction: {result}, Confidence: {confidence:.3f}, Time: {processing_time:.3f}s"
            log_to_syslog(syslog_message)
            response = {
                "prediction": result,
                "confidence": round(confidence, 3),
                "processing_time": round(processing_time, 3),
                "probabilities": {
                    "not_survived": round(float(pred_proba[0]), 3),
                    "survived": round(float(pred_proba[1]), 3)
                },
                "passenger_info": {
                    "class": passenger.Pclass,
                    "sex": passenger.Sex,
                    "age": passenger.Age
                },
                "service": SERVICE_NAME,
                "timestamp": datetime.now().isoformat()
            }
            return response
        except ValueError as e:
            span.set_attribute("error", str(e))
            span.set_attribute("error.type", "ValidationError")
            error_message = f"❌ Validation error: {e}"
            logger.error(error_message)
            log_to_syslog(error_message, syslog.LOG_ERR)
            raise HTTPException(status_code=422, detail=f"Validation error: {e}")
        except Exception as e:
            processing_time = time.time() - prediction_start_time
            span.set_attribute("error", str(e))
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("processing_time", processing_time)
            error_message = f"❌ Prediction error: {e}"
            logger.error(error_message, exc_info=True)
            log_to_syslog(error_message, syslog.LOG_ERR)
            raise HTTPException(status_code=500, detail=f"Prediction error: {e}")

@app.post("/simulate_error")
def simulate_error():
    with tracer.start_as_current_span("simulate_error") as span:
        span.set_attribute("error.simulated", True)
        span.set_attribute("error.type", "SimulatedError")
        error_type = random.choice(["server_error", "database_error", "model_error", "timeout"])
        span.set_attribute("error.subtype", error_type)
        error_message = f"🚨 Simulated {error_type} for testing alerting system"
        logger.error(error_message)
        log_to_syslog(error_message, syslog.LOG_ERR)
        error_details = {
            "server_error": "Internal server error occurred",
            "database_error": "Database connection failed", 
            "model_error": "Model inference failed",
            "timeout": "Request timeout exceeded"
        }
        raise HTTPException(
            status_code=500, 
            detail=f"Simulated {error_type}: {error_details.get(error_type, 'Unknown error')}"
        )

@app.get("/metrics/system")
def get_system_metrics():
    with tracer.start_as_current_span("system_metrics"):
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            network = psutil.net_io_counters()
            metrics_data = {
                "timestamp": datetime.now().isoformat(),
                "service": SERVICE_NAME,
                "system": {
                    "cpu": {
                        "usage_percent": round(cpu_percent, 2),
                        "count": cpu_count
                    },
                    "memory": {
                        "total_bytes": memory.total,
                        "available_bytes": memory.available,
                        "used_bytes": memory.used,
                        "usage_percent": round(memory.percent, 2)
                    },
                    "disk": {
                        "total_bytes": disk.total,
                        "used_bytes": disk.used,
                        "free_bytes": disk.free,
                        "usage_percent": round(disk.percent, 2),
                        "io": {
                            "read_bytes": disk_io.read_bytes if disk_io else 0,
                            "write_bytes": disk_io.write_bytes if disk_io else 0,
                            "read_count": disk_io.read_count if disk_io else 0,
                            "write_count": disk_io.write_count if disk_io else 0
                        }
                    },
                    "network": {
                        "bytes_sent": network.bytes_sent,
                        "bytes_recv": network.bytes_recv,
                        "packets_sent": network.packets_sent,
                        "packets_recv": network.packets_recv
                    }
                }
            }
            logger.info(f"📊 System metrics collected - CPU: {cpu_percent:.1f}%, Memory: {memory.percent:.1f}%")
            log_to_syslog(f"System metrics - CPU: {cpu_percent:.1f}%, Memory: {memory.percent:.1f}%")
            return metrics_data
        except Exception as e:
            error_message = f"❌ Error collecting system metrics: {e}"
            logger.error(error_message)
            log_to_syslog(error_message, syslog.LOG_ERR)
            raise HTTPException(status_code=500, detail=f"Error collecting metrics: {e}")

@app.get("/info")
def get_service_info():
    global request_count, error_count, service_start_time
    uptime = time.time() - service_start_time
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "description": "Titanic Survival Prediction API with SigNoz monitoring",
        "otlp_endpoint": OTEL_ENDPOINT,
        "model_info": {
            "path": MODEL_PATH,
            "type": "Random Forest Classifier (ML - No GPU needed)",
            "status": "loaded"
        },
        "runtime_stats": {
            "uptime_seconds": round(uptime, 1),
            "total_requests": request_count,
            "total_errors": error_count,
            "requests_per_second": round(request_count / uptime if uptime > 0 else 0, 2)
        },
        "monitoring": {
            "tracing": "enabled",
            "metrics": "enabled", 
            "logging": {
                "file": "enabled",
                "stdout": "enabled",
                "stderr": "enabled",
                "syslog": "enabled" if SYSLOG_AVAILABLE else "not available"
            },
            "alerting": "SigNoz native alerting"
        },
        "system_monitoring": {
            "cpu": "enabled",
            "memory": "enabled",
            "disk_space": "enabled",
            "disk_io": "enabled",
            "network_io": "enabled",
            "gpu": "not needed (ML model)"
        },
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")