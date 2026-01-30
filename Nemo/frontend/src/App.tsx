import { useState, useEffect, useCallback, useRef } from 'react';
import './index.css';
import { NemoScene } from './components/NemoScene';
import { ChatPanel, type Message } from './components/ChatPanel';
import { useNemoSocket } from './hooks/useNemoSocket';
import { useAudioPlayer } from './hooks/useAudioPlayer';

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);

  const { isConnected, sendMessage, lastResponse, error } = useNemoSocket();
  const { isPlaying, audioLevel, playAudio } = useAudioPlayer();

  // Track processed responses to prevent duplicates
  const processedResponseRef = useRef<string | null>(null);

  // Handle sending a message
  const handleSend = useCallback((text: string) => {
    // Add user message
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);

    // Send to backend
    sendMessage(text);
  }, [sendMessage]);

  // Handle response from Nemo - using ref to avoid dependency issues
  const playAudioRef = useRef(playAudio);
  playAudioRef.current = playAudio;

  useEffect(() => {
    if (lastResponse && lastResponse.text) {
      // Create unique ID for this response
      const responseId = `${lastResponse.text}-${Date.now()}`;

      // Skip if already processed (prevent duplicates)
      if (processedResponseRef.current === lastResponse.text) {
        return;
      }
      processedResponseRef.current = lastResponse.text;

      setIsTyping(false);

      // Add Nemo's message
      const nemoMessage: Message = {
        id: `nemo-${Date.now()}`,
        role: 'nemo',
        content: lastResponse.text,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, nemoMessage]);

      // Play audio if available
      if (lastResponse.audio) {
        playAudioRef.current(lastResponse.audio);
      }
    }
  }, [lastResponse]); // Only depend on lastResponse, not playAudio

  // Handle errors
  useEffect(() => {
    if (error) {
      console.error('Nemo error:', error);
      setIsTyping(false);
    }
  }, [error]);

  return (
    <div className="app-container">
      {/* 3D Background Scene */}
      <NemoScene
        isSpeaking={isPlaying}
        audioLevel={audioLevel}
      />

      {/* Chat Interface */}
      <ChatPanel
        messages={messages}
        onSend={handleSend}
        isConnected={isConnected}
        isTyping={isTyping}
      />

      {/* Error Toast */}
      {error && (
        <div
          style={{
            position: 'fixed',
            top: '1rem',
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(239, 68, 68, 0.9)',
            color: 'white',
            padding: '0.75rem 1.5rem',
            borderRadius: '8px',
            fontSize: '0.9rem',
            zIndex: 1000,
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}

export default App;
