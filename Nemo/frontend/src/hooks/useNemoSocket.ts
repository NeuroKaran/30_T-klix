import { useState, useEffect, useCallback, useRef } from 'react';

interface NemoResponse {
    text: string;
    audio: string;
    visemes: unknown[];
    error?: string;
}

interface UseNemoSocketReturn {
    isConnected: boolean;
    isConnecting: boolean;
    sendMessage: (text: string) => void;
    lastResponse: NemoResponse | null;
    error: string | null;
}

const WS_URL = 'ws://localhost:8000/talk';
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;

export function useNemoSocket(): UseNemoSocketReturn {
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(true);
    const [lastResponse, setLastResponse] = useState<NemoResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectAttemptsRef = useRef(0);
    const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Connect to WebSocket
    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return;
        }

        setIsConnecting(true);
        setError(null);

        try {
            const ws = new WebSocket(WS_URL);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('🔌 Connected to Nemo');
                setIsConnected(true);
                setIsConnecting(false);
                setError(null);
                reconnectAttemptsRef.current = 0;
            };

            ws.onclose = (event) => {
                console.log('🔌 Disconnected from Nemo', event.code);
                setIsConnected(false);
                setIsConnecting(false);

                // Attempt reconnect
                if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
                    reconnectAttemptsRef.current++;
                    console.log(`Reconnecting... (${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`);

                    reconnectTimeoutRef.current = setTimeout(() => {
                        connect();
                    }, RECONNECT_DELAY);
                } else {
                    setError('Unable to connect to Nemo. Is the server running?');
                }
            };

            ws.onerror = (event) => {
                console.error('WebSocket error:', event);
                setError('Connection error');
            };

            ws.onmessage = (event) => {
                try {
                    const data: NemoResponse = JSON.parse(event.data);
                    console.log('📥 Received:', data.text?.substring(0, 50));
                    setLastResponse(data);

                    if (data.error) {
                        setError(data.error);
                    }
                } catch (e) {
                    console.error('Failed to parse message:', e);
                }
            };

        } catch (e) {
            console.error('Failed to create WebSocket:', e);
            setIsConnecting(false);
            setError('Failed to connect');
        }
    }, []);

    // Send a message
    const sendMessage = useCallback((text: string) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            setError('Not connected to Nemo');
            return;
        }

        const message = JSON.stringify({ text });
        wsRef.current.send(message);
        console.log('📤 Sent:', text.substring(0, 50));
    }, []);

    // Connect on mount, cleanup on unmount
    useEffect(() => {
        connect();

        return () => {
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [connect]);

    return {
        isConnected,
        isConnecting,
        sendMessage,
        lastResponse,
        error,
    };
}
