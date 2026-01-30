/**
 * Nova - API Client
 * Handles all communication with the Nova backend.
 */

import type {
    ChatRequest,
    ChatResponse,
    Memory,
    MemoryType,
    StatusResponse,
    StreamEvent,
    Thread,
    ThreadCreate,
} from './types';

// =============================================================================
// Configuration
// =============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';

// =============================================================================
// API Client Class
// =============================================================================

class ApiClient {
    private baseUrl: string;
    private wsUrl: string;

    constructor(baseUrl: string = API_BASE_URL, wsUrl: string = WS_URL) {
        this.baseUrl = baseUrl;
        this.wsUrl = wsUrl;
    }

    // ===========================================================================
    // Helper Methods
    // ===========================================================================

    private async fetch<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`;

        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }

    // ===========================================================================
    // Status
    // ===========================================================================

    async getStatus(): Promise<StatusResponse> {
        return this.fetch<StatusResponse>('/api/status');
    }

    // ===========================================================================
    // Chat
    // ===========================================================================

    async sendMessage(request: ChatRequest): Promise<ChatResponse> {
        return this.fetch<ChatResponse>('/api/chat', {
            method: 'POST',
            body: JSON.stringify(request),
        });
    }

    /**
     * Create a WebSocket connection for streaming messages.
     * Returns an object with methods to send messages and close the connection.
     */
    createStreamConnection(
        onEvent: (event: StreamEvent) => void,
        onError?: (error: Error) => void,
        onClose?: () => void
    ): {
        send: (text: string, threadId?: string, userId?: string) => void;
        close: () => void;
        isConnected: () => boolean;
    } {
        let ws: WebSocket | null = null;
        let connected = false;

        const connect = () => {
            ws = new WebSocket(this.wsUrl);

            ws.onopen = () => {
                connected = true;
                console.log('WebSocket connected');
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data) as StreamEvent;
                    onEvent(data);
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                onError?.(new Error('WebSocket connection error'));
            };

            ws.onclose = () => {
                connected = false;
                console.log('WebSocket disconnected');
                onClose?.();
            };
        };

        connect();

        return {
            send: (text: string, threadId?: string, userId?: string) => {
                if (ws && connected) {
                    ws.send(JSON.stringify({ text, thread_id: threadId, user_id: userId }));
                } else {
                    console.error('WebSocket not connected');
                }
            },
            close: () => {
                ws?.close();
            },
            isConnected: () => connected,
        };
    }

    // ===========================================================================
    // Threads
    // ===========================================================================

    async getThreads(userId?: string, limit = 20): Promise<{ threads: Thread[]; total: number }> {
        const params = new URLSearchParams();
        if (userId) params.set('user_id', userId);
        params.set('limit', limit.toString());

        return this.fetch(`/api/threads?${params.toString()}`);
    }

    async getThread(threadId: string): Promise<{ thread: Thread; messages: unknown[] }> {
        return this.fetch(`/api/threads/${threadId}`);
    }

    async createThread(request: ThreadCreate): Promise<Thread> {
        return this.fetch<Thread>('/api/threads', {
            method: 'POST',
            body: JSON.stringify(request),
        });
    }

    async deleteThread(threadId: string): Promise<void> {
        await this.fetch(`/api/threads/${threadId}`, {
            method: 'DELETE',
        });
    }

    // ===========================================================================
    // Memories
    // ===========================================================================

    async getMemories(userId?: string, limit = 20): Promise<{ memories: Memory[]; total: number }> {
        const params = new URLSearchParams();
        if (userId) params.set('user_id', userId);
        params.set('limit', limit.toString());

        return this.fetch(`/api/memories?${params.toString()}`);
    }

    async searchMemories(
        query: string,
        userId?: string,
        limit = 10
    ): Promise<{ memories: Memory[]; total: number }> {
        return this.fetch('/api/memories/search', {
            method: 'POST',
            body: JSON.stringify({ query, user_id: userId, limit }),
        });
    }

    async saveMemory(
        text: string,
        memoryType: MemoryType = 'semantic',
        userId?: string
    ): Promise<void> {
        await this.fetch('/api/memories', {
            method: 'POST',
            body: JSON.stringify({ text, memory_type: memoryType, user_id: userId }),
        });
    }

    async deleteMemory(memoryId: string): Promise<void> {
        await this.fetch(`/api/memories/${memoryId}`, {
            method: 'DELETE',
        });
    }
}

// =============================================================================
// Singleton Instance
// =============================================================================

export const api = new ApiClient();

export default api;
