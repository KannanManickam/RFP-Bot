import React from "react";
import {
    AbsoluteFill,
    useCurrentFrame,
    useVideoConfig,
    interpolate,
    spring,
    Easing,
    Audio,
} from "remotion";
import {
    TransitionSeries,
    linearTiming,
    springTiming,
} from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";
import { clockWipe } from "@remotion/transitions/clock-wipe";
import { fade } from "@remotion/transitions/fade";
import { whoosh } from "@remotion/sfx";
import { z } from "zod";
import {
    SplitLineReveal,
    ScalePopIn,
    FloatingElement,
    AnimatedDivider,
    PulseGlow,
    NoiseParticleField,
    DecorativeShapes,
    BrandFooter,
    ConvergingShapes,
} from "./animations";

export const funFactSchema = z.object({
    factText: z.string(),
    emoji: z.string().default("🧠"),
    brandName: z.string().default("Sparktoship"),
});

type FunFactProps = z.infer<typeof funFactSchema>;

// ── Style constants ──
const GOLD = "#FFD700";
const TEXT_COLOR = "#F0E6D3";

// ── Animated gradient background ──
const AnimatedBackground: React.FC<{ hueOffset?: number }> = ({ hueOffset = 0 }) => {
    const frame = useCurrentFrame();
    const hue1 = ((frame * 0.3) + hueOffset) % 360;
    const hue2 = (hue1 + 40) % 360;
    const hue3 = (hue1 + 80) % 360;

    return (
        <AbsoluteFill
            style={{
                background: `linear-gradient(${135 + Math.sin(frame * 0.02) * 20}deg, 
          hsl(${hue1}, 70%, 15%) 0%, 
          hsl(${hue2}, 60%, 20%) 50%, 
          hsl(${hue3}, 50%, 12%) 100%)`,
            }}
        />
    );
};

// ── Intro shapes config ──
const INTRO_SHAPES = [
    { type: "star" as const, x: 8, y: 12, size: 35, color: GOLD, speed: 0.006, seed: "is1", delay: 10 },
    { type: "circle" as const, x: 85, y: 15, size: 28, color: GOLD, speed: 0.007, seed: "is2", delay: 18 },
    { type: "triangle" as const, x: 10, y: 80, size: 32, color: GOLD, speed: 0.005, seed: "is3", delay: 25 },
    { type: "ring" as const, x: 88, y: 78, size: 30, color: GOLD, speed: 0.008, seed: "is4", delay: 15 },
    { type: "star" as const, x: 50, y: 8, size: 24, color: GOLD, speed: 0.009, seed: "is5", delay: 22 },
];

// ── Content shapes config ──
const CONTENT_SHAPES = [
    { type: "circle" as const, x: 5, y: 20, size: 22, color: `${GOLD}88`, speed: 0.005, seed: "cs1", delay: 5 },
    { type: "star" as const, x: 92, y: 50, size: 26, color: `${GOLD}88`, speed: 0.006, seed: "cs2", delay: 12 },
    { type: "ring" as const, x: 8, y: 70, size: 20, color: `${GOLD}88`, speed: 0.004, seed: "cs3", delay: 8 },
    { type: "triangle" as const, x: 90, y: 85, size: 24, color: `${GOLD}88`, speed: 0.007, seed: "cs4", delay: 15 },
];

// ═════════════════════════════════════════════
// Scene 1: INTRO — Emoji + Title
// ═════════════════════════════════════════════
const IntroScene: React.FC<{ emoji: string }> = ({ emoji }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const titleProgress = spring({
        frame: frame - 12,
        fps,
        config: { damping: 14, stiffness: 100, mass: 0.7 },
    });

    const titleY = interpolate(titleProgress, [0, 1], [50, 0]);
    const titleOpacity = interpolate(titleProgress, [0, 0.3, 1], [0, 0.5, 1]);

    return (
        <AbsoluteFill>
            <AnimatedBackground />
            <NoiseParticleField count={20} color="rgba(255, 200, 50, 0.12)" />
            <DecorativeShapes shapes={INTRO_SHAPES} />

            {/* Whoosh at start */}
            <Audio src={whoosh} startFrom={0} volume={0.3} />

            <div
                style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    height: "100%",
                    gap: 20,
                    position: "relative",
                    zIndex: 1,
                }}
            >
                {/* Pulse glow behind emoji */}
                <div style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <PulseGlow color={GOLD} size={250} />
                    <FloatingElement seed="emoji-intro" amplitudeX={5} amplitudeY={8}>
                        <ScalePopIn delay={0} rotationDeg={15}>
                            <div
                                style={{
                                    fontSize: 120,
                                    filter: "drop-shadow(0 6px 30px rgba(255,200,50,0.5))",
                                }}
                            >
                                {emoji}
                            </div>
                        </ScalePopIn>
                    </FloatingElement>
                </div>

                {/* Title */}
                <div
                    style={{
                        fontSize: 56,
                        fontWeight: 800,
                        color: GOLD,
                        letterSpacing: 5,
                        textTransform: "uppercase",
                        opacity: titleOpacity,
                        transform: `translateY(${titleY}px)`,
                        textShadow: "0 3px 25px rgba(255,215,0,0.4)",
                        fontFamily: "'Inter', 'Segoe UI', sans-serif",
                    }}
                >
                    Fun Fact
                </div>

                {/* Animated divider */}
                <AnimatedDivider startFrame={18} width={320} color={GOLD} duration={30} />
            </div>
        </AbsoluteFill>
    );
};

// ═════════════════════════════════════════════
// Scene 2: CONTENT — Typewriter text reveal
// ═════════════════════════════════════════════
const ContentScene: React.FC<{ factText: string; emoji: string }> = ({ factText, emoji }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    // Small emoji in top left as context
    const miniEmojiOpacity = spring({
        frame: frame - 5,
        fps,
        config: { damping: 20, stiffness: 120 },
    });

    return (
        <AbsoluteFill>
            <AnimatedBackground hueOffset={120} />
            <NoiseParticleField count={18} color="rgba(255, 200, 50, 0.1)" baseSpeed={0.006} />
            <DecorativeShapes shapes={CONTENT_SHAPES} />

            <div
                style={{
                    display: "flex",
                    flexDirection: "column",
                    height: "100%",
                    position: "relative",
                    zIndex: 1,
                }}
            >
                {/* Mini emoji + label */}
                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                        padding: "40px 60px 0",
                        opacity: miniEmojiOpacity,
                    }}
                >
                    <span style={{ fontSize: 40 }}>{emoji}</span>
                    <span
                        style={{
                            fontSize: 22,
                            color: GOLD,
                            fontWeight: 700,
                            letterSpacing: 3,
                            textTransform: "uppercase",
                            fontFamily: "'Inter', 'Segoe UI', sans-serif",
                        }}
                    >
                        Fun Fact
                    </span>
                    <div
                        style={{
                            flex: 1,
                            height: 1,
                            background: `linear-gradient(90deg, ${GOLD}44, transparent)`,
                            marginLeft: 10,
                        }}
                    />
                </div>

                {/* SplitLineReveal — lines slide in from alternating sides */}
                <SplitLineReveal
                    text={factText}
                    startFrame={15}
                    framesPerLine={12}
                    fontSize={40}
                    color={TEXT_COLOR}
                    maxCharsPerLine={40}
                />
            </div>
        </AbsoluteFill>
    );
};

// ═════════════════════════════════════════════
// Scene 3: OUTRO — Brand + converging shapes
// ═════════════════════════════════════════════
const OutroScene: React.FC<{ brandName: string }> = ({ brandName }) => {
    const frame = useCurrentFrame();

    // Gentle fade to darker
    const dimOverlay = interpolate(frame, [0, 60], [0, 0.3], {
        extrapolateRight: "clamp",
    });

    return (
        <AbsoluteFill>
            <AnimatedBackground hueOffset={240} />
            <NoiseParticleField count={12} color="rgba(255, 200, 50, 0.08)" />

            {/* Dim overlay for cinematic feel */}
            <AbsoluteFill
                style={{
                    background: `rgba(0, 0, 0, ${dimOverlay})`,
                }}
            />

            <ConvergingShapes accent={GOLD} startFrame={5} />
            <BrandFooter brandName={brandName} accent={GOLD} appearAt={10} />
        </AbsoluteFill>
    );
};
// ═════════════════════════════════════════════
// Main Composition — TransitionSeries
// ═════════════════════════════════════════════

const INTRO_FRAMES = 75;
const OUTRO_FRAMES = 75;
const TRANSITION_OVERLAP = 45; // transitions cause sequence overlap

export const FunFact: React.FC<FunFactProps> = ({
    factText,
    emoji,
    brandName,
}) => {
    const { width, height, durationInFrames } = useVideoConfig();

    // Content scene gets all remaining frames after intro, outro, and transitions
    const contentFrames = Math.max(
        durationInFrames - INTRO_FRAMES - OUTRO_FRAMES + TRANSITION_OVERLAP,
        210
    );

    return (
        <AbsoluteFill style={{ fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>
            <TransitionSeries>
                {/* Scene 1: Intro (2.5s = 75 frames) */}
                <TransitionSeries.Sequence durationInFrames={INTRO_FRAMES}>
                    <IntroScene emoji={emoji} />
                </TransitionSeries.Sequence>

                {/* Transition: slide from bottom */}
                <TransitionSeries.Transition
                    presentation={slide({ direction: "from-bottom" })}
                    timing={springTiming({ config: { damping: 200 } })}
                />

                {/* Scene 2: Content (dynamic duration) */}
                <TransitionSeries.Sequence durationInFrames={contentFrames}>
                    <ContentScene factText={factText} emoji={emoji} />
                </TransitionSeries.Sequence>

                {/* Transition: clock wipe */}
                <TransitionSeries.Transition
                    presentation={clockWipe({ width, height })}
                    timing={linearTiming({ durationInFrames: 25 })}
                />

                {/* Scene 3: Outro (2.5s = 75 frames) */}
                <TransitionSeries.Sequence durationInFrames={OUTRO_FRAMES}>
                    <OutroScene brandName={brandName} />
                </TransitionSeries.Sequence>
            </TransitionSeries>
        </AbsoluteFill>
    );
};

