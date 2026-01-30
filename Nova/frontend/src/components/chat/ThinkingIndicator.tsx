'use client';

/**
 * Nova - Thinking Indicator Component
 * Animated dots showing the AI is processing.
 */

import { motion } from 'framer-motion';
import { Bot, Sparkles } from 'lucide-react';

interface ThinkingIndicatorProps {
    message?: string;
}

export function ThinkingIndicator({ message = 'Thinking...' }: ThinkingIndicatorProps) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex gap-3"
        >
            {/* Avatar */}
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center pulse-glow">
                <Bot className="w-4 h-4 text-white" />
            </div>

            {/* Thinking Bubble */}
            <div className="glass-card px-4 py-3 flex items-center gap-3">
                <Sparkles className="w-4 h-4 text-violet-400 animate-pulse" />

                {/* Animated Dots */}
                <div className="thinking-dots">
                    <span />
                    <span />
                    <span />
                </div>

                <span className="text-sm text-gray-400">{message}</span>
            </div>
        </motion.div>
    );
}

export default ThinkingIndicator;
