
import requests
import json

try:
    response = requests.get("http://localhost:8000/health")
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
