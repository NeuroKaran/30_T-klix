import { motion } from 'framer-motion';

interface Message {
    id: string;
    role: 'user' | 'nemo';
    content: string;
    timestamp: Date;
}

interface MessageBubbleProps {
    message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
    const isUser = message.role === 'user';

    return (
        <motion.div
            className={`message ${isUser ? 'message-user' : 'message-nemo'}`}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{
                duration: 0.3,
                ease: [0.4, 0, 0.2, 1]
            }}
        >
            <p className="message-text">{message.content}</p>
            <span
                style={{
                    fontSize: '0.7rem',
                    opacity: 0.5,
                    marginTop: '0.5rem',
                    display: 'block'
                }}
            >
                {message.timestamp.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit'
                })}
            </span>
        </motion.div>
    );
}

export function TypingIndicator() {
    return (
        <motion.div
            className="message message-nemo"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
        >
            <div className="typing-indicator">
                <div className="typing-dot" />
                <div className="typing-dot" />
                <div className="typing-dot" />
            </div>
        </motion.div>
    );
}
