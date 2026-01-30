'use client';

/**
 * Nova - Main Page
 * The primary chat interface with sidebar and artifact panel.
 */

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ChatStage } from '@/components/chat/ChatStage';
import { Sidebar } from '@/components/sidebar/Sidebar';
import { api } from '@/lib/api';
import type { Thread, StatusResponse } from '@/lib/types';

export default function HomePage() {
  // State
  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      try {
        // Load status
        const statusData = await api.getStatus();
        setStatus(statusData);

        // Load threads
        const { threads: threadData } = await api.getThreads();
        setThreads(threadData);
      } catch (error) {
        console.error('Failed to load initial data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  // Handle thread selection
  const handleSelectThread = (threadId: string) => {
    setActiveThreadId(threadId);
  };

  // Handle new thread
  const handleNewThread = async () => {
    try {
      const newThread = await api.createThread({ title: 'New Conversation' });
      setThreads((prev) => [newThread, ...prev]);
      setActiveThreadId(newThread.id);
    } catch (error) {
      console.error('Failed to create thread:', error);
    }
  };

  // Handle delete thread
  const handleDeleteThread = async (threadId: string) => {
    try {
      await api.deleteThread(threadId);
      setThreads((prev) => prev.filter((t) => t.id !== threadId));
      if (activeThreadId === threadId) {
        setActiveThreadId(null);
      }
    } catch (error) {
      console.error('Failed to delete thread:', error);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <div className="w-16 h-16 mb-4 mx-auto rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center animate-pulse">
            <span className="text-2xl">✨</span>
          </div>
          <p className="text-gray-400">Loading Nova...</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={handleSelectThread}
        onNewThread={handleNewThread}
        onDeleteThread={handleDeleteThread}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header Bar */}
        <header className="h-14 px-4 flex items-center justify-between border-b border-white/5 bg-black/20 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-2 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            )}
            <div>
              <h1 className="text-lg font-semibold text-white">
                {activeThreadId
                  ? threads.find((t) => t.id === activeThreadId)?.title || 'Chat'
                  : 'Nova'}
              </h1>
              {status && (
                <p className="text-xs text-gray-500">
                  {status.provider}: {status.model}
                </p>
              )}
            </div>
          </div>

          {/* Status Indicators */}
          <div className="flex items-center gap-4">
            {status?.services.map((service) => (
              <span
                key={service.name}
                className={`flex items-center gap-1.5 text-xs ${service.enabled ? 'text-green-400' : 'text-gray-500'
                  }`}
              >
                <span
                  className={`w-2 h-2 rounded-full ${service.enabled ? 'bg-green-400' : 'bg-gray-500'
                    }`}
                />
                {service.name}
              </span>
            ))}
          </div>
        </header>

        {/* Chat Area */}
        <div className="flex-1 overflow-hidden">
          <ChatStage threadId={activeThreadId || undefined} />
        </div>
      </div>

      {/* Artifact Panel Placeholder */}
      {/* TODO: Implement CodePanel for artifacts */}
    </div>
  );
}
