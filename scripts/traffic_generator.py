import requests
import random
import time
import json
from datetime import datetime

API_BASE_URL = "http://localhost:8000"

def generate_passenger_data():
    """Generate random passenger data"""
    return {
        "Pclass": random.choice([1, 2, 3]),
        "Sex": random.choice(["male", "female"]),
        "Age": random.randint(1, 80),
        "SibSp": random.randint(0, 3),
        "Parch": random.randint(0, 2),
        "Fare": round(random.uniform(5, 500), 2),
        "Embarked": random.choice(["C", "Q", "S"])
    }

def make_prediction_request():
    """Make a prediction request"""
    try:
        passenger_data = generate_passenger_data()
        response = requests.post(
            f"{API_BASE_URL}/predict",
            json=passenger_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Prediction: {result['prediction']}, Confidence: {result['confidence']}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"🔌 Connection error: {e}")

def make_error_request():
    """Make a request that will cause an error"""
    try:
        response = requests.get(f"{API_BASE_URL}/simulate_error", timeout=5)
        print(f"🚨 Error request: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"🔌 Error request failed: {e}")

def make_slow_request():
    """Make a request that will be slow"""
    try:
        response = requests.get(f"{API_BASE_URL}/simulate_slow", timeout=10)
        if response.status_code == 200:
            print(f"🐌 Slow request completed")
        else:
            print(f"🐌 Slow request error: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"🔌 Slow request failed: {e}")

def main():
    """Main traffic generation loop"""
    print("🚀 Starting traffic generator...")
    print(f"📡 Target API: {API_BASE_URL}")
    
    # Test API availability
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API health check failed!")
            return
        print("✅ API is healthy, starting traffic generation...")
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to API!")
        return
    
    duration = 300  # 5 minutes
    requests_per_second = 3
    interval = 1.0 / requests_per_second
    
    start_time = time.time()
    request_count = 0
    
    print(f"⏱️  Running for {duration} seconds with {requests_per_second} RPS")
    
    while time.time() - start_time < duration:
        request_count += 1
        
        # 80% normal requests, 10% errors, 5% slow requests, 5% health checks
        rand = random.random()
        
        if rand < 0.80:
            make_prediction_request()
        elif rand < 0.90:
            make_error_request()
        elif rand < 0.95:
            make_slow_request()
        else:
            # Health check
            try:
                response = requests.get(f"{API_BASE_URL}/health", timeout=5)
                print(f"💓 Health check: {response.status_code}")
            except:
                print("💓 Health check failed")
        
        time.sleep(interval)
        
        if request_count % 20 == 0:
            elapsed = time.time() - start_time
            print(f"📊 Progress: {request_count} requests in {elapsed:.1f}s")
    
    print(f"✅ Traffic generation completed! Made {request_count} requests")

if __name__ == "__main__":
    main()