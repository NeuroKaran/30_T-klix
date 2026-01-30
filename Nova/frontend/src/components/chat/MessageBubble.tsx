'use client';

/**
 * Nova - Message Bubble Component
 * Renders user and assistant messages with glass styling.
 */

import { motion } from 'framer-motion';
import { Bot, User, Wrench } from 'lucide-react';
import type { Message, ToolCall } from '@/lib/types';

interface MessageBubbleProps {
    message: Message;
    isLatest?: boolean;
}

export function MessageBubble({ message, isLatest = false }: MessageBubbleProps) {
    const isUser = message.role === 'user';
    const isAssistant = message.role === 'assistant';
    const isTool = message.role === 'tool';

    // Format timestamp
    const formatTime = (timestamp: string) => {
        try {
            return new Date(timestamp).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch {
            return '';
        }
    };

    // Render tool call indicator
    const renderToolCalls = (toolCalls: ToolCall[]) => (
        <div className="mt-3 space-y-2">
            {toolCalls.map((tc, idx) => (
                <div
                    key={tc.id || idx}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-black/20 text-sm"
                >
                    <Wrench className="w-4 h-4 text-yellow-400" />
                    <span className="text-yellow-400 font-mono">{tc.name}</span>
                </div>
            ))}
        </div>
    );

    // Render code blocks with syntax highlighting
    const renderContent = (content: string) => {
        // Simple code block detection
        const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
        const parts: React.ReactNode[] = [];
        let lastIndex = 0;
        let match;

        while ((match = codeBlockRegex.exec(content)) !== null) {
            // Add text before code block
            if (match.index > lastIndex) {
                parts.push(
                    <span key={`text-${lastIndex}`}>
                        {content.slice(lastIndex, match.index)}
                    </span>
                );
            }

            // Add code block
            const language = match[1] || 'text';
            const code = match[2];
            parts.push(
                <div key={`code-${match.index}`} className="my-3 code-block">
                    <div className="flex items-center justify-between px-4 py-2 border-b border-white/10 text-xs text-gray-400">
                        <span>{language}</span>
                        <button
                            onClick={() => navigator.clipboard.writeText(code)}
                            className="hover:text-white transition-colors"
                        >
                            Copy
                        </button>
                    </div>
                    <pre className="overflow-x-auto">
                        <code>{code}</code>
                    </pre>
                </div>
            );

            lastIndex = match.index + match[0].length;
        }

        // Add remaining text
        if (lastIndex < content.length) {
            parts.push(
                <span key={`text-${lastIndex}`}>
                    {content.slice(lastIndex)}
                </span>
            );
        }

        return parts.length > 0 ? parts : content;
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'} ${isLatest ? 'mb-4' : 'mb-3'
                }`}
        >
            {/* Avatar */}
            <div
                className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${isUser
                        ? 'bg-gradient-to-br from-violet-500 to-indigo-600'
                        : isTool
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : 'bg-gradient-to-br from-indigo-500 to-purple-600'
                    }`}
            >
                {isUser ? (
                    <User className="w-4 h-4 text-white" />
                ) : isTool ? (
                    <Wrench className="w-4 h-4" />
                ) : (
                    <Bot className="w-4 h-4 text-white" />
                )}
            </div>

            {/* Message Bubble */}
            <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[80%]`}>
                <div
                    className={
                        isUser
                            ? 'bubble-user'
                            : isTool
                                ? 'bg-yellow-500/10 border border-yellow-500/20 rounded-xl px-4 py-3 text-sm font-mono'
                                : 'bubble-assistant'
                    }
                >
                    {/* Content */}
                    <div className="whitespace-pre-wrap break-words leading-relaxed">
                        {renderContent(message.content)}
                    </div>

                    {/* Tool Calls */}
                    {message.toolCalls && message.toolCalls.length > 0 && renderToolCalls(message.toolCalls)}
                </div>

                {/* Timestamp */}
                <span className="text-xs text-gray-500 mt-1 px-2">
                    {formatTime(message.timestamp)}
                </span>
            </div>
        </motion.div>
    );
}

export default MessageBubble;
