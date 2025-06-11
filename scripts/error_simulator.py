import requests
import time
import random

API_BASE_URL = "http://localhost:8000"

def simulate_high_error_rate():
    """Simulate high error rate scenario"""
    print("🚨 Simulating high error rate...")
    
    for i in range(20):
        try:
            # Send error requests
            response = requests.get(f"{API_BASE_URL}/simulate_error", timeout=5)
            print(f"Error request {i+1}: {response.status_code}")
        except Exception as e:
            print(f"Error request {i+1} failed: {e}")
        
        time.sleep(0.5)

def simulate_low_confidence_predictions():
    """Simulate scenario with potentially low confidence predictions"""
    print("🎯 Simulating edge case predictions...")
    
    edge_cases = [
        {"Pclass": 3, "Sex": "male", "Age": 50, "SibSp": 0, "Parch": 0, "Fare": 5.0, "Embarked": "S"},
        {"Pclass": 1, "Sex": "female", "Age": 2, "SibSp": 1, "Parch": 2, "Fare": 151.55, "Embarked": "S"},
        {"Pclass": 2, "Sex": "male", "Age": 45, "SibSp": 1, "Parch": 1, "Fare": 25.0, "Embarked": "Q"},
    ]
    
    for i, passenger in enumerate(edge_cases):
        try:
            response = requests.post(f"{API_BASE_URL}/predict", json=passenger, timeout=5)
            if response.status_code == 200:
                result = response.json()
                print(f"Edge case {i+1}: {result['prediction']}, Confidence: {result['confidence']}")
            else:
                print(f"Edge case {i+1} failed: {response.status_code}")
        except Exception as e:
            print(f"Edge case {i+1} error: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    print("🎭 Error Simulator Starting...")
    simulate_high_error_rate()
    time.sleep(5)
    simulate_low_confidence_predictions()
    print("✅ Error simulation completed!")