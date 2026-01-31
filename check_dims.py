import requests
import json

def check_dimensions():
    url = "http://localhost:11434/api/embeddings"
    data = {
        "model": "nomic-embed-text-v2-moe:latest",
        "prompt": "test dimension"
    }
    
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        embedding = response.json().get("embedding", [])
        print(f"Embedding length: {len(embedding)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_dimensions()
