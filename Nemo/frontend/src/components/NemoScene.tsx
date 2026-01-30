import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment } from '@react-three/drei';
import { NemoOrb } from './NemoOrb';

interface NemoSceneProps {
    isSpeaking: boolean;
    audioLevel?: number;
}

export function NemoScene({ isSpeaking, audioLevel = 0 }: NemoSceneProps) {
    return (
        <div className="scene-container">
            <Canvas
                camera={{ position: [0, 0, 5], fov: 60 }}
                gl={{
                    antialias: true,
                    alpha: true,
                    powerPreference: 'high-performance'
                }}
            >
                {/* Ambient lighting */}
                <ambientLight intensity={0.3} />

                {/* Colored point lights for dramatic effect */}
                <pointLight position={[5, 5, 5]} intensity={1} color="#8b5cf6" />
                <pointLight position={[-5, -5, 5]} intensity={0.8} color="#06b6d4" />
                <pointLight position={[0, -5, -5]} intensity={0.6} color="#ec4899" />

                {/* Environment for reflections */}
                <Environment preset="night" />

                {/* The Nemo orb */}
                <NemoOrb isSpeaking={isSpeaking} audioLevel={audioLevel} />

                {/* Subtle mouse interaction */}
                <OrbitControls
                    enableZoom={false}
                    enablePan={false}
                    maxPolarAngle={Math.PI / 1.5}
                    minPolarAngle={Math.PI / 3}
                    autoRotate
                    autoRotateSpeed={0.5}
                />
            </Canvas>

            {/* Gradient overlay for depth */}
            <div
                style={{
                    position: 'absolute',
                    inset: 0,
                    pointerEvents: 'none',
                    background: 'radial-gradient(circle at center, transparent 30%, rgba(10, 10, 26, 0.8) 100%)',
                }}
            />
        </div>
    );
}
