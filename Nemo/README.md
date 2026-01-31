# 🌊 Nemo - Real-time AI Companion Backend

> A low-latency, memory-enabled voice AI companion backend powered by Gemini, Mem0, and Edge-TTS.

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green?style=flat-square&logo=fastapi)
![WebSocket](https://img.shields.io/badge/WebSocket-Real--time-orange?style=flat-square)

## ✨ Features

- **⚡ Ultra-Fast LLM**: Gemini 2.5 Flash provides fast response times
- **🧠 Persistent Memory**: Mem0-powered personalization across sessions
- **🔊 Neural TTS**: Microsoft Edge's free, high-quality neural voices
- **🔌 Real-time WebSocket**: Low-latency bidirectional communication
- **🎭 Nemo Persona**: Sassy, empathetic AI friend personality
- **📡 REST API**: Alternative HTTP endpoints for flexibility

## 🏗️ Architecture

```
Nemo/
├── core/
│   ├── memory.py      # Mem0 Memory Service (context injection)
│   ├── llm.py         # Groq Client (ultra-fast inference)
│   └── tts.py         # Edge-TTS Wrapper (voice synthesis)
├── server.py          # FastAPI + WebSockets
├── .env.example       # Configuration template
└── requirements.txt   # Python dependencies
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd Nemo
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys:
# - GROQ_API_KEY (required): https://console.groq.com/
# - MEM0_API_KEY (required): https://app.mem0.ai/
```

### 3. Run the Server

```bash
python server.py
# Or with uvicorn directly:
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "Hey Shanaya, how are you?"}'
```

## 📡 WebSocket Protocol

Connect to `ws://localhost:8000/talk` for real-time voice conversations.

### Client → Server
```json
{
  "text": "Hey, I'm feeling a bit down today",
  "user_id": "optional_user_id"
}
```

### Server → Client
```json
{
  "audio": "base64_encoded_mp3_audio",
  "text": "Aww, I'm sorry to hear that. What's going on?",
  "visemes": []
}
```

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info and available endpoints |
| `/health` | GET | Service health check |
| `/chat` | POST | Chat with audio response |
| `/talk` | WebSocket | Real-time voice conversation |
| `/voices` | GET | List available TTS voices |
| `/memory` | POST | Explicitly save a memory |
| `/memory` | DELETE | Clear user memories |

## 🧠 How Memory Works

1. **Context Injection**: Before generating a response, relevant memories are retrieved using semantic search
2. **System Prompt Enhancement**: Memories are injected into Shanaya's system prompt
3. **Background Saving**: After responding, the conversation is saved asynchronously (non-blocking)

```
User: "I'm sad"
    ↓
Memory Search: Finds "User broke up last week"
    ↓
System Prompt: "...MEMORIES: User broke up last week..."
    ↓
Shanaya: "Hey, still thinking about the breakup? I'm here for you."
```

## 🔊 Voice Options

Using Microsoft Edge's neural voices (free, no API key needed):

| Preset | Voice ID | Description |
|--------|----------|-------------|
| `shanaya_default` | en-IN-NeerjaNeural | Natural, warm Indian English |
| `shanaya_expressive` | en-IN-NeerjaExpressiveNeural | More emotional range |
| `aria` | en-US-AriaNeural | US English female |
| `sonia` | en-GB-SoniaNeural | British English female |

## 🎯 Performance

| Component | Latency |
|-----------|---------|
| Groq LLM (llama-3.3-70b) | ~200-400ms |
| Memory Search | ~50-100ms |
| Edge-TTS Synthesis | ~100-300ms |
| **Total Response** | **~400-800ms** |

## 🔐 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | Groq API key for LLM |
| `MEM0_API_KEY` | ✅ | Mem0 API key for memory |
| `GROQ_MODEL` | ❌ | Model name (default: llama-3.3-70b-versatile) |
| `TTS_VOICE` | ❌ | Voice ID (default: en-IN-NeerjaExpressiveNeural) |
| `PORT` | ❌ | Server port (default: 8000) |
| `MEMORY_ENABLED` | ❌ | Enable memory (default: true) |

## 🔮 Frontend Integration

This backend is designed to work with any frontend that supports WebSockets. The frontend handles:
- **Speech-to-Text** (STT): Convert user speech to text
- **Audio Playback**: Play the base64 MP3 audio from responses
- **Optional**: Lip sync using viseme data (future feature)

### Example JavaScript Client

```javascript
const ws = new WebSocket('ws://localhost:8000/talk');

ws.onopen = () => console.log('Connected to Nemo');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Shanaya:', data.text);
  
  // Play audio
  const audio = new Audio('data:audio/mp3;base64,' + data.audio);
  audio.play();
};

// Send a message
ws.send(JSON.stringify({ text: "Hey Shanaya!" }));
```

## 🛠️ Development

```bash
# Run with auto-reload
uvicorn server:app --reload

# Run tests (coming soon)
pytest tests/

# Format code
black .
```

## 📝 License

MIT License - Built with ❤️ for Project Shanaya

---

*"She doesn't just chat. She remembers. She cares."* 🌊
