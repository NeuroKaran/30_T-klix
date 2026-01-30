// Nova Frontend Types

// =============================================================================
// Message Types
// =============================================================================

export type MessageRole = 'user' | 'assistant' | 'system' | 'tool';

export interface Message {
    id: string;
    role: MessageRole;
    content: string;
    timestamp: string;
    toolCalls?: ToolCall[];
    toolCallId?: string;
    toolName?: string;
}

export interface ToolCall {
    id: string;
    name: string;
    arguments: Record<string, unknown>;
}

// =============================================================================
// Thread Types
// =============================================================================

export interface Thread {
    id: string;
    title: string;
    createdAt: string;
    updatedAt: string;
    messageCount: number;
    memoryCount: number;
    userId?: string;
}

export interface ThreadCreate {
    title?: string;
    userId?: string;
}

// =============================================================================
// Memory Types
// =============================================================================

export type MemoryType = 'episodic' | 'semantic' | 'procedural';

export interface Memory {
    id: string;
    content: string;
    memoryType: MemoryType;
    createdAt?: string;
    metadata?: Record<string, unknown>;
}

// =============================================================================
// Chat Types
// =============================================================================

export interface ChatRequest {
    text: string;
    threadId?: string;
    userId?: string;
    stream?: boolean;
}

export interface ChatResponse {
    text: string;
    threadId: string;
    messageId: string;
    toolCalls?: ToolCall[];
    timestamp: string;
}

// =============================================================================
// Streaming Types
// =============================================================================

export type StreamEventType =
    | 'text'
    | 'tool_call'
    | 'tool_result'
    | 'thinking'
    | 'done'
    | 'error';

export interface StreamEvent {
    type: StreamEventType;
    content: string;
    toolName?: string;
    toolArgs?: Record<string, unknown>;
    timestamp: string;
}

// =============================================================================
// Status Types
// =============================================================================

export interface ServiceStatus {
    name: string;
    enabled: boolean;
    details: string;
}

export interface StatusResponse {
    status: string;
    version: string;
    model: string;
    provider: string;
    services: ServiceStatus[];
    uptimeSeconds: number;
}

// =============================================================================
// UI State Types
// =============================================================================

export interface ChatState {
    messages: Message[];
    isStreaming: boolean;
    isThinking: boolean;
    currentStreamContent: string;
    error?: string;
}

export interface AppState {
    threads: Thread[];
    activeThreadId: string | null;
    memories: Memory[];
    status: StatusResponse | null;
    sidebarOpen: boolean;
    artifactPanelOpen: boolean;
}
