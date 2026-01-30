
from config import get_config
from mem_0 import get_memory_service

def debug_search():
    config = get_config()
    print(f"User ID: {config.memory_user_id}")
    
    ms = get_memory_service(config)
    
    if not ms.is_enabled:
        print("Memory service disabled!")
        return


    print("\n--- Adding Test Memory ---")
    result = ms.add_text("Karan loves coding in Python", user_id=config.memory_user_id)
    print(f"Add result: {result}")
    import time
    time.sleep(2) # Wait for indexing

    queries = [
        "What does Karan love?",
        "coding",
        "Python"
    ]

    print("\n--- Testing Search ---")
    for q in queries:
        print(f"\nQuery: '{q}'")
        results = ms.search(q, user_id=config.memory_user_id)
        print(f"Found {len(results)} results:")
        for r in results:
            print(f" - {r.content} (score: {r.metadata.get('score', 'N/A')})")

    print("\n--- Testing Get All ---")
    all_mems = ms.get_all(user_id=config.memory_user_id, limit=5)
    for m in all_mems:
        print(f" - {m.content}")
        print(f"   Metadata: {m.metadata}")

if __name__ == "__main__":
    debug_search()
