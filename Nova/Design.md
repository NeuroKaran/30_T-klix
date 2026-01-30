# Nova: Design & Architecture Document

## 1. Vision & Problem Statement: The Memory Continuity Problem

### The Problem
Current AI assistants suffer from "Ambasador's Amnesia" — every conversation feels like the first. While they may have vast general knowledge, they lack the **personal continuity** that defines human relationships. They do not remember your preferences, past projects, or subtle context changes over time. This fragmentation breaks the illusion of intelligence and limits long-term utility.

### The Solution: Nova
Nova is designed to solve the **AI Human Memory Continuity Problem**. It is not just a chatbot; it is a long-horizon agentic assistant that possesses:
- **Episodic Memory**: Remembering specific past events and conversations.
- **Semantic Memory**: Understanding facts and preferences about the user.
- **Procedural Memory**: Learning how to perform tasks better over time.

This ensures that Nova evolves *with* the user, creating a seamless, continuous interaction loop that feels less like software and more like a partner.

---

## 2. Functional Architecture (Klix Backend Integration)

Nova leverages the existing **Klix** backend infrastructure while providing a modern web interface:

### Layer 1: The Interface (Perception)
*   **Role**: Accepts multimodal input (Text, Voice, Images, Code) and renders dynamic, aesthetic responses.
*   **Tech**: Next.js 14 (React), TailwindCSS, Framer Motion.
*   **Key Concept**: "Liquid Glass" design. Glassmorphism, fluid animations, and real-time "Thinking" visualizations build trust.

### Layer 2: The Orchestrator (Cognition)
*   **Role**: The central brain that routes requests, manages state, and decides *how* to answer.
*   **Tech**: Python (FastAPI) wrapping existing Klix components.
*   **Key Concept**: Asynchronous command loop with WebSocket streaming.

### Layer 3: The Memory Cortex (Context)
*   **Role**: The differentiator. Before every LLM call, this layer runs a retrieval process to inject relevant context.
*   **Tech**: **Mem0** (The Memory Layer) - integrated via Klix's `MemoryService`.
*   **Data Flow**: `User Input` -> `Memory Search` -> `Context Injection` -> `LLM`.

### Layer 4: The Engine (Intelligence)
*   **Role**: The raw processing power.
*   **Tech**: 
    -   **Primary**: Google Gemini for advanced reasoning.
    -   **Local**: Ollama (LLaMA 3, Mistral) for privacy and speed.
    -   **Tools**: Klix's `ToolRegistry` for file ops, web search, shell commands.

---

## 3. Technology Stack & Tools

### Frontend (The Face)
-   **Framework**: **Next.js 14+** (App Router) for server-side rendering.
-   **Styling**: **TailwindCSS** for utility-first styling.
-   **Animations**: **Framer Motion** for complex layout transitions.
-   **Icons**: **Lucide React** for consistent iconography.
-   **Syntax Highlighting**: **Prism React Renderer** for code artifacts.

### Backend (The Brain)
-   **Language**: **Python 3.10+**.
-   **API Framework**: **FastAPI** with WebSocket support.
-   **Database**: **SQLite** with SQLAlchemy (async) for thread/message storage.
-   **Existing Components**: Klix's `LLMClient`, `MemoryService`, `ToolRegistry`.

### AI & Memory Infrastructure
-   **Memory Layer**: **Mem0** (via Klix's `MemoryService`).
-   **LLM Providers**: Gemini (primary), Ollama (local).
-   **Agent Framework**: Klix's `AgentLoop` adapted for web.

---

## 4. Frontend Design & Layouts

### Design Philosophy: "Liquid Glass"
The interface should feel organic. No hard cuts. Everything floats in a hierarchical glass stack.

### Key Layouts
1.  **The Immersion Container**:
    -   Full viewport height.
    -   Background: Animated dark gradients (Indigo/Violet).
    -   Content sits on `backdrop-filter: blur(20px)` panels.

2.  **The Sidebar (Memory Lane)**:
    -   Collapsible.
    -   Lists "Threads" not just chats.
    -   Visual indicators for threads with "High Memory Value".

3.  **The Chat Stage**:
    -   Central focus.
    -   **User Bubble**: Minimal, aligned right, gradient accent.
    -   **Nova Bubble**: Rich content, aligned left, glass styling.

4.  **The Artifact Panel**:
    -   Slide-in side panel for code viewing.
    -   Syntax highlighting with dark theme.
    -   Copy button and language indicator.

### CSS & Visual Concepts
-   **Glassmorphism**: `bg-white/5 border border-white/10 backdrop-blur-xl`.
-   **Glow Effects**: Radial gradients behind active elements.
-   **Typography**: `Geist Sans` for UI; `Geist Mono` for code.
-   **Accent Colors**: Violet (#8b5cf6) to Indigo (#6366f1) gradients.

---

## 5. Connectivity & Integration

### Frontend <-> Backend Bridge
-   **Protocol**: REST API for CRUD ops, **WebSockets** for real-time streaming.
-   **State Sync**: Frontend state persisted to SQLite via API.
-   **Thread Management**: Threads and messages stored in database.

### Klix Backend Integration
-   **LLMClient**: Reused directly for Gemini/Ollama communication.
-   **MemoryService**: Reused for Mem0 memory operations.
-   **ToolRegistry**: Reused for file, shell, and web search tools.
-   **Config**: Reused for model/provider configuration.

### WebSocket Streaming
-   **Events**: `thinking`, `text`, `tool_call`, `tool_result`, `done`, `error`.
-   **Format**: JSON objects with type, content, and metadata.

---

## 6. Functional Architecture: The "Thinking" Process

To solve the continuity problem, the system must "Think" before it speaks.

1.  **Input**: User says "Update the project plan."
2.  **Recall (Mem0)**: System retrieves *which* project plan (from Semantic Memory).
3.  **Plan (Agent)**: System creates a hidden chain-of-thought:
    *   *Check*: Do I have the file?
    *   *Action*: Read file.
    *   *Action*: Update file.
4.  **Execute**: Tools are called (File I/O).
5.  **Output**: Response generated using the *new* context.
6.  **Memorize (Mem0)**: System records "User updated Project X plan on [Date]".

## 7. Memory Continuity Problem Statement

**"The Continuity Gap"**
Humans rely on shared history to build trust and efficiency. Standard LLMs reset this history every session (or rely on limited context windows). 

**Nova's Objective**: To bridge the Continuity Gap by creating a **Persistent User State** that survives unrelated sessions. If you tell Nova you dislike Python on Monday, it should not suggest Python code on Friday, even in a completely different conversation thread. This requires **Active Memory Management**, not just passive logging.
