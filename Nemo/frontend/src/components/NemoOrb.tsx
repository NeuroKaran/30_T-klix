import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface NemoOrbProps {
    isSpeaking: boolean;
    audioLevel?: number;
}

export function NemoOrb({ isSpeaking, audioLevel = 0 }: NemoOrbProps) {
    const pointsRef = useRef<THREE.Points>(null);
    const materialRef = useRef<THREE.ShaderMaterial>(null);

    // Generate particle positions on a sphere
    const { positions, colors } = useMemo(() => {
        const count = 2000;
        const positions = new Float32Array(count * 3);
        const colors = new Float32Array(count * 3);

        for (let i = 0; i < count; i++) {
            // Fibonacci sphere distribution
            const phi = Math.acos(-1 + (2 * i) / count);
            const theta = Math.sqrt(count * Math.PI) * phi;

            const radius = 1.5 + Math.random() * 0.3;

            positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
            positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
            positions[i * 3 + 2] = radius * Math.cos(phi);

            // Gradient colors: purple -> cyan -> pink
            const t = i / count;
            if (t < 0.33) {
                // Purple
                colors[i * 3] = 0.55;     // R
                colors[i * 3 + 1] = 0.36; // G
                colors[i * 3 + 2] = 0.96; // B
            } else if (t < 0.66) {
                // Cyan
                colors[i * 3] = 0.02;
                colors[i * 3 + 1] = 0.71;
                colors[i * 3 + 2] = 0.83;
            } else {
                // Pink
                colors[i * 3] = 0.93;
                colors[i * 3 + 1] = 0.27;
                colors[i * 3 + 2] = 0.60;
            }
        }

        return { positions, colors };
    }, []);

    // Shader material for glowing particles
    const shaderMaterial = useMemo(() => {
        return new THREE.ShaderMaterial({
            uniforms: {
                uTime: { value: 0 },
                uScale: { value: 1 },
                uAudioLevel: { value: 0 },
            },
            vertexShader: `
        uniform float uTime;
        uniform float uScale;
        uniform float uAudioLevel;
        
        attribute vec3 color;
        varying vec3 vColor;
        varying float vAlpha;
        
        void main() {
          vColor = color;
          
          // Noise-based displacement
          float noise = sin(position.x * 5.0 + uTime) * 
                        cos(position.y * 5.0 + uTime) * 
                        sin(position.z * 5.0 + uTime);
          
          // Audio-reactive scale
          float audioScale = 1.0 + uAudioLevel * 0.3;
          
          vec3 pos = position * uScale * audioScale;
          pos += normal * noise * 0.1 * (1.0 + uAudioLevel);
          
          vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
          gl_Position = projectionMatrix * mvPosition;
          
          // Size attenuation
          float size = 3.0 + uAudioLevel * 2.0;
          gl_PointSize = size * (300.0 / -mvPosition.z);
          
          vAlpha = 0.6 + uAudioLevel * 0.4;
        }
      `,
            fragmentShader: `
        varying vec3 vColor;
        varying float vAlpha;
        
        void main() {
          // Circular point with soft edges
          float dist = length(gl_PointCoord - vec2(0.5));
          if (dist > 0.5) discard;
          
          float alpha = vAlpha * (1.0 - dist * 2.0);
          gl_FragColor = vec4(vColor, alpha);
        }
      `,
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        });
    }, []);

    // Animation loop
    useFrame((state) => {
        if (pointsRef.current && materialRef.current) {
            const time = state.clock.elapsedTime;

            // Rotate slowly
            pointsRef.current.rotation.y = time * 0.1;
            pointsRef.current.rotation.x = Math.sin(time * 0.2) * 0.1;

            // Update uniforms
            materialRef.current.uniforms.uTime.value = time;
            materialRef.current.uniforms.uAudioLevel.value = isSpeaking ? 0.5 + audioLevel : audioLevel * 0.3;

            // Pulsing scale when speaking
            const baseScale = 1 + Math.sin(time * 2) * 0.02;
            const speakingScale = isSpeaking ? 1 + Math.sin(time * 8) * 0.05 : 0;
            materialRef.current.uniforms.uScale.value = baseScale + speakingScale;
        }
    });

    return (
        <points ref={pointsRef}>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    count={positions.length / 3}
                    array={positions}
                    itemSize={3}
                />
                <bufferAttribute
                    attach="attributes-color"
                    count={colors.length / 3}
                    array={colors}
                    itemSize={3}
                />
            </bufferGeometry>
            <primitive object={shaderMaterial} ref={materialRef} attach="material" />
        </points>
    );
}
