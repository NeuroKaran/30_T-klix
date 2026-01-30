'use client';

/**
 * Nova - WebSocket Hook
 * Custom hook for managing WebSocket connections with auto-reconnect.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { StreamEvent } from '@/lib/types';

interface UseWebSocketOptions {
    url?: string;
    onEvent?: (event: StreamEvent) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
    onError?: (error: Event) => void;
    autoConnect?: boolean;
    reconnectInterval?: number;
    maxReconnectAttempts?: number;
}

interface UseWebSocketReturn {
    isConnected: boolean;
    isConnecting: boolean;
    send: (message: { text: string; threadId?: string; userId?: string }) => void;
    connect: () => void;
    disconnect: () => void;
    lastEvent: StreamEvent | null;
}

const DEFAULT_WS_URL = 'ws://localhost:8000/ws';

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
    const {
        url = DEFAULT_WS_URL,
        onEvent,
        onConnect,
        onDisconnect,
        onError,
        autoConnect = true,
        reconnectInterval = 3000,
        maxReconnectAttempts = 5,
    } = options;

    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);
    const [lastEvent, setLastEvent] = useState<StreamEvent | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectAttemptsRef = useRef(0);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return;
        }

        setIsConnecting(true);

        try {
            const ws = new WebSocket(url);

            ws.onopen = () => {
                setIsConnected(true);
                setIsConnecting(false);
                reconnectAttemptsRef.current = 0;
                console.log('🔌 WebSocket connected');
                onConnect?.();
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data) as StreamEvent;
                    setLastEvent(data);
                    onEvent?.(data);
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                onError?.(error);
            };

            ws.onclose = () => {
                setIsConnected(false);
                setIsConnecting(false);
                console.log('🔌 WebSocket disconnected');
                onDisconnect?.();

                // Attempt to reconnect
                if (reconnectAttemptsRef.current < maxReconnectAttempts) {
                    reconnectAttemptsRef.current += 1;
                    console.log(
                        `Reconnecting in ${reconnectInterval}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`
                    );
                    reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval);
                }
            };

            wsRef.current = ws;
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            setIsConnecting(false);
        }
    }, [url, onEvent, onConnect, onDisconnect, onError, reconnectInterval, maxReconnectAttempts]);

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
        reconnectAttemptsRef.current = maxReconnectAttempts; // Prevent reconnection
        wsRef.current?.close();
        wsRef.current = null;
    }, [maxReconnectAttempts]);

    const send = useCallback(
        (message: { text: string; threadId?: string; userId?: string }) => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(
                    JSON.stringify({
                        text: message.text,
                        thread_id: message.threadId,
                        user_id: message.userId,
                    })
                );
            } else {
                console.error('WebSocket is not connected');
            }
        },
        []
    );

    // Auto-connect on mount
    useEffect(() => {
        if (autoConnect) {
            connect();
        }

        return () => {
            disconnect();
        };
    }, [autoConnect, connect, disconnect]);

    return {
        isConnected,
        isConnecting,
        send,
        connect,
        disconnect,
        lastEvent,
    };
}

export default useWebSocket;
