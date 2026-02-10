import requests
import time
import json


API_URL = "http://localhost:8000"

def test_api():
    """Test the MVP API endpoints"""
    
    print("🧪 Testing Cloud Cost Anomaly Detection MVP...")
    
    # Test 1: Health check
    print("1. Testing health check...")
    try:
        response = requests.get(f"{API_URL}/")
        if response.status_code == 200:
            print("   ✅ API is running")
        else:
            print(f"   ❌ API returned {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot connect to API: {e}")
        return False
    
    # Test 2: Trigger detection
    print("2. Triggering detection...")
    try:
        response = requests.post(f"{API_URL}/api/v1/detect?cloud=aws")
        if response.status_code in [200, 202]:
            print("   ✅ Detection triggered")
        else:
            print(f"   ❌ Detection failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error triggering detection: {e}")
    
    # Wait for detection to complete
    print("3. Waiting for detection to complete...")
    time.sleep(30)
    
    # Test 3: Get anomalies
    print("4. Fetching anomalies...")
    try:
        response = requests.get(f"{API_URL}/api/v1/anomalies")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Found {data['count']} anomalies")
            if data['count'] > 0:
                print(f"   📊 Severity breakdown:")
                print(f"      Critical: {data['summary']['critical']}")
                print(f"      High: {data['summary']['high']}")
                print(f"      Medium: {data['summary']['medium']}")
        else:
            print(f"   ❌ Failed to get anomalies: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error fetching anomalies: {e}")
    
    
    # Test 4: Get statistics
    print("5. Getting statistics...")
    try:
        response = requests.get(f"{API_URL}/api/v1/stats?hours=24")
        if response.status_code == 200:
            stats = response.json()
            print(f"   ✅ Stats retrieved")
            print(f"   💰 Estimated monthly savings: ${stats.get('estimated_monthly_savings', 0):,.2f}")
        else:
            print(f"   ❌ Failed to get stats: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting stats: {e}")
    
    print("\n🎉 MVP Testing Complete!")
    print(f"📊 Dashboard: http://localhost:8501")
    print(f"📚 API Docs: {API_URL}/docs")
    
    return True

if __name__ == "__main__":
    test_api()
