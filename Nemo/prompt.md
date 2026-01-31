Act as a senior developer with 60 years of experience.
Create the prompt.md file that asks the Claude opus4.5 to build this - 
Implementation Plan
1. The Directory Structure
We will organize this exactly like the Klix backend to keep it modular.
Plaintext

Nemo/
├── core/
│   ├── memory.py          # The Klix Memory Service (Mem0)
│   ├── llm.py             # Groq Client
│   └── tts.py             # Edge-TTS Wrapper
├── server.py              # FastAPI + WebSockets
└── .env                   # API Keys (Groq, Deepgram, Mem0)
2. The Memory Service (Borrowed from Klix)
We use the exact logic from your Klix PROJECT.md, but tuned for conversation.
core/memory.py
Python

from mem0 import Memoryimport osclass MemoryService:
    def __init__(self):
        # Initialize Mem0 (uses Qdrant or local vector store by default)
        self.m = Memory()
        self.user_id = "user_default"

    def get_context(self, text: str) -> str:
        """
        Searches past conversations for relevant info.
        Example: If user says "I'm sad", it might recall "User broke up last week".
        """
        memories = self.m.search(text, user_id=self.user_id, limit=3)
        context_str = "\n".join([m['memory'] for m in memories])
        return context_str

    def save_interaction(self, user_text: str, agent_text: str):
        """
        Saves the turn to long-term memory.
        """
        # We store the combined interaction
        self.m.add(f"User: {user_text} | Shanaya: {agent_text}", user_id=self.user_id)
3. The Real-Time Backend (FastAPI)
Here is where we handle the latency. Crucial: We use FastAPI's BackgroundTasks to save memory after we respond, so we don't delay the voice response.
server.py
Python

from fastapi import FastAPI, WebSocket, BackgroundTasksfrom core.memory import MemoryServicefrom core.llm import GroqClientfrom core.tts import TextToSpeechimport asyncio

app = FastAPI()
memory_service = MemoryService()
llm = GroqClient()
tts = TextToSpeech()@app.websocket("/talk")async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # 1. Receive Audio (or Text) from Frontend
            data = await websocket.receive_json()
            user_text = data['text'] # Assuming STT happened on client or previous step

            # 2. Retrieve Memory (The Klix "Context Injection")
            # We fetch memories related to what the user just said
            past_context = memory_service.get_context(user_text)
            
            print(f"🧠 Recalled: {past_context}")

            # 3. Construct System Prompt with Memory
            system_prompt = f"""
            You are Shanaya, a sassy and empathetic friend.
            
            RELEVANT MEMORIES (Use these to personalize the chat):
            {past_context}
            
            Keep responses short (under 2 sentences) and conversational.
            """

            # 4. Generate Response (Groq)
            response_text = await llm.generate(user_text, system_prompt)

            # 5. Stream Audio (Edge-TTS) & Send to Client
            audio_base64 = await tts.synthesize(response_text)
            
            await websocket.send_json({
                "audio": audio_base64,
                "text": response_text,
                "visemes": [] # Optional: for lip sync
            })

            # 6. Save to Memory (Async - NON-BLOCKING)
            # This ensures the user doesn't wait for the DB write
            # We run this in a background thread or just await it if fast enough
            asyncio.create_task(
                async_save_memory(user_text, response_text)
            )

    except Exception as e:
        print(f"Error: {e}")async def async_save_memory(user_text, agent_text):
    print("💾 Saving memory in background...")
    memory_service.save_interaction(user_text, agent_text)
4. The Frontend (React + Three.js)
The frontend remains the same as the plan for Project Shanaya. It blindly plays whatever audio it receives. It doesn't need to know that the backend used a vector database; it just "feels" smarter.