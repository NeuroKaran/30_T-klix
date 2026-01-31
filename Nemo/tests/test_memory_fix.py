import asyncio
import websockets
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_memory():
    uri = "ws://localhost:8000/talk"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"Connected to {uri}")
            
            # Step 1: Teach the memory
            message_1 = "My name is Tester."
            payload_1 = {"text": message_1, "user_id": "test_user"}
            logger.info(f"Sending: {payload_1}")
            await websocket.send(json.dumps(payload_1))
            
            response_1 = await websocket.recv()
            logger.info(f"Received: {response_1}")
            
            # Allow some time for memory to be saved (it's backgrounded)
            logger.info("Waiting for memory to save (15s)...")
            await asyncio.sleep(15)
            
            # Step 2: Test retrieval
            message_2 = "What is my name?"
            payload_2 = {"text": message_2, "user_id": "test_user"}
            logger.info(f"Sending: {payload_2}")
            await websocket.send(json.dumps(payload_2))
            
            response_2 = await websocket.recv()
            logger.info(f"Received: {response_2}")
            
            response_data = json.loads(response_2)
            response_text = response_data.get("text", "")
            
            if "Tester" in response_text:
                logger.info("✅ SUCCESS: Memory retrieved correctly!")
            else:
                logger.error(f"❌ FAILURE: Memory NOT retrieved. Got: {response_text}")

    except Exception as e:
        logger.error(f"Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_memory())
