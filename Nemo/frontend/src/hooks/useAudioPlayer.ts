import { useState, useCallback, useRef, useEffect } from 'react';

interface UseAudioPlayerReturn {
    isPlaying: boolean;
    audioLevel: number;
    playAudio: (base64Audio: string) => Promise<void>;
    stopAudio: () => void;
}

export function useAudioPlayer(): UseAudioPlayerReturn {
    const [isPlaying, setIsPlaying] = useState(false);
    const [audioLevel, setAudioLevel] = useState(0);

    const audioRef = useRef<HTMLAudioElement | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const animationFrameRef = useRef<number | null>(null);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current);
            }
            if (audioContextRef.current) {
                audioContextRef.current.close();
            }
        };
    }, []);

    // Analyze audio levels for visualization
    const analyzeAudio = useCallback(() => {
        if (!analyserRef.current || !isPlaying) {
            setAudioLevel(0);
            return;
        }

        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(dataArray);

        // Calculate average volume
        const sum = dataArray.reduce((a, b) => a + b, 0);
        const average = sum / dataArray.length;
        const normalized = average / 255;

        setAudioLevel(normalized);

        animationFrameRef.current = requestAnimationFrame(analyzeAudio);
    }, [isPlaying]);

    // Play base64 encoded audio
    const playAudio = useCallback(async (base64Audio: string) => {
        if (!base64Audio) {
            console.warn('No audio data provided');
            return;
        }

        // Stop any currently playing audio
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }

        try {
            // Create audio element from base64
            const audio = new Audio(`data:audio/mp3;base64,${base64Audio}`);
            audioRef.current = audio;

            // Set up audio context for analysis (optional visual feedback)
            if (!audioContextRef.current) {
                audioContextRef.current = new AudioContext();
            }

            const audioContext = audioContextRef.current;

            // Resume context if suspended (browser autoplay policy)
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
            }

            // Create analyser for audio visualization
            const source = audioContext.createMediaElementSource(audio);
            const analyser = audioContext.createAnalyser();
            analyser.fftSize = 256;

            source.connect(analyser);
            analyser.connect(audioContext.destination);
            analyserRef.current = analyser;

            // Handle audio events
            audio.onplay = () => {
                console.log('🔊 Audio playing');
                setIsPlaying(true);
                analyzeAudio();
            };

            audio.onended = () => {
                console.log('🔇 Audio ended');
                setIsPlaying(false);
                setAudioLevel(0);
                if (animationFrameRef.current) {
                    cancelAnimationFrame(animationFrameRef.current);
                }
            };

            audio.onerror = (e) => {
                console.error('Audio error:', e);
                setIsPlaying(false);
                setAudioLevel(0);
            };

            // Play the audio
            await audio.play();

        } catch (error) {
            console.error('Failed to play audio:', error);
            setIsPlaying(false);
            setAudioLevel(0);
        }
    }, [analyzeAudio]);

    // Stop currently playing audio
    const stopAudio = useCallback(() => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }
        setIsPlaying(false);
        setAudioLevel(0);

        if (animationFrameRef.current) {
            cancelAnimationFrame(animationFrameRef.current);
        }
    }, []);

    return {
        isPlaying,
        audioLevel,
        playAudio,
        stopAudio,
    };
}
