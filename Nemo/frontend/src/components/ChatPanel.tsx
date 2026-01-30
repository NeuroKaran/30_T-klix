import { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageBubble, TypingIndicator } from './MessageBubble';
import { InputBar } from './InputBar';

export interface Message {
    id: string;
    role: 'user' | 'nemo';
    content: string;
    timestamp: Date;
}

interface ChatPanelProps {
    messages: Message[];
    onSend: (message: string) => void;
    isConnected: boolean;
    isTyping: boolean;
    disabled?: boolean;
}

export function ChatPanel({
    messages,
    onSend,
    isConnected,
    isTyping,
    disabled = false
}: ChatPanelProps) {
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isTyping]);

    return (
        <div className="chat-container">
            {/* Messages list */}
            <motion.div
                className="message-list glass-panel"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
            >
                {/* Welcome message if empty */}
                {messages.length === 0 && !isTyping && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.5 }}
                        style={{
                            textAlign: 'center',
                            padding: '2rem',
                            color: 'var(--text-muted)'
                        }}
                    >
                        <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>🌊</div>
                        <p>Hey there! I'm <strong style={{ color: 'var(--accent-primary)' }}>Nemo</strong>.</p>
                        <p style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>
                            Your sassy AI friend. What's on your mind?
                        </p>
                    </motion.div>
                )}

                {/* Message bubbles */}
                <AnimatePresence mode="popLayout">
                    {messages.map((message) => (
                        <MessageBubble key={message.id} message={message} />
                    ))}
                </AnimatePresence>

                {/* Typing indicator */}
                <AnimatePresence>
                    {isTyping && <TypingIndicator />}
                </AnimatePresence>

                {/* Scroll anchor */}
                <div ref={messagesEndRef} />
            </motion.div>

            {/* Input bar */}
            <InputBar
                onSend={onSend}
                disabled={disabled || isTyping}
                isConnected={isConnected}
            />
        </div>
    );
}
