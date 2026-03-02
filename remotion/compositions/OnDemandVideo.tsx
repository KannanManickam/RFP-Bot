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
import { wipe } from "@remotion/transitions/wipe";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { clockWipe } from "@remotion/transitions/clock-wipe";
import { whip } from "@remotion/sfx";
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

export const onDemandSchema = z.object({
    title: z.string(),
    content: z.string(),
    emoji: z.string().default("✨"),
    brandName: z.string().default("Sparktoship"),
    style: z.enum(["facts", "explainer", "quote"]).default("facts"),
});

type OnDemandProps = z.infer<typeof onDemandSchema>;

// ── Style presets ──
const STYLE_CONFIG: Record<
    string,
    {
        bg1: string;
        bg2: string;
        accent: string;
        shapes: Array<{
            type: "circle" | "star" | "triangle" | "ring";
            x: number;
            y: number;
            size: number;
            color: string;
            speed: number;
            seed: string;
            delay: number;
        }>;
        transitionType: "wipe" | "slide" | "clockWipe";
    }
> = {
    facts: {
        bg1: "hsl(260, 60%, 14%)",
        bg2: "hsl(280, 50%, 20%)",
        accent: "#A78BFA",
        shapes: [
            { type: "star", x: 8, y: 12, size: 30, color: "#A78BFA", speed: 0.006, seed: "fs1", delay: 10 },
            { type: "circle", x: 88, y: 18, size: 25, color: "#A78BFA", speed: 0.007, seed: "fs2", delay: 16 },
            { type: "ring", x: 10, y: 82, size: 28, color: "#A78BFA", speed: 0.005, seed: "fs3", delay: 22 },
            { type: "star", x: 90, y: 80, size: 22, color: "#A78BFA", speed: 0.008, seed: "fs4", delay: 18 },
        ],
        transitionType: "clockWipe",
    },
    explainer: {
        bg1: "hsl(200, 60%, 12%)",
        bg2: "hsl(220, 50%, 18%)",
        accent: "#60A5FA",
        shapes: [
            { type: "triangle", x: 8, y: 15, size: 28, color: "#60A5FA", speed: 0.005, seed: "es1", delay: 12 },
            { type: "circle", x: 90, y: 20, size: 24, color: "#60A5FA", speed: 0.006, seed: "es2", delay: 18 },
            { type: "triangle", x: 12, y: 78, size: 26, color: "#60A5FA", speed: 0.007, seed: "es3", delay: 14 },
            { type: "ring", x: 85, y: 82, size: 22, color: "#60A5FA", speed: 0.005, seed: "es4", delay: 20 },
        ],
        transitionType: "slide",
    },
    quote: {
        bg1: "hsl(340, 50%, 14%)",
        bg2: "hsl(20, 40%, 18%)",
        accent: "#FB923C",
        shapes: [
            { type: "circle", x: 10, y: 15, size: 26, color: "#FB923C", speed: 0.006, seed: "qs1", delay: 10 },
            { type: "ring", x: 88, y: 18, size: 24, color: "#FB923C", speed: 0.005, seed: "qs2", delay: 15 },
            { type: "circle", x: 8, y: 80, size: 22, color: "#FB923C", speed: 0.007, seed: "qs3", delay: 20 },
            { type: "ring", x: 90, y: 78, size: 28, color: "#FB923C", speed: 0.006, seed: "qs4", delay: 12 },
        ],
        transitionType: "wipe",
    },
};

// ── Animated mesh background ──
const MeshBackground: React.FC<{ bg1: string; bg2: string; shift?: number }> = ({
    bg1,
    bg2,
    shift = 0,
}) => {
    const frame = useCurrentFrame();
    const angle = 135 + Math.sin((frame + shift) * 0.015) * 25;

    return (
        <>
            <AbsoluteFill
                style={{
                    background: `linear-gradient(${angle}deg, ${bg1} 0%, ${bg2} 100%)`,
                }}
            />
            {/* Grid overlay */}
            <AbsoluteFill
                style={{
                    backgroundImage: `
                        linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
                    `,
                    backgroundSize: "60px 60px",
                    backgroundPosition: `${frame * 0.3}px ${frame * 0.2}px`,
                }}
            />
        </>
    );
};

// ── Quote mark for quote style ──
const QuoteMark: React.FC<{ accent: string }> = ({ accent }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const scaleVal = spring({
        frame: frame - 5,
        fps,
        config: { damping: 12, stiffness: 60 },
    });

    return (
        <div
            style={{
                position: "absolute",
                top: 60,
                left: 50,
                fontSize: 200,
                color: accent,
                opacity: scaleVal * 0.12,
                fontFamily: "Georgia, serif",
                lineHeight: 1,
                transform: `scale(${scaleVal})`,
                pointerEvents: "none",
            }}
        >
            "
        </div>
    );
};

// ═════════════════════════════════════════════
// Scene 1: INTRO — Emoji + Title + Shapes
// ═════════════════════════════════════════════
const IntroScene: React.FC<{
    title: string;
    emoji: string;
    config: (typeof STYLE_CONFIG)["facts"];
    styleKey: string;
}> = ({ title, emoji, config, styleKey }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const titleProgress = spring({
        frame: frame - 14,
        fps,
        config: { damping: 14, stiffness: 100, mass: 0.7 },
    });

    // Split title into words for staggered reveal
    const titleWords = title.split(" ");

    return (
        <AbsoluteFill>
            <MeshBackground bg1={config.bg1} bg2={config.bg2} />
            <NoiseParticleField count={18} color={`${config.accent}22`} />
            <DecorativeShapes shapes={config.shapes} />

            {/* Whip SFX */}
            <Audio src={whip} startFrom={0} volume={0.25} />

            {/* Quote mark for quote style */}
            {styleKey === "quote" && <QuoteMark accent={config.accent} />}

            <div
                style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    height: "100%",
                    gap: 24,
                    position: "relative",
                    zIndex: 1,
                }}
            >
                {/* Pulse glow + emoji */}
                <div style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <PulseGlow color={config.accent} size={240} />
                    <FloatingElement seed="od-emoji" amplitudeX={6} amplitudeY={8}>
                        <ScalePopIn delay={0} rotationDeg={12}>
                            <div
                                style={{
                                    fontSize: 110,
                                    filter: `drop-shadow(0 6px 30px ${config.accent}55)`,
                                }}
                            >
                                {emoji}
                            </div>
                        </ScalePopIn>
                    </FloatingElement>
                </div>

                {/* Title — word-by-word spring */}
                <div
                    style={{
                        display: "flex",
                        flexWrap: "wrap",
                        justifyContent: "center",
                        gap: "0 12px",
                        padding: "0 60px",
                    }}
                >
                    {titleWords.map((word, i) => {
                        const wordProgress = spring({
                            frame: frame - 14 - i * 4,
                            fps,
                            config: { damping: 14, stiffness: 120, mass: 0.6 },
                        });

                        return (
                            <span
                                key={i}
                                style={{
                                    fontSize: 50,
                                    fontWeight: 800,
                                    color: config.accent,
                                    letterSpacing: 3,
                                    textTransform: "uppercase",
                                    opacity: wordProgress,
                                    transform: `translateY(${(1 - wordProgress) * 30}px)`,
                                    textShadow: `0 3px 25px ${config.accent}44`,
                                    fontFamily: "'Inter', 'Segoe UI', sans-serif",
                                    display: "inline-block",
                                }}
                            >
                                {word}
                            </span>
                        );
                    })}
                </div>

                {/* Animated divider */}
                <AnimatedDivider startFrame={20} width={300} color={config.accent} duration={28} />
            </div>
        </AbsoluteFill>
    );
};

// ═════════════════════════════════════════════
// Scene 2: BODY — Content text with SplitLineReveal
// ═════════════════════════════════════════════
const BodyScene: React.FC<{
    content: string;
    title: string;
    emoji: string;
    config: (typeof STYLE_CONFIG)["facts"];
    styleKey: string;
}> = ({ content, title, emoji, config, styleKey }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const headerOpacity = spring({
        frame: frame - 3,
        fps,
        config: { damping: 20, stiffness: 120 },
    });

    // Fewer, subtler shapes for content area
    const contentShapes = config.shapes.map((s) => ({
        ...s,
        size: s.size * 0.7,
        color: `${config.accent}66`,
    }));

    return (
        <AbsoluteFill>
            <MeshBackground bg1={config.bg1} bg2={config.bg2} shift={200} />
            <NoiseParticleField count={15} color={`${config.accent}18`} baseSpeed={0.005} />
            <DecorativeShapes shapes={contentShapes} />

            {/* Quote mark watermark */}
            {styleKey === "quote" && <QuoteMark accent={config.accent} />}

            <div
                style={{
                    display: "flex",
                    flexDirection: "column",
                    height: "100%",
                    position: "relative",
                    zIndex: 1,
                }}
            >
                {/* Compact header bar */}
                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                        padding: "36px 60px 0",
                        opacity: headerOpacity,
                    }}
                >
                    <span style={{ fontSize: 36 }}>{emoji}</span>
                    <span
                        style={{
                            fontSize: 20,
                            color: config.accent,
                            fontWeight: 700,
                            letterSpacing: 3,
                            textTransform: "uppercase",
                            fontFamily: "'Inter', 'Segoe UI', sans-serif",
                        }}
                    >
                        {title}
                    </span>
                    <div
                        style={{
                            flex: 1,
                            height: 1,
                            background: `linear-gradient(90deg, ${config.accent}44, transparent)`,
                            marginLeft: 10,
                        }}
                    />
                </div>

                {/* Content — SplitLineReveal */}
                <SplitLineReveal
                    text={content}
                    startFrame={12}
                    framesPerLine={10}
                    fontSize={38}
                    color="#E8E0D8"
                    maxCharsPerLine={38}
                />
            </div>
        </AbsoluteFill>
    );
};

// ═════════════════════════════════════════════
// Scene 3: OUTRO — Brand + converging shapes
// ═════════════════════════════════════════════
const OutroScene: React.FC<{
    brandName: string;
    config: (typeof STYLE_CONFIG)["facts"];
}> = ({ brandName, config }) => {
    const frame = useCurrentFrame();

    const dimOverlay = interpolate(frame, [0, 60], [0, 0.3], {
        extrapolateRight: "clamp",
    });

    return (
        <AbsoluteFill>
            <MeshBackground bg1={config.bg1} bg2={config.bg2} shift={400} />
            <NoiseParticleField count={10} color={`${config.accent}10`} />

            <AbsoluteFill style={{ background: `rgba(0, 0, 0, ${dimOverlay})` }} />

            <ConvergingShapes accent={config.accent} startFrame={5} />
            <BrandFooter brandName={brandName} accent={config.accent} appearAt={10} />
        </AbsoluteFill>
    );
};
// ── Build style-specific transition element ──
const getStyleTransition = (type: string, width: number, height: number) => {
    switch (type) {
        case "slide":
            return (
                <TransitionSeries.Transition
                    presentation={slide({ direction: "from-left" })}
                    timing={springTiming({ config: { damping: 200 } })}
                />
            );
        case "clockWipe":
            return (
                <TransitionSeries.Transition
                    presentation={clockWipe({ width, height })}
                    timing={linearTiming({ durationInFrames: 25 })}
                />
            );
        case "wipe":
        default:
            return (
                <TransitionSeries.Transition
                    presentation={wipe({ direction: "from-left" })}
                    timing={linearTiming({ durationInFrames: 25 })}
                />
            );
    }
};

// ═════════════════════════════════════════════
// Main Composition
// ═════════════════════════════════════════════

const INTRO_FRAMES = 75;
const OUTRO_FRAMES = 75;
const TRANSITION_OVERLAP = 45; // transitions cause sequence overlap

export const OnDemandVideo: React.FC<OnDemandProps> = ({
    title,
    content,
    emoji,
    brandName,
    style: styleKey,
}) => {
    const config = STYLE_CONFIG[styleKey] || STYLE_CONFIG.facts;
    const { width, height, durationInFrames } = useVideoConfig();

    // Content scene gets all remaining frames
    // Add back TRANSITION_OVERLAP because transitions cause sequences to overlap,
    // meaning the content scene needs those extra frames to fill the visual gap
    const contentFrames = Math.max(
        durationInFrames - INTRO_FRAMES - OUTRO_FRAMES + TRANSITION_OVERLAP,
        210
    );

    return (
        <AbsoluteFill style={{ fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>
            <TransitionSeries>
                {/* Scene 1: Intro (2.5s = 75 frames) */}
                <TransitionSeries.Sequence durationInFrames={INTRO_FRAMES}>
                    <IntroScene title={title} emoji={emoji} config={config} styleKey={styleKey} />
                </TransitionSeries.Sequence>

                {/* Transition based on style */}
                {getStyleTransition(config.transitionType, width, height)}

                {/* Scene 2: Body (dynamic duration) */}
                <TransitionSeries.Sequence durationInFrames={contentFrames}>
                    <BodyScene
                        content={content}
                        title={title}
                        emoji={emoji}
                        config={config}
                        styleKey={styleKey}
                    />
                </TransitionSeries.Sequence>

                {/* Fade out to outro */}
                <TransitionSeries.Transition
                    presentation={fade()}
                    timing={linearTiming({ durationInFrames: 20 })}
                />

                {/* Scene 3: Outro (2.5s = 75 frames) */}
                <TransitionSeries.Sequence durationInFrames={OUTRO_FRAMES}>
                    <OutroScene brandName={brandName} config={config} />
                </TransitionSeries.Sequence>
            </TransitionSeries>
        </AbsoluteFill>
    );
};


