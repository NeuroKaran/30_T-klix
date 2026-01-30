'use client';

/**
 * Nova - Sidebar Component
 * Thread list and memory indicators.
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    MessageSquare,
    Plus,
    ChevronLeft,
    ChevronRight,
    Search,
    Brain,
    Trash2,
    Settings,
} from 'lucide-react';
import type { Thread } from '@/lib/types';

interface SidebarProps {
    threads: Thread[];
    activeThreadId: string | null;
    onSelectThread: (threadId: string) => void;
    onNewThread: () => void;
    onDeleteThread: (threadId: string) => void;
    isOpen: boolean;
    onToggle: () => void;
}

export function Sidebar({
    threads,
    activeThreadId,
    onSelectThread,
    onNewThread,
    onDeleteThread,
    isOpen,
    onToggle,
}: SidebarProps) {
    const [searchQuery, setSearchQuery] = useState('');

    // Filter threads by search
    const filteredThreads = threads.filter((thread) =>
        thread.title.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // Format date
    const formatDate = (dateStr: string) => {
        try {
            const date = new Date(dateStr);
            const now = new Date();
            const diffDays = Math.floor(
                (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
            );

            if (diffDays === 0) return 'Today';
            if (diffDays === 1) return 'Yesterday';
            if (diffDays < 7) return `${diffDays} days ago`;
            return date.toLocaleDateString();
        } catch {
            return '';
        }
    };

    return (
        <>
            {/* Sidebar Panel */}
            <AnimatePresence>
                {isOpen && (
                    <motion.aside
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 280, opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="h-full glass-panel flex flex-col overflow-hidden"
                    >
                        {/* Header */}
                        <div className="p-4 border-b border-white/5">
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-lg font-semibold text-gradient">Nova</h2>
                                <button
                                    onClick={onToggle}
                                    className="p-1.5 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors"
                                >
                                    <ChevronLeft className="w-5 h-5" />
                                </button>
                            </div>

                            {/* New Thread Button */}
                            <button
                                onClick={onNewThread}
                                className="w-full flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-violet-500/20 to-indigo-500/20 border border-violet-500/30 text-white hover:border-violet-500/50 transition-all"
                            >
                                <Plus className="w-4 h-4" />
                                <span>New Conversation</span>
                            </button>
                        </div>

                        {/* Search */}
                        <div className="p-3 border-b border-white/5">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                                <input
                                    type="text"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    placeholder="Search threads..."
                                    className="w-full pl-9 pr-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-500 outline-none focus:border-violet-500/50 transition-colors"
                                />
                            </div>
                        </div>

                        {/* Thread List */}
                        <div className="flex-1 overflow-y-auto p-2">
                            {filteredThreads.length === 0 ? (
                                <div className="text-center text-gray-500 py-8">
                                    <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                    <p className="text-sm">No conversations yet</p>
                                </div>
                            ) : (
                                <div className="space-y-1">
                                    {filteredThreads.map((thread) => (
                                        <motion.button
                                            key={thread.id}
                                            onClick={() => onSelectThread(thread.id)}
                                            className={`w-full group flex items-start gap-3 p-3 rounded-lg text-left transition-all ${activeThreadId === thread.id
                                                    ? 'bg-violet-500/20 border border-violet-500/30'
                                                    : 'hover:bg-white/5 border border-transparent'
                                                }`}
                                            whileHover={{ x: 2 }}
                                        >
                                            <MessageSquare
                                                className={`w-4 h-4 mt-0.5 flex-shrink-0 ${activeThreadId === thread.id
                                                        ? 'text-violet-400'
                                                        : 'text-gray-500'
                                                    }`}
                                            />
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium text-white truncate">
                                                    {thread.title}
                                                </p>
                                                <div className="flex items-center gap-2 mt-1">
                                                    <span className="text-xs text-gray-500">
                                                        {formatDate(thread.updatedAt)}
                                                    </span>
                                                    {thread.memoryCount > 0 && (
                                                        <span className="flex items-center gap-1 text-xs text-violet-400">
                                                            <Brain className="w-3 h-3" />
                                                            {thread.memoryCount}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    onDeleteThread(thread.id);
                                                }}
                                                className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 text-gray-500 hover:text-red-400 transition-all"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </motion.button>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Footer */}
                        <div className="p-3 border-t border-white/5">
                            <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors">
                                <Settings className="w-4 h-4" />
                                <span className="text-sm">Settings</span>
                            </button>
                        </div>
                    </motion.aside>
                )}
            </AnimatePresence>

            {/* Collapsed Toggle Button */}
            {!isOpen && (
                <motion.button
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    onClick={onToggle}
                    className="fixed left-4 top-4 z-20 p-2 glass-card hover:bg-white/10 transition-colors"
                >
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                </motion.button>
            )}
        </>
    );
}

export default Sidebar;
