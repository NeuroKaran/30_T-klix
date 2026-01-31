
import sys
import os
from pathlib import Path

# Add project root to path (mimicking server.py)
project_root = str(Path(__file__).parent.parent.resolve())
if project_root not in sys.path:
    sys.path.append(project_root)

from mem_0 import get_memory_service
from config import get_config

def check_memory():
    print(f"Checking memory from: {os.getcwd()}")
    config = get_config()
    print(f"Configured Qdrant Path: {config.mem0_qdrant_path}")
    
    service = get_memory_service()
    
    # We will search for a specific unique token
    token = "SYNC_TEST_TOKEN_98765"
    print(f"Searching for token: {token}")
    
    # Search broadly
    memories = service.get_all(user_id="default", limit=100)
    found = False
    for mem in memories:
        if token in mem.content:
            print(f"✅ FOUND MEMORY: {mem.content}")
            found = True
            # Clean up
            service.delete(mem.id)
            print("Memory deleted after verification.")
            break
            
    if not found:
        print("❌ FAILED: Memory not found.")
        sys.exit(1)
    else:
        print("✅ SUCCESS: Synchronization confirmed.")

if __name__ == "__main__":
    check_memory()
