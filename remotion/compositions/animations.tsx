import React from "react";
import {
    AbsoluteFill,
    useCurrentFrame,
    useVideoConfig,
    interpolate,
    spring,
    Easing,
    Sequence,
    Audio,
    Img,
    staticFile,
} from "remotion";
import { noise2D } from "@remotion/noise";
import { makeTransform, scale, rotate, translateX, translateY } from "@remotion/animation-utils";

// ═══════════════════════════════════════════════
// Typewriter Text — char-by-char reveal with cursor
// ═══════════════════════════════════════════════

export const TypewriterText: React.FC<{
    text: string;
    startFrame?: number;
    framesPerChar?: number;
    fontSize?: number;
    color?: string;
    cursorColor?: string;
}> = ({
    text,
    startFrame = 0,
    framesPerChar = 1.2,
    fontSize = 38,
    color = "#F0E6D3",
    cursorColor = "#FFD700",
}) => {
        const frame = useCurrentFrame();
        const localFrame = frame - startFrame;

        if (localFrame < 0) return null;

        const charsToShow = Math.min(
            Math.floor(localFrame / framesPerChar),
            text.length
        );
        const visibleText = text.slice(0, charsToShow);
        const isComplete = charsToShow >= text.length;

        // Blinking cursor (blinks every 15 frames)
        const cursorOpacity = isComplete
            ? interpolate(frame % 30, [0, 14, 15, 29], [1, 1, 0, 0])
            : 1;

        return (
            <div
                style={{
                    padding: "30px 65px",
                    flex: 1,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                }
                }
            >
                <p
                    style={
                        {
                            fontSize,
                            lineHeight: 1.65,
                            color,
                            fontFamily: "'Inter', 'Segoe UI', sans-serif",
                            fontWeight: 400,
                            textAlign: "center",
                            textShadow: "0 1px 6px rgba(0,0,0,0.3)",
                            whiteSpace: "pre-wrap",
                        }
                    }
                >
                    {visibleText}
                    < span
                        style={{
                            display: "inline-block",
                            width: 3,
                            height: fontSize * 0.8,
                            backgroundColor: cursorColor,
                            marginLeft: 2,
                            opacity: cursorOpacity,
                            verticalAlign: "middle",
                            borderRadius: 1,
                        }}
                    />
                </p>
            </div>
        );
    };

// ═══════════════════════════════════════════════
// Split Line Reveal — lines slide from alternating sides
// ═══════════════════════════════════════════════

export const SplitLineReveal: React.FC<{
    text: string;
    startFrame?: number;
    framesPerLine?: number;
    fontSize?: number;
    color?: string;
    maxCharsPerLine?: number;
}> = ({
    text,
    startFrame = 0,
    framesPerLine = 12,
    fontSize = 36,
    color = "#E8E0D8",
    maxCharsPerLine = 40,
}) => {
        const frame = useCurrentFrame();
        const { fps } = useVideoConfig();

        // Split text into lines
        const words = text.split(" ");
        const lines: string[] = [];
        let currentLine = "";
        for (const word of words) {
            if ((currentLine + " " + word).trim().length > maxCharsPerLine && currentLine) {
                lines.push(currentLine.trim());
                currentLine = word;
            } else {
                currentLine = currentLine ? currentLine + " " + word : word;
            }
        }
        if (currentLine.trim()) lines.push(currentLine.trim());

        return (
            <div
                style={{
                    padding: "30px 65px",
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 8,
                    overflow: "hidden",
                }
                }
            >
                {
                    lines.map((line, i) => {
                        const lineStartFrame = startFrame + i * framesPerLine;
                        const fromLeft = i % 2 === 0;

                        const progress = spring({
                            frame: frame - lineStartFrame,
                            fps,
                            config: { damping: 18, stiffness: 120, mass: 0.8 },
                        });

                        const xOffset = interpolate(progress, [0, 1], [fromLeft ? -600 : 600, 0]);
                        const opacity = interpolate(progress, [0, 0.3, 1], [0, 0.5, 1]);

                        return (
                            <div
                                key={i}
                                style={{
                                    fontSize,
                                    lineHeight: 1.65,
                                    color,
                                    fontFamily: "'Inter', 'Segoe UI', sans-serif",
                                    fontWeight: 400,
                                    textAlign: "center",
                                    textShadow: "0 1px 6px rgba(0,0,0,0.3)",
                                    opacity: frame < lineStartFrame ? 0 : opacity,
                                    transform: frame < lineStartFrame ? undefined : `translateX(${xOffset}px)`,
                                }
                                }
                            >
                                {line}
                            </div>
                        );
                    })}
            </div>
        );
    };

// ═══════════════════════════════════════════════
// Scale Pop In — scale 0 → overshoot → settle
// ═══════════════════════════════════════════════

export const ScalePopIn: React.FC<{
    children: React.ReactNode;
    delay?: number;
    rotationDeg?: number;
}> = ({ children, delay = 0, rotationDeg = 0 }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const scaleVal = spring({
        frame: frame - delay,
        fps,
        config: { damping: 8, stiffness: 150, mass: 0.6 },
    });

    const rot = interpolate(scaleVal, [0, 0.5, 1], [rotationDeg, rotationDeg * 0.3, 0]);

    return (
        <div
            style={{
                display: "inline-flex",
                transform: makeTransform([scale(scaleVal), rotate(`${rot}deg`)]),
                transformOrigin: "center center",
            }
            }
        >
            {children}
        </div>
    );
};

// ═══════════════════════════════════════════════
// Floating Element — noise-driven organic motion
// ═══════════════════════════════════════════════

export const FloatingElement: React.FC<{
    children: React.ReactNode;
    seed?: string;
    amplitudeX?: number;
    amplitudeY?: number;
    speed?: number;
}> = ({ children, seed = "float", amplitudeX = 15, amplitudeY = 10, speed = 0.01 }) => {
    const frame = useCurrentFrame();

    const x = noise2D(seed + "-x", frame * speed, 0) * amplitudeX;
    const y = noise2D(seed + "-y", 0, frame * speed) * amplitudeY;
    const rot = noise2D(seed + "-r", frame * speed * 0.5, 0) * 3;

    return (
        <div
            style={{
                display: "inline-flex",
                transform: makeTransform([translateX(x), translateY(y), rotate(`${rot}deg`)]),
            }
            }
        >
            {children}
        </div>
    );
};

// ═══════════════════════════════════════════════
// Animated Divider — SVG line that draws itself
// ═══════════════════════════════════════════════

export const AnimatedDivider: React.FC<{
    startFrame?: number;
    width?: number;
    color?: string;
    duration?: number;
}> = ({ startFrame = 20, width = 300, color = "#FFD700", duration = 25 }) => {
    const frame = useCurrentFrame();

    const progress = interpolate(frame, [startFrame, startFrame + duration], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.out(Easing.cubic),
    });

    const dashLength = width;
    const dashOffset = dashLength * (1 - progress);

    const opacity = interpolate(frame, [startFrame, startFrame + 8], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
    });

    return (
        <div style={{ display: "flex", justifyContent: "center", opacity }
        }>
            <svg width={width} height={6} viewBox={`0 0 ${width} 6`}>
                <defs>
                    <linearGradient id="divider-grad" x1="0%" y1="0%" x2="100%" y2="0%" >
                        <stop offset="0%" stopColor="transparent" />
                        <stop offset="30%" stopColor={color} />
                        <stop offset="70%" stopColor={color} />
                        <stop offset="100%" stopColor="transparent" />
                    </linearGradient>
                </defs>
                < line
                    x1={0}
                    y1={3}
                    x2={width}
                    y2={3}
                    stroke="url(#divider-grad)"
                    strokeWidth={2.5}
                    strokeDasharray={dashLength}
                    strokeDashoffset={dashOffset}
                    strokeLinecap="round"
                />
            </svg>
        </div>
    );
};

// ═══════════════════════════════════════════════
// Pulse Glow — pulsating ring effect
// ═══════════════════════════════════════════════

export const PulseGlow: React.FC<{
    color?: string;
    size?: number;
    pulseSpeed?: number;
}> = ({ color = "#FFD700", size = 200, pulseSpeed = 0.06 }) => {
    const frame = useCurrentFrame();

    const pulse = 0.8 + Math.sin(frame * pulseSpeed) * 0.2;
    const opacity = 0.15 + Math.sin(frame * pulseSpeed) * 0.1;

    return (
        <div
            style={{
                position: "absolute",
                width: size,
                height: size,
                borderRadius: "50%",
                background: `radial-gradient(circle, ${color}44 0%, ${color}11 40%, transparent 70%)`,
                transform: `scale(${pulse})`,
                opacity,
                pointerEvents: "none",
            }
            }
        />
    );
};

// ═══════════════════════════════════════════════
// Noise Particle Field — organic floating particles
// ═══════════════════════════════════════════════

export const NoiseParticleField: React.FC<{
    count?: number;
    color?: string;
    baseSpeed?: number;
}> = ({ count = 25, color = "rgba(255, 200, 50, 0.15)", baseSpeed = 0.008 }) => {
    const frame = useCurrentFrame();

    const particles = Array.from({ length: count }, (_, i) => {
        const seedX = `p${i}-x`;
        const seedY = `p${i}-y`;

        // Base position distributed across the canvas
        const baseX = ((i * 137.5) % 100);
        const baseY = ((i * 73.7) % 100);

        // Noise-driven offset
        const noiseX = noise2D(seedX, frame * baseSpeed, i * 0.5) * 12;
        const noiseY = noise2D(seedY, i * 0.5, frame * baseSpeed) * 12;

        const x = baseX + noiseX;
        const y = baseY + noiseY;
        const size = 3 + (i % 5) * 1.5;
        const opacity = interpolate(
            noise2D(`p${i}-o`, frame * 0.005, 0),
            [-1, 1],
            [0.05, 0.25]
        );

        return (
            <div
                key={i}
                style={{
                    position: "absolute",
                    left: `${x}%`,
                    top: `${y}%`,
                    width: size,
                    height: size,
                    borderRadius: "50%",
                    background: color,
                    opacity,
                    filter: `blur(${1 + (i % 3)}px)`,
                    transform: "translate(-50%, -50%)",
                }
                }
            />
        );
    });

    return <AbsoluteFill>{particles} </AbsoluteFill>;
};

// ═══════════════════════════════════════════════
// Decorative shape configs
// ═══════════════════════════════════════════════

interface ShapeConfig {
    type: "circle" | "star" | "triangle" | "ring";
    x: number; // percentage
    y: number; // percentage
    size: number;
    color: string;
    speed: number;
    seed: string;
    delay: number;
}

export const DecorativeShapes: React.FC<{
    shapes: ShapeConfig[];
}> = ({ shapes }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    return (
        <AbsoluteFill style={{ pointerEvents: "none" }
        }>
            {
                shapes.map((shape, i) => {
                    const enterProgress = spring({
                        frame: frame - shape.delay,
                        fps,
                        config: { damping: 15, stiffness: 80 },
                    });

                    const noiseX = noise2D(shape.seed + "-sx", frame * shape.speed, 0) * 20;
                    const noiseY = noise2D(shape.seed + "-sy", 0, frame * shape.speed) * 20;
                    const noiseRot = noise2D(shape.seed + "-sr", frame * shape.speed * 0.5, 0) * 15;

                    return (
                        <div
                            key={i}
                            style={{
                                position: "absolute",
                                left: `${shape.x + noiseX * 0.3}%`,
                                top: `${shape.y + noiseY * 0.3}%`,
                                transform: makeTransform([
                                    scale(enterProgress),
                                    rotate(`${noiseRot}deg`),
                                ]),
                                opacity: enterProgress * 0.3,
                            }
                            }
                        >
                            <ShapeSvg
                                type={shape.type}
                                size={shape.size}
                                color={shape.color}
                            />
                        </div>
                    );
                })}
        </AbsoluteFill>
    );
};

const ShapeSvg: React.FC<{ type: string; size: number; color: string }> = ({
    type,
    size,
    color,
}) => {
    const halfSize = size / 2;
    switch (type) {
        case "circle":
            return (
                <svg width={size} height={size} >
                    <circle
                        cx={halfSize}
                        cy={halfSize}
                        r={halfSize * 0.8}
                        fill="none"
                        stroke={color}
                        strokeWidth={1.5}
                    />
                </svg>
            );
        case "ring":
            return (
                <svg width={size} height={size} >
                    <circle
                        cx={halfSize}
                        cy={halfSize}
                        r={halfSize * 0.7}
                        fill="none"
                        stroke={color}
                        strokeWidth={2}
                        strokeDasharray="8 4"
                    />
                </svg>
            );
        case "star":
            const points = 5;
            const outerR = halfSize * 0.8;
            const innerR = halfSize * 0.35;
            let d = "";
            for (let p = 0; p < points * 2; p++) {
                const r = p % 2 === 0 ? outerR : innerR;
                const angle = (Math.PI * p) / points - Math.PI / 2;
                const x = halfSize + r * Math.cos(angle);
                const y = halfSize + r * Math.sin(angle);
                d += (p === 0 ? "M" : "L") + x + " " + y;
            }
            d += "Z";
            return (
                <svg width={size} height={size} >
                    <path d={d} fill="none" stroke={color} strokeWidth={1.5} />
                </svg>
            );
        case "triangle":
            return (
                <svg width={size} height={size} >
                    <polygon
                        points={`${halfSize},${size * 0.15} ${size * 0.15},${size * 0.85} ${size * 0.85},${size * 0.85}`}
                        fill="none"
                        stroke={color}
                        strokeWidth={1.5}
                    />
                </svg>
            );
        default:
            return null;
    }
};

// ═══════════════════════════════════════════════
// Brand Footer — animated brand reveal
// ═══════════════════════════════════════════════

export const BrandFooter: React.FC<{
    brandName: string;
    accent: string;
    appearAt?: number;
}> = ({ brandName, accent, appearAt }) => {
    const frame = useCurrentFrame();
    const { fps, durationInFrames } = useVideoConfig();

    const startFrame = appearAt ?? durationInFrames - 90;

    const slideUp = spring({
        frame: frame - startFrame,
        fps,
        config: { damping: 15, stiffness: 100 },
    });

    const opacity = interpolate(slideUp, [0, 0.5, 1], [0, 0.6, 1]);
    const yOffset = interpolate(slideUp, [0, 1], [60, 0]);
    const logoScale = interpolate(slideUp, [0, 1], [0.6, 1]);

    return (
        <div
            style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                opacity,
                transform: `translateY(${yOffset}px)`,
            }}
        >
            <Img
                src={staticFile("LogoFull.png")}
                style={{
                    width: 360,
                    objectFit: "contain",
                    transform: `scale(${logoScale})`,
                    filter: `drop-shadow(0 4px 30px ${accent}55)`,
                }}
            />
        </div>
    );
};

// ═══════════════════════════════════════════════
// Outro Shapes Converge — shapes fly inward
// ═══════════════════════════════════════════════

export const ConvergingShapes: React.FC<{
    accent: string;
    startFrame?: number;
}> = ({ accent, startFrame = 0 }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const positions = [
        { x: -120, y: -120, type: "star" as const },
        { x: 120, y: -100, type: "circle" as const },
        { x: -100, y: 120, type: "triangle" as const },
        { x: 130, y: 110, type: "ring" as const },
        { x: 0, y: -140, type: "circle" as const },
        { x: 0, y: 140, type: "star" as const },
    ];

    return (
        <AbsoluteFill
            style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                pointerEvents: "none",
            }
            }
        >
            {
                positions.map((pos, i) => {
                    const progress = spring({
                        frame: frame - startFrame - i * 3,
                        fps,
                        config: { damping: 20, stiffness: 60 },
                    });

                    const x = interpolate(progress, [0, 1], [pos.x * 4, pos.x * 0.3]);
                    const y = interpolate(progress, [0, 1], [pos.y * 4, pos.y * 0.3]);
                    const rot = interpolate(progress, [0, 1], [180, 0]);
                    const opacity = interpolate(progress, [0, 0.2, 1], [0, 0.15, 0.25]);

                    return (
                        <div
                            key={i}
                            style={{
                                position: "absolute",
                                transform: makeTransform([
                                    translateX(x),
                                    translateY(y),
                                    rotate(`${rot}deg`),
                                    scale(progress * 0.8),
                                ]),
                                opacity,
                            }
                            }
                        >
                            <ShapeSvg type={pos.type} size={30 + i * 5} color={accent} />
                        </div>
                    );
                })}
        </AbsoluteFill>
    );
};
