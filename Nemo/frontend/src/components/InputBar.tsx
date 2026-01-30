import { useState, useEffect, KeyboardEvent } from 'react';
import { motion } from 'framer-motion';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';

interface InputBarProps {
    onSend: (message: string) => void;
    disabled?: boolean;
    isConnected: boolean;
}

export function InputBar({ onSend, disabled = false, isConnected }: InputBarProps) {
    const [input, setInput] = useState('');

    const {
        isListening,
        isSupported,
        transcript,
        startListening,
        stopListening
    } = useSpeechRecognition();

    // Update input when speech recognition provides transcript
    useEffect(() => {
        if (transcript) {
            setInput(transcript);
        }
    }, [transcript]);

    // Auto-send when speech recognition ends with a transcript
    useEffect(() => {
        if (!isListening && transcript && transcript.trim()) {
            // Small delay to show the transcribed text before sending
            const timer = setTimeout(() => {
                handleSend();
            }, 300);
            return () => clearTimeout(timer);
        }
    }, [isListening, transcript]);

    const handleSend = () => {
        const trimmed = input.trim();
        if (trimmed && !disabled) {
            onSend(trimmed);
            setInput('');
        }
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleMicClick = () => {
        if (isListening) {
            stopListening();
        } else {
            startListening();
        }
    };

    return (
        <motion.div
            className="input-bar glass-panel"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            style={{ padding: '0.75rem' }}
        >
            {/* Connection status */}
            <div
                className={`status-dot ${isConnected ? 'status-connected' : 'status-disconnected'
                    }`}
                title={isConnected ? 'Connected' : 'Disconnected'}
                style={{ marginLeft: '0.5rem' }}
            />

            {/* Microphone button */}
            {isSupported && (
                <motion.button
                    className={`btn btn-icon ${isListening ? 'btn-primary' : 'btn-ghost'}`}
                    onClick={handleMicClick}
                    disabled={disabled || !isConnected}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    title={isListening ? 'Stop listening' : 'Start voice input'}
                    style={{
                        marginLeft: '0.5rem',
                        position: 'relative',
                    }}
                >
                    {/* Microphone icon */}
                    <svg
                        width="20"
                        height="20"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                        <line x1="12" y1="19" x2="12" y2="23" />
                        <line x1="8" y1="23" x2="16" y2="23" />
                    </svg>

                    {/* Listening indicator pulse */}
                    {isListening && (
                        <motion.div
                            style={{
                                position: 'absolute',
                                inset: -4,
                                borderRadius: '50%',
                                border: '2px solid var(--accent-primary)',
                            }}
                            animate={{
                                scale: [1, 1.3, 1],
                                opacity: [0.8, 0, 0.8],
                            }}
                            transition={{
                                duration: 1.5,
                                repeat: Infinity,
                                ease: 'easeInOut',
                            }}
                        />
                    )}
                </motion.button>
            )}

            {/* Text input */}
            <input
                type="text"
                className="input-field"
                placeholder={
                    isListening
                        ? "Listening..."
                        : isConnected
                            ? "Say something to Nemo..."
                            : "Connecting..."
                }
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={disabled || !isConnected || isListening}
                style={{
                    flexGrow: 1,
                    marginLeft: '0.5rem',
                }}
            />

            {/* Send button */}
            <motion.button
                className="btn btn-primary btn-icon"
                onClick={handleSend}
                disabled={disabled || !input.trim() || !isConnected || isListening}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                style={{
                    opacity: (disabled || !input.trim() || !isConnected || isListening) ? 0.5 : 1,
                    cursor: (disabled || !input.trim() || !isConnected || isListening) ? 'not-allowed' : 'pointer'
                }}
            >
                <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                >
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
            </motion.button>
        </motion.div>
    );
}
