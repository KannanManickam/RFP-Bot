import React from "react";
import {
    AbsoluteFill,
    useCurrentFrame,
    useVideoConfig,
    interpolate,
    spring,
    Audio,
    staticFile,
} from "remotion";
import {
    TransitionSeries,
    linearTiming,
    springTiming,
} from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";
import { clockWipe } from "@remotion/transitions/clock-wipe";
import { whoosh } from "@remotion/sfx";
import { funFactSchema } from "./FunFact";
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
} from "./animations";

// Re-export the same schema
export { funFactSchema as funFactVerticalSchema };
type FunFactVerticalProps = z.infer<typeof funFactSchema>;

const GOLD = "#FFD700";
const TEXT_COLOR = "#F0E6D3";

// ── Vertical layout constants (9:16 safe zones) ──
const V_PADDING_TOP = 140;    // clear device top chrome
const V_PADDING_SIDE = 60;
const V_FONT_MAIN = 44;       // slightly larger for taller canvas
const V_FONT_HOOK = 34;

// Shapes spread a bit wider for vertical canvas
const INTRO_SHAPES = [
    { type: "star" as const, x: 8, y: 8, size: 36, color: GOLD, speed: 0.006, seed: "vis1", delay: 10 },
    { type: "circle" as const, x: 85, y: 10, size: 28, color: GOLD, speed: 0.007, seed: "vis2", delay: 18 },
    { type: "triangle" as const, x: 10, y: 88, size: 32, color: GOLD, speed: 0.005, seed: "vis3", delay: 25 },
    { type: "ring" as const, x: 88, y: 85, size: 30, color: GOLD, speed: 0.008, seed: "vis4", delay: 15 },
    { type: "star" as const, x: 50, y: 5, size: 24, color: GOLD, speed: 0.009, seed: "vis5", delay: 22 },
];
const CONTENT_SHAPES = [
    { type: "circle" as const, x: 5, y: 25, size: 22, color: `${GOLD}88`, speed: 0.005, seed: "vcs1", delay: 5 },
    { type: "star" as const, x: 92, y: 50, size: 26, color: `${GOLD}88`, speed: 0.006, seed: "vcs2", delay: 12 },
    { type: "ring" as const, x: 8, y: 75, size: 20, color: `${GOLD}88`, speed: 0.004, seed: "vcs3", delay: 8 },
    { type: "triangle" as const, x: 90, y: 88, size: 24, color: `${GOLD}88`, speed: 0.007, seed: "vcs4", delay: 15 },
];

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

// ── Image background ──
const ImageBackground: React.FC<{ base64Image: string; durationInFrames: number }> = ({ base64Image, durationInFrames }) => {
    const frame = useCurrentFrame();
    const scale = interpolate(frame, [0, durationInFrames], [1.0, 1.12], { extrapolateRight: "clamp" });
    return (
        <AbsoluteFill>
            <AbsoluteFill style={{ overflow: "hidden" }}>
                <img
                    src={base64Image}
                    style={{ width: "100%", height: "100%", objectFit: "cover", filter: "blur(8px)", transform: `scale(${scale})` }}
                />
            </AbsoluteFill>
            <AbsoluteFill style={{ backgroundColor: "rgba(0,0,0,0.52)" }} />
        </AbsoluteFill>
    );
};

// ═════════════════════════════════════════════
// Vertical IntroScene
// ═════════════════════════════════════════════
const IntroScene: React.FC<{ emoji: string; imageBase64?: string }> = ({ emoji, imageBase64 }) => {
    const frame = useCurrentFrame();
    const { fps, durationInFrames } = useVideoConfig();

    const titleProgress = spring({ frame: frame - 12, fps, config: { damping: 14, stiffness: 100, mass: 0.7 } });
    const titleY = interpolate(titleProgress, [0, 1], [50, 0]);
    const titleOp = interpolate(titleProgress, [0, 0.3, 1], [0, 0.5, 1]);

    // Static "Did you know?" teaser
    const teaseProgress = spring({ frame: frame - 36, fps, config: { damping: 18, stiffness: 100, mass: 0.8 } });
    const teaseOpacity = interpolate(teaseProgress, [0, 1], [0, 1]);
    const teaseY = interpolate(teaseProgress, [0, 1], [18, 0]);
    const hookWords: string[] = []; // unused, kept to avoid prop removal cascade

    return (
        <AbsoluteFill>
            {imageBase64
                ? <ImageBackground base64Image={imageBase64} durationInFrames={durationInFrames} />
                : <><AnimatedBackground /><NoiseParticleField count={20} color="rgba(255,200,50,0.12)" /></>
            }
            <DecorativeShapes shapes={INTRO_SHAPES} />
            <Audio src={whoosh} startFrom={0} volume={0.3} />

            <div style={{
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                height: "100%", gap: 24, position: "relative", zIndex: 1,
                paddingTop: V_PADDING_TOP, paddingLeft: V_PADDING_SIDE, paddingRight: V_PADDING_SIDE,
            }}>
                <div style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <PulseGlow color={GOLD} size={280} />
                    <FloatingElement seed="emoji-v-intro" amplitudeX={5} amplitudeY={8}>
                        <ScalePopIn delay={0} rotationDeg={15}>
                            <div style={{ fontSize: 130, filter: "drop-shadow(0 6px 30px rgba(255,200,50,0.5))" }}>
                                {emoji}
                            </div>
                        </ScalePopIn>
                    </FloatingElement>
                </div>

                <div style={{
                    fontSize: 60, fontWeight: 800, color: GOLD, letterSpacing: 6,
                    textTransform: "uppercase", opacity: titleOp,
                    transform: `translateY(${titleY}px)`,
                    textShadow: "0 3px 25px rgba(255,215,0,0.4)",
                    fontFamily: "'Inter','Segoe UI',sans-serif",
                }}>Fun Fact</div>

                <AnimatedDivider startFrame={18} width={360} color={GOLD} duration={30} />

                {/* Static teaser — "Did you know?" */}
                <div style={{
                    fontSize: V_FONT_HOOK,
                    fontWeight: 400,
                    color: TEXT_COLOR,
                    fontFamily: "'Inter','Segoe UI',sans-serif",
                    fontStyle: "italic",
                    opacity: teaseOpacity,
                    transform: `translateY(${teaseY}px)`,
                    textShadow: "0 1px 8px rgba(0,0,0,0.5)",
                    letterSpacing: 1,
                }}>
                    Did you know?
                </div>
            </div>
        </AbsoluteFill>
    );
};

// ═════════════════════════════════════════════
// Vertical ContentScene
// ═════════════════════════════════════════════
const ContentScene: React.FC<{ factText: string; emoji: string; imageBase64?: string; sourceLabel?: string }> = ({
    factText, emoji, imageBase64, sourceLabel,
}) => {
    const frame = useCurrentFrame();
    const { fps, durationInFrames } = useVideoConfig();

    const miniEmojiOp = spring({ frame: frame - 5, fps, config: { damping: 20, stiffness: 120 } });
    const KARAOKE_START = 15;

    return (
        <AbsoluteFill>
            {imageBase64
                ? <ImageBackground base64Image={imageBase64} durationInFrames={durationInFrames} />
                : <><AnimatedBackground hueOffset={120} /><NoiseParticleField count={18} color="rgba(255,200,50,0.1)" baseSpeed={0.006} /></>
            }
            <DecorativeShapes shapes={CONTENT_SHAPES} />

            <ZoomPunch delay={0}>
                <div style={{ display: "flex", flexDirection: "column", height: "100%", position: "relative", zIndex: 1 }}>
                    {/* Header */}
                    <div style={{
                        display: "flex", alignItems: "center", gap: 12,
                        padding: `${V_PADDING_TOP}px ${V_PADDING_SIDE}px 0`,
                        opacity: miniEmojiOp,
                    }}>
                        <span style={{ fontSize: 44 }}>{emoji}</span>
                        <span style={{
                            fontSize: 22, color: GOLD, fontWeight: 700, letterSpacing: 3,
                            textTransform: "uppercase", fontFamily: "'Inter','Segoe UI',sans-serif",
                        }}>Fun Fact</span>
                        <div style={{ flex: 1, height: 1, background: `linear-gradient(90deg,${GOLD}44,transparent)`, marginLeft: 10 }} />
                    </div>

                    {/* Karaoke text */}
                    <KaraokeLine
                        text={factText}
                        startFrame={KARAOKE_START}
                        framesPerWord={8}
                        fontSize={V_FONT_MAIN}
                        dimColor="rgba(240,230,211,0.28)"
                        accent={GOLD}
                        maxCharsPerLine={30}
                    />
                </div>
            </ZoomPunch>

            <ParticleBurst triggerFrame={KARAOKE_START} color={GOLD} count={18} />
            {sourceLabel && <SourceBadge label={sourceLabel} appearAt={KARAOKE_START + 10} accent={GOLD} />}
        </AbsoluteFill>
    );
};

// ═════════════════════════════════════════════
// Vertical OutroScene
// ═════════════════════════════════════════════
const OutroScene: React.FC<{ brandName: string; imageBase64?: string }> = ({ brandName, imageBase64 }) => {
    const frame = useCurrentFrame();
    const { durationInFrames } = useVideoConfig();
    const dimOverlay = interpolate(frame, [0, 60], [0, 0.3], { extrapolateRight: "clamp" });

    return (
        <AbsoluteFill>
            {imageBase64
                ? <ImageBackground base64Image={imageBase64} durationInFrames={durationInFrames} />
                : <><AnimatedBackground hueOffset={240} /><NoiseParticleField count={12} color="rgba(255,200,50,0.08)" /></>
            }
            <AbsoluteFill style={{ background: `rgba(0,0,0,${dimOverlay})` }} />
            <ConvergingShapes accent={GOLD} startFrame={5} />
            <BrandFooter brandName={brandName} accent={GOLD} appearAt={10} />
        </AbsoluteFill>
    );
};

// ═════════════════════════════════════════════
// Main Vertical Composition
// ═════════════════════════════════════════════
const INTRO_FRAMES = 75;
const OUTRO_FRAMES = 75;
const TRANSITION_OVERLAP = 45;

export const FunFactVertical: React.FC<FunFactVerticalProps> = ({
    factText, emoji, brandName, imageBase64, hookLine, sourceLabel,
}) => {
    const { width, height } = useVideoConfig();
    const { durationInFrames } = useVideoConfig();

    const contentFrames = Math.max(
        durationInFrames - INTRO_FRAMES - OUTRO_FRAMES + TRANSITION_OVERLAP,
        210
    );

    return (
        <AbsoluteFill style={{ fontFamily: "'Inter','Segoe UI',sans-serif" }}>
            <TransitionSeries>
                <TransitionSeries.Sequence durationInFrames={INTRO_FRAMES}>
                    <IntroScene emoji={emoji} imageBase64={imageBase64} />
                </TransitionSeries.Sequence>

                <TransitionSeries.Transition
                    presentation={slide({ direction: "from-bottom" })}
                    timing={springTiming({ config: { damping: 200 } })}
                />

                <TransitionSeries.Sequence durationInFrames={contentFrames}>
                    <ContentScene factText={factText} emoji={emoji} imageBase64={imageBase64} sourceLabel={sourceLabel} />
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
