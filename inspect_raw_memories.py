from config import get_config
from mem_0 import get_memory_service

def inspect_raw_memories():
    config = get_config()
    ms = get_memory_service(config)
    
    if not ms.is_enabled:
        print("Memory service disabled!")
        return

    print("\n--- Raw Memories from get_all ---")
    # Access private client to get raw data
    user_id = config.memory_user_id
    raw_results = ms._client.get_all(user_id=user_id)
    print(f"Raw results type: {type(raw_results)}")
    
    items = raw_results.get("results", []) if isinstance(raw_results, dict) else raw_results
    for i, item in enumerate(items):
        print(f"\nItem {i}:")
        print(item)

if __name__ == "__main__":
    inspect_raw_memories()
