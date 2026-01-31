from qdrant_client import QdrantClient
import os

def inspect_qdrant():
    qdrant_path = os.path.abspath("./.qdrant_data")
    print(f"Connecting to Qdrant at {qdrant_path}")
    client = QdrantClient(path=qdrant_path)
    
    collections = client.get_collections().collections
    print(f"Collections: {[c.name for c in collections]}")
    
    for c in collections:
        count = client.count(collection_name=c.name).count
        print(f"Collection '{c.name}' has {count} points.")
        
        # Get some points
        points, _ = client.scroll(collection_name=c.name, limit=5)
        for p in points:
            print(f" - Point ID: {p.id}")
            print(f"   Payload: {p.payload}")
            # print(f"   Vector preview: {p.vector[:5]}...") # Vector is usually hidden in scroll unless specified
    
    client.close()

if __name__ == "__main__":
    inspect_qdrant()
