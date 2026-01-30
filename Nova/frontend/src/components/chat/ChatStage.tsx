'use client';

/**
 * Nova - Chat Stage Component
 * Main chat area with messages, input, and streaming support.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Mic, Paperclip, Sparkles } from 'lucide-react';
import { MessageBubble } from './MessageBubble';
import { ThinkingIndicator } from './ThinkingIndicator';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { Message, StreamEvent } from '@/lib/types';

interface ChatStageProps {
    threadId?: string;
    userId?: string;
    initialMessages?: Message[];
}

export function ChatStage({
    threadId,
    userId,
    initialMessages = []
}: ChatStageProps) {
    const [messages, setMessages] = useState<Message[]>(initialMessages);
    const [inputValue, setInputValue] = useState('');
    const [isThinking, setIsThinking] = useState(false);
    const [thinkingMessage, setThinkingMessage] = useState('Thinking...');
    const [currentStream, setCurrentStream] = useState('');

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // WebSocket connection
    const { isConnected, send } = useWebSocket({
        onEvent: (event: StreamEvent) => handleStreamEvent(event),
        onConnect: () => console.log('Chat connected'),
    });

    // Handle streaming events
    const handleStreamEvent = useCallback((event: StreamEvent) => {
        switch (event.type) {
            case 'thinking':
                setIsThinking(true);
                setThinkingMessage(event.content || 'Thinking...');
                break;

            case 'text':
                setIsThinking(false);
                setCurrentStream(prev => prev + event.content);
                break;

            case 'tool_call':
                setThinkingMessage(`Using ${event.toolName}...`);
                break;

            case 'tool_result':
                setThinkingMessage('Processing results...');
                break;

            case 'done':
                setIsThinking(false);
                // Convert streamed content to message
                if (currentStream) {
                    setMessages(prev => [
                        ...prev,
                        {
                            id: Date.now().toString(),
                            role: 'assistant',
                            content: currentStream,
                            timestamp: new Date().toISOString(),
                        },
                    ]);
                    setCurrentStream('');
                }
                break;

            case 'error':
                setIsThinking(false);
                console.error('Stream error:', event.content);
                break;
        }
    }, [currentStream]);

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isThinking, currentStream]);

    // Handle send message
    const handleSend = useCallback(() => {
        if (!inputValue.trim()) return;

        // Add user message
        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: inputValue.trim(),
            timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, userMessage]);

        // Send via WebSocket
        send({ text: inputValue.trim(), threadId, userId });

        // Clear input
        setInputValue('');
        inputRef.current?.focus();
    }, [inputValue, send, threadId, userId]);

    // Handle keyboard shortcuts
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex flex-col h-full">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {/* Welcome Message */}
                {messages.length === 0 && !isThinking && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex flex-col items-center justify-center h-full text-center"
                    >
                        <div className="w-20 h-20 mb-6 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center glow-accent">
                            <Sparkles className="w-10 h-10 text-white" />
                        </div>
                        <h2 className="text-2xl font-semibold text-gradient mb-2">
                            Hello! I'm Nova
                        </h2>
                        <p className="text-gray-400 max-w-md">
                            Your AI assistant with persistent memory. I remember our conversations
                            and learn your preferences over time.
                        </p>
                    </motion.div>
                )}

                {/* Message List */}
                <AnimatePresence mode="popLayout">
                    {messages.map((message, index) => (
                        <MessageBubble
                            key={message.id}
                            message={message}
                            isLatest={index === messages.length - 1}
                        />
                    ))}
                </AnimatePresence>

                {/* Streaming Content */}
                {currentStream && (
                    <MessageBubble
                        message={{
                            id: 'streaming',
                            role: 'assistant',
                            content: currentStream,
                            timestamp: new Date().toISOString(),
                        }}
                        isLatest
                    />
                )}

                {/* Thinking Indicator */}
                <AnimatePresence>
                    {isThinking && <ThinkingIndicator message={thinkingMessage} />}
                </AnimatePresence>

                {/* Scroll anchor */}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-white/5">
                <div className="glass-panel p-2 flex items-end gap-2">
                    {/* Attachment Button */}
                    <button
                        className="p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-white/5"
                        title="Attach file"
                    >
                        <Paperclip className="w-5 h-5" />
                    </button>

                    {/* Text Input */}
                    <textarea
                        ref={inputRef}
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask me anything..."
                        rows={1}
                        className="flex-1 bg-transparent border-none outline-none resize-none text-white placeholder-gray-500 py-2 px-2 max-h-32"
                        style={{ minHeight: '40px' }}
                    />

                    {/* Voice Button */}
                    <button
                        className="p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-white/5"
                        title="Voice input"
                    >
                        <Mic className="w-5 h-5" />
                    </button>

                    {/* Send Button */}
                    <button
                        onClick={handleSend}
                        disabled={!inputValue.trim() || !isConnected}
                        className={`p-2 rounded-lg transition-all ${inputValue.trim() && isConnected
                                ? 'bg-gradient-to-r from-violet-500 to-indigo-600 text-white hover:opacity-90'
                                : 'text-gray-500 cursor-not-allowed'
                            }`}
                        title="Send message"
                    >
                        <Send className="w-5 h-5" />
                    </button>
                </div>

                {/* Connection Status */}
                <div className="flex justify-center mt-2">
                    <span className={`text-xs flex items-center gap-1 ${isConnected ? 'text-green-400' : 'text-yellow-400'}`}>
                        <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-yellow-400 animate-pulse'}`} />
                        {isConnected ? 'Connected' : 'Connecting...'}
                    </span>
                </div>
            </div>
        </div>
    );
}

export default ChatStage;
