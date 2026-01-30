# Klix code

A sophisticated TUI-based AI Agent that replicates the "Claude Code" interface, powered by Google Gemini and Ollama, with advanced long-term memory.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Rich](https://img.shields.io/badge/TUI-rich-orange.svg)

## Features

- 🎨 **Beautiful TUI** - Dark mode interface with Tangerine Orange accents
- 🧠 **Hybrid Brain** - Google Gemini (cloud) + Ollama (local) support
- 🧠 **Persistent Memory** - Powered by Mem0 for long-term recall of user preferences and project context
- 🔧 **Built-in Tools** - File operations, shell commands, web search, and **OSINT suite** (DNS, WHOIS, Port Scanning)
- 💬 **Slash Commands** - `/init`, `/config`, `/model`, `/clear`, `/help`, `/memory`, `/forget`, `/remember`
- 📝 **Markdown Support** - Syntax-highlighted code and rich formatting
- 🔄 **Streaming** - Real-time response streaming
- 🚀 **Ecosystem** - Includes **Nemo** (AI Companion) and **Nova** (Advanced Platform) sub-projects

## Installation

1. **Clone and setup:**
   ```bash
   cd Terent
   pip install -r requirements.txt
   ```

2. **Configure API keys:**
   ```bash
   cp .env.example .env
   # Edit .env and add your GOOGLE_API_KEY and MEM0_API_KEY
   ```

3. **Run:**
   ```bash
   python main.py
   ```

## Usage

### Basic Commands

```bash
# Start with Gemini (default)
python main.py

# Start with local Ollama
python main.py --local

# Use specific model
python main.py --model gemini-1.5-flash

# Initialize with project directory
python main.py --project ./my-project
```

### Slash Commands

| Command | Description |
|---------|-------------|
| `/init [path]` | Initialize project context |
| `/config` | View or change configuration |
| `/model [name]` | Switch between models (gemini/ollama) |
| `/clear` | Clear conversation context |
| `/tools` | Show available tools |
| `/status` | Show current status |
| `/memory` | View and search persistent memories |
| `/forget` | Delete a memory or all memories |
| `/remember` | Manually add a memory |
| `/help` | Show all commands |
| `/quit` | Exit Klix code (alias: `/exit`) |

### Available Tools

The agent has access to these tools:

- **ls** - List files in a directory
- **read_file** - Read file contents
- **write_file** - Create or overwrite files
- **append_file** - Append to files
- **delete_file** - Delete files
- **run_command** - Execute shell commands
- **web_search** - Search the web (alias: `search_web`)
- **get_project_structure** - View project tree
- **dns_lookup** - Perform DNS records lookup
- **whois_lookup** - Get domain registration info
- **port_scan** - Scan target for open ports
- **http_headers** - Fetch and analyze HTTP headers

## Architecture

```
┌─────────────────────────────────────────────────┐
│                    TUI Layer                     │
│              (tui.py - rich library)             │
└─────────────────────────────────────────────────┘
                        │
┌─────────────────────────────────────────────────┐
│                  Agent Loop                      │
│         (main.py - AgentLoop class)              │
│  ┌────────────┐  ┌────────────────────────────┐ │
│  │   Memory   │  │    Slash Commands          │ │
│  │  Manager   │  │  /init /config /clear etc  │ │
│  └────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────┘
                        │
┌─────────────────────────────────────────────────┐
│              LLM Client Layer                    │
│          (llm_client.py - adapters)              │
│  ┌────────────────┐  ┌──────────────────────┐   │
│  │ GeminiClient   │  │   OllamaClient       │   │
│  │ (cloud)        │  │   (local)            │   │
│  └────────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────┘
                        │
┌─────────────────────────────────────────────────┐
│                 Tools Layer                      │
│    (tools.py - ToolRegistry + implementations)   │
└─────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google AI Studio API key | (required for Gemini) |
| `MEM0_API_KEY` | Mem0 API key for persistent memory | (optional) |
| `MEMORY_ENABLED` | Enable persistent memory | `true` |
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `DEFAULT_MODEL` | Default model to use | `gemini-1.5-flash` |
| `GEMINI_MODEL` | Specific Gemini model | `gemini-1.5-flash` |
| `OLLAMA_MODEL` | Specific Ollama model | `qwen2.5-coder` |
| `USER_NAME` | Display name in header | `Karan` |
| `ORG_NAME` | Organization name | `NeuroKaran's Org` |

### Gemini Safety Settings

By default, all safety settings are set to `BLOCK_NONE` for maximum developer freedom when working with code. This can be configured in `config.py`.

## Requirements

- Python 3.10+
- Google AI Studio API key (for Gemini)
- Mem0 API key (for persistent memory)
- Ollama installed locally (for local mode)
- OSINT Deps: `pip install dnspython python-whois requests`

## Project Ecosystem

### 🤖 Nemo
A personalized AI companion with a dual-interface approach:
- **Core**: Advanced LLM integration with fallback mechanisms.
- **Frontend**: A modern, responsive web dashboard and a sleek TUI.
- **Server**: FastAPI-based backend for seamless agent interaction.

### 🌟 Nova
A high-performance, modular platform designed for scale:
- **Backend**: Robust Python backend with structured data models and agentic logic.
- **Frontend**: A cutting-edge web interface built for speed and visual excellence.
- **Design**: Focused on modularity and extensibility.

## License

MIT
