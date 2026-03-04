import React from "react";
import {
    AbsoluteFill,
    useCurrentFrame,
    useVideoConfig,
    interpolate,
    spring,
    Audio,
    staticFile,
    Sequence,
} from "remotion";
import {
    TransitionSeries,
    linearTiming,
    springTiming,
} from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";
import { clockWipe } from "@remotion/transitions/clock-wipe";
import { whoosh } from "@remotion/sfx";
import { z } from "zod";
import {
    ScalePopIn,
    FloatingElement,
    AnimatedDivider,
    PulseGlow,
    NoiseParticleField,
    DecorativeShapes,
    BrandFooter,
    ConvergingShapes,
    KaraokeLine,
    ZoomPunch,
    ParticleBurst,
    SourceBadge,
    NumberRoll,
} from "./animations";

export const funFactSchema = z.object({
    factText: z.string(),
    emoji: z.string().default("🧠"),
    brandName: z.string().default("Sparktoship"),
    imageBase64: z.string().optional(),
    hookLine: z.string().optional(),
    sourceLabel: z.string().optional(),
});

type FunFactProps = z.infer<typeof funFactSchema>;

const GOLD = "#FFD700";
const TEXT_COLOR = "#F0E6D3";

// ── Number extraction helper ──
function extractFirstNumber(text: string): { value: number; prefix: string; suffix: string } | null {
    const match = text.match(/(\D{0,8}?)([\d,]+(?:\.\d+)?)(\s*(?:million|billion|thousand|km|m|%|mph|°)?)/i);
    if (!match) return null;
    const raw = parseFloat(match[2].replace(/,/g, ""));
    if (isNaN(raw) || raw < 2 || raw > 999_999_999) return null;
    return {
        value: Math.floor(raw),
        prefix: match[1]?.trim() || "",
        suffix: match[3]?.trim() || "",
    };
}

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

// ── Image Background with Ken Burns & Blur ──
const ImageBackground: React.FC<{ base64Image: string; durationInFrames: number }> = ({ base64Image, durationInFrames }) => {
    const frame = useCurrentFrame();
    const scale = interpolate(frame, [0, durationInFrames], [1.0, 1.15], { extrapolateRight: "clamp" });
    return (
        <AbsoluteFill>
            <AbsoluteFill style={{ overflow: "hidden" }}>
                <img
                    src={base64Image}
                    style={{
                        width: "100%",
                        height: "100%",
                        objectFit: "cover",
                        filter: "blur(8px)",
                        transform: `scale(${scale})`,
                    }}
                />
            </AbsoluteFill>
            <AbsoluteFill style={{ backgroundColor: "rgba(0, 0, 0, 0.52)" }} />
        </AbsoluteFill>
    );
};

const INTRO_SHAPES = [
    { type: "star" as const, x: 8, y: 12, size: 35, color: GOLD, speed: 0.006, seed: "is1", delay: 10 },
    { type: "circle" as const, x: 85, y: 15, size: 28, color: GOLD, speed: 0.007, seed: "is2", delay: 18 },
    { type: "triangle" as const, x: 10, y: 80, size: 32, color: GOLD, speed: 0.005, seed: "is3", delay: 25 },
    { type: "ring" as const, x: 88, y: 78, size: 30, color: GOLD, speed: 0.008, seed: "is4", delay: 15 },
    { type: "star" as const, x: 50, y: 8, size: 24, color: GOLD, speed: 0.009, seed: "is5", delay: 22 },
];

const CONTENT_SHAPES = [
    { type: "circle" as const, x: 5, y: 20, size: 22, color: `${GOLD}88`, speed: 0.005, seed: "cs1", delay: 5 },
    { type: "star" as const, x: 92, y: 50, size: 26, color: `${GOLD}88`, speed: 0.006, seed: "cs2", delay: 12 },
    { type: "ring" as const, x: 8, y: 70, size: 20, color: `${GOLD}88`, speed: 0.004, seed: "cs3", delay: 8 },
    { type: "triangle" as const, x: 90, y: 85, size: 24, color: `${GOLD}88`, speed: 0.007, seed: "cs4", delay: 15 },
];

// ═════════════════════════════════════════════
// Scene 1: INTRO — Emoji + Title + "Did you know?"
// ═════════════════════════════════════════════
const IntroScene: React.FC<{ emoji: string; imageBase64?: string }> = ({ emoji, imageBase64 }) => {
    const frame = useCurrentFrame();
    const { fps, durationInFrames } = useVideoConfig();

    const titleProgress = spring({ frame: frame - 12, fps, config: { damping: 14, stiffness: 100, mass: 0.7 } });
    const titleY = interpolate(titleProgress, [0, 1], [50, 0]);
    const titleOpacity = interpolate(titleProgress, [0, 0.3, 1], [0, 0.5, 1]);

    const teaseProgress = spring({ frame: frame - 36, fps, config: { damping: 18, stiffness: 100, mass: 0.8 } });
    const teaseOpacity = interpolate(teaseProgress, [0, 1], [0, 1]);
    const teaseY = interpolate(teaseProgress, [0, 1], [18, 0]);

    return (
        <AbsoluteFill>
            {imageBase64 ? (
                <ImageBackground base64Image={imageBase64} durationInFrames={durationInFrames} />
            ) : (
                <>
                    <AnimatedBackground />
                    <NoiseParticleField count={20} color="rgba(255, 200, 50, 0.12)" />
                </>
            )}
            <DecorativeShapes shapes={INTRO_SHAPES} />
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
                <div style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <PulseGlow color={GOLD} size={250} />
                    <FloatingElement seed="emoji-intro" amplitudeX={5} amplitudeY={8}>
                        <ScalePopIn delay={0} rotationDeg={15}>
                            <div style={{ fontSize: 120, filter: "drop-shadow(0 6px 30px rgba(255,200,50,0.5))" }}>
                                {emoji}
                            </div>
                        </ScalePopIn>
                    </FloatingElement>
                </div>

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

                <AnimatedDivider startFrame={18} width={320} color={GOLD} duration={30} />

                {/* Static "Did you know?" teaser */}
                <div
                    style={{
                        fontSize: 32,
                        fontWeight: 400,
                        color: TEXT_COLOR,
                        fontFamily: "'Inter', 'Segoe UI', sans-serif",
                        fontStyle: "italic",
                        opacity: teaseOpacity,
                        transform: `translateY(${teaseY}px)`,
                        textShadow: "0 1px 8px rgba(0,0,0,0.5)",
                        letterSpacing: 1,
                    }}
                >
                    Did you know?
                </div>
            </div>
        </AbsoluteFill>
    );
};

// ═════════════════════════════════════════════
// Scene 2: CONTENT — Karaoke + ZoomPunch + ParticleBurst + SourceBadge
// ═════════════════════════════════════════════
const ContentScene: React.FC<{
    factText: string;
    emoji: string;
    imageBase64?: string;
    sourceLabel?: string;
}> = ({ factText, emoji, imageBase64, sourceLabel }) => {
    const frame = useCurrentFrame();
    const { fps, durationInFrames } = useVideoConfig();

    const miniEmojiOpacity = spring({ frame: frame - 5, fps, config: { damping: 20, stiffness: 120 } });

    const KARAOKE_START = 15;
    const FRAMES_PER_WORD = 8;

    const numberInfo = extractFirstNumber(factText);
    const showNumberRoll = numberInfo !== null && numberInfo.value >= 2;
    const karaokeStart = showNumberRoll ? KARAOKE_START + 50 : KARAOKE_START;

    return (
        <AbsoluteFill>
            {imageBase64 ? (
                <ImageBackground base64Image={imageBase64} durationInFrames={durationInFrames} />
            ) : (
                <>
                    <AnimatedBackground hueOffset={120} />
                    <NoiseParticleField count={18} color="rgba(255, 200, 50, 0.1)" baseSpeed={0.006} />
                </>
            )}
            <DecorativeShapes shapes={CONTENT_SHAPES} />

            <ZoomPunch delay={0}>
                <div
                    style={{
                        display: "flex",
                        flexDirection: "column",
                        height: "100%",
                        position: "relative",
                        zIndex: 1,
                    }}
                >
                    {/* Mini emoji header */}
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

                    {/* Optional Number Roll */}
                    {showNumberRoll && numberInfo && (
                        <div style={{ padding: "20px 60px 0", display: "flex", justifyContent: "center" }}>
                            <NumberRoll
                                target={numberInfo.value}
                                startFrame={KARAOKE_START}
                                prefix={numberInfo.prefix}
                                suffix={numberInfo.suffix}
                                fontSize={72}
                                color={GOLD}
                            />
                        </div>
                    )}

                    {/* Karaoke word-by-word highlight */}
                    <KaraokeLine
                        text={factText}
                        startFrame={karaokeStart}
                        framesPerWord={FRAMES_PER_WORD}
                        fontSize={40}
                        dimColor="rgba(240, 230, 211, 0.28)"
                        accent={GOLD}
                        maxCharsPerLine={38}
                    />
                </div>
            </ZoomPunch>

            {/* Particle burst at first word */}
            <ParticleBurst triggerFrame={karaokeStart} color={GOLD} count={18} />

            {/* Source badge */}
            {sourceLabel && (
                <SourceBadge label={sourceLabel} appearAt={karaokeStart + 10} accent={GOLD} />
            )}
        </AbsoluteFill>
    );
};

// ═════════════════════════════════════════════
// Scene 3: OUTRO — Brand + converging shapes
// ═════════════════════════════════════════════
const OutroScene: React.FC<{ brandName: string; imageBase64?: string }> = ({ brandName, imageBase64 }) => {
    const frame = useCurrentFrame();
    const { durationInFrames } = useVideoConfig();
    const dimOverlay = interpolate(frame, [0, 60], [0, 0.3], { extrapolateRight: "clamp" });

    return (
        <AbsoluteFill>
            {imageBase64 ? (
                <ImageBackground base64Image={imageBase64} durationInFrames={durationInFrames} />
            ) : (
                <>
                    <AnimatedBackground hueOffset={240} />
                    <NoiseParticleField count={12} color="rgba(255, 200, 50, 0.08)" />
                </>
            )}
            <AbsoluteFill style={{ background: `rgba(0, 0, 0, ${dimOverlay})` }} />
            <ConvergingShapes accent={GOLD} startFrame={5} />
            <BrandFooter brandName={brandName} accent={GOLD} appearAt={10} />
        </AbsoluteFill>
    );
};

// ═════════════════════════════════════════════
// Main Composition
// ═════════════════════════════════════════════

const INTRO_FRAMES = 75;
const OUTRO_FRAMES = 75;
const TRANSITION_OVERLAP = 45;

export const FunFact: React.FC<FunFactProps> = ({
    factText,
    emoji,
    brandName,
    imageBase64,
    hookLine,
    sourceLabel,
}) => {
    const { width, height, durationInFrames } = useVideoConfig();

    const contentFrames = Math.max(
        durationInFrames - INTRO_FRAMES - OUTRO_FRAMES + TRANSITION_OVERLAP,
        210
    );

    return (
        <AbsoluteFill style={{ fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>
            <TransitionSeries>
                <TransitionSeries.Sequence durationInFrames={INTRO_FRAMES}>
                    <IntroScene emoji={emoji} imageBase64={imageBase64} />
                </TransitionSeries.Sequence>

                <TransitionSeries.Transition
                    presentation={slide({ direction: "from-bottom" })}
                    timing={springTiming({ config: { damping: 200 } })}
                />

                <TransitionSeries.Sequence durationInFrames={contentFrames}>
                    <ContentScene
                        factText={factText}
                        emoji={emoji}
                        imageBase64={imageBase64}
                        sourceLabel={sourceLabel}
                    />
                </TransitionSeries.Sequence>

                <TransitionSeries.Transition
                    presentation={clockWipe({ width, height })}
                    timing={linearTiming({ durationInFrames: 25 })}
                />

                <TransitionSeries.Sequence durationInFrames={OUTRO_FRAMES}>
                    <OutroScene brandName={brandName} imageBase64={imageBase64} />
                </TransitionSeries.Sequence>
            </TransitionSeries>
        </AbsoluteFill>
    );
};
