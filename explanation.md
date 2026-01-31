# Terent Architecture Explanation

## Overview

Terent is a sophisticated TUI-based AI Agent that replicates the "Claude Code" interface, powered by Google Gemini and Ollama, with advanced long-term memory capabilities. The architecture is designed to be modular, extensible, and efficient.

## Architecture Layers

The system is organized into several distinct layers:

1. **TUI Layer**: User interface using Rich library
2. **Agent Loop**: Core conversation and tool management
3. **LLM Client Layer**: Abstraction for different LLM providers
4. **Memory Layer**: Persistent memory using Mem0
5. **Tools Layer**: File operations, web search, and OSINT tools

```mermaid
graph TD
    A[TUI Layer] --> B[Agent Loop]
    B --> C[LLM Client Layer]
    B --> D[Memory Layer]
    B --> E[Tools Layer]
    C --> F[Gemini Client]
    C --> G[Ollama Client]
    D --> H[Mem0 Cloud API]
    D --> I[Mem0 Local Qdrant]
```

## Key Components

### 1. TUI Layer (`tui.py`)

The Text User Interface layer provides a beautiful, dark-mode interface with Tangerine Orange accents. It handles:

- User input/output
- Message rendering with syntax highlighting
- Status indicators and activity tracking
- Slash command interface

### 2. Agent Loop (`main.py`)

The core of the system, the `AgentLoop` class manages:

- **Memory Management**: Sliding window approach for conversation context
- **Slash Commands**: `/init`, `/config`, `/model`, `/clear`, `/help`, `/memory`, `/forget`, `/remember`
- **Tool Execution**: File operations, web search, OSINT tools
- **LLM Interaction**: Sending messages, receiving responses, handling tool calls
- **Context Injection**: Adding memory context to LLM prompts

### 3. LLM Client Layer (`llm_client.py`)

This layer provides an abstraction over different LLM providers:

- **GeminiClient**: Google Gemini API integration
- **OllamaClient**: Local Ollama model integration
- **Standardized Interface**: Common methods for chat, streaming, and tool usage
- **Message Conversion**: Converts between internal format and provider-specific formats

```mermaid
classDiagram
    class LLMClient {
        +chat(messages, tools, stream)
        +close()
        +generate(prompt)
        +set_system_instruction(instruction)
    }
    
    class GeminiClient {
        +chat(messages, tools, stream)
        +close()
        +generate(prompt)
    }
    
    class OllamaClient {
        +chat(messages, tools, stream)
        +close()
        +generate(prompt)
    }
    
    LLMClient <|-- GeminiClient
    LLMClient <|-- OllamaClient
```

### 4. Memory Layer (`mem_0.py`)

The persistent memory layer uses Mem0 for long-term recall:

- **MemoryService**: Main interface for memory operations
- **Memory Types**: Episodic (events), Semantic (facts), Procedural (how-to)
- **Search**: Semantic search for relevant memories
- **Context Building**: Formats memories for LLM injection
- **Auto-extraction**: Automatically extracts and stores memories from conversations

```mermaid
classDiagram
    class MemoryService {
        +search(query, user_id, limit)
        +get_all(user_id, limit)
        +add(messages, user_id, memory_type)
        +get_memory_context(query, user_id, max_memories)
        +extract_and_store(user_input, assistant_response, user_id)
    }
    
    class MemoryItem {
        +id: str
        +content: str
        +memory_type: MemoryType
        +created_at: datetime
        +metadata: dict
    }
    
    class MemoryType {
        <<enumeration>>
        EPISODIC
        SEMANTIC
        PROCEDURAL
    }
    
    MemoryService "1" *-- "0..*" MemoryItem
    MemoryItem "1" *-- "1" MemoryType
```

### 5. Tools Layer (`tools.py`)

The tools layer provides various utilities:

- **File Operations**: `ls`, `read_file`, `write_file`, `append_file`, `delete_file`
- **System Commands**: `run_command`
- **Web Search**: `web_search`
- **Project Tools**: `get_project_structure`
- **OSINT Tools**: `dns_lookup`, `whois_lookup`, `port_scan`, `http_headers`

```mermaid
classDiagram
    class ToolRegistry {
        +register(name, description, parameters)
        +get(name)
        +execute(name, **kwargs)
        +list_tools()
        +get_tools_for_llm()
    }
    
    class Tool {
        +name: str
        +description: str
        +function: Callable
        +parameters: list[ToolParameter]
        +execute(**kwargs)
        +to_json_schema()
    }
    
    class ToolParameter {
        +name: str
        +type: str
        +description: str
        +required: bool
        +default: Any
    }
    
    ToolRegistry "1" *-- "0..*" Tool
    Tool "1" *-- "0..*" ToolParameter
```

## Memory Context Extraction

The memory system extracts context in several ways:

1. **Auto-extraction**: After each conversation exchange, the system automatically extracts and stores memories
2. **Manual Addition**: Users can manually add memories using the `/remember` command
3. **Memory Types**: Memories are categorized as:
   - **Episodic**: Specific past events/conversations
   - **Semantic**: User preferences and facts
   - **Procedural**: How-to knowledge and patterns

The extraction process:

1. User sends a message
2. Agent processes the message
3. After receiving the assistant's response
4. The system calls `extract_and_store()` with both user input and assistant response
5. Mem0 handles the actual extraction and storage

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant MemoryService
    participant Mem0
    
    User->>Agent: Send message
    Agent->>LLM: Process message
    LLM->>Agent: Return response
    Agent->>MemoryService: extract_and_store(user_input, assistant_response)
    MemoryService->>Mem0: add(messages, user_id, memory_type)
    Mem0-->>MemoryService: Success
```

## Context Injection to LLM

Context is injected into the LLM in a carefully controlled manner:

1. **Memory Context Retrieval**: Before sending a message to the LLM, the agent retrieves relevant memories
2. **Context Formatting**: Memories are formatted with icons and organized by type
3. **Context Injection**: The context is appended to the user's message in a special `[MEMORY CONTEXT]` section
4. **Token Management**: The system tracks token usage to avoid exceeding limits

The injection process:

1. User sends a message
2. Agent retrieves memory context using `get_memory_context()`
3. Agent creates a modified copy of the messages with memory context appended
4. Agent sends the enhanced messages to the LLM
5. LLM receives the context but it's hidden from the user in the TUI

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant MemoryService
    participant LLM
    
    User->>Agent: Send message
    Agent->>MemoryService: get_memory_context(query=user_message)
    MemoryService->>Mem0: search(query)
    Mem0-->>MemoryService: Return relevant memories
    MemoryService-->>Agent: Return formatted context
    Agent->>Agent: Append context to user message
    Agent->>LLM: Send enhanced message with context
    LLM-->>Agent: Return response
    Agent->>User: Display response (without showing context)
```

## Data Flow

```mermaid
flowchart TD
    A[User Input] --> B[Agent Loop]
    B --> C{Slash Command?}
    C -->|Yes| D[Execute Command]
    C -->|No| E[Process Chat]
    E --> F[Retrieve Memory Context]
    F --> G[Append Context to Message]
    G --> H[Send to LLM]
    H --> I{Tool Calls?}
    I -->|Yes| J[Execute Tools]
    I -->|No| K[Return Response]
    J --> K
    K --> L[Auto-extract Memories]
    L --> M[Store in Memory]
    M --> B
```

## Configuration Management

The system uses a comprehensive configuration system (`config.py`):

- **Environment Variables**: Loaded from `.env` file
- **Model Configuration**: Gemini and Ollama models
- **Memory Settings**: Mem0 API keys and local configuration
- **Theme Settings**: TUI colors and styling
- **Safety Settings**: Gemini safety thresholds

## Key Features

1. **Hybrid Brain**: Supports both cloud (Gemini) and local (Ollama) models
2. **Persistent Memory**: Long-term recall using Mem0
3. **Tool Integration**: File operations, web search, and OSINT tools
4. **Slash Commands**: Quick access to common operations
5. **Markdown Support**: Syntax-highlighted code and rich formatting
6. **Streaming**: Real-time response streaming
7. **Token Management**: Sliding window for efficient context management

## Error Handling and Logging

The system includes comprehensive error handling and logging:

- **Logging**: Structured logging with different levels
- **Error Recovery**: Graceful handling of API failures
- **Validation**: Configuration validation on startup
- **Reasoning Traces**: Detailed logs of agent reasoning process

## Future Enhancements

The architecture is designed to be extensible for future enhancements:

- Additional LLM providers
- More sophisticated memory extraction
- Enhanced tool capabilities
- Improved TUI features
- Better performance optimization

## Conclusion

Terent's architecture is a well-designed, modular system that effectively combines the power of large language models with persistent memory and a comprehensive toolset. The layered approach allows for easy maintenance, extension, and optimization while providing a rich user experience through the TUI interface.