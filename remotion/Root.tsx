import React from "react";
import { Composition } from "remotion";
import { FunFact, funFactSchema } from "./compositions/FunFact";
import { OnDemandVideo, onDemandSchema } from "./compositions/OnDemandVideo";

// ── Duration helpers ──

const INTRO_FRAMES = 75;    // 2.5s
const OUTRO_FRAMES = 75;    // 2.5s
const TRANSITION_OVERLAP = 45; // transitions cause sequences to overlap
const MIN_CONTENT_FRAMES = 210; // 7s minimum
const FPS = 30;

/**
 * Calculate content scene duration for SplitLineReveal (FunFact).
 * Speed: ~12 frames per line, max 40 chars per line, + 30-frame start delay.
 */
const funFactContentFrames = (text: string, maxCharsPerLine = 40): number => {
    const words = text.split(" ");
    let lines = 0;
    let currentLine = "";
    for (const word of words) {
        if ((currentLine + " " + word).trim().length > maxCharsPerLine && currentLine) {
            lines++;
            currentLine = word;
        } else {
            currentLine = currentLine ? currentLine + " " + word : word;
        }
    }
    if (currentLine.trim()) lines++;

    const needed = lines * 12 + 30;
    return Math.max(needed, MIN_CONTENT_FRAMES);
};

/**
 * Calculate content scene duration for SplitLineReveal (OnDemandVideo).
 * Speed: ~10 frames per line, max 38 chars per line, + 30-frame start delay.
 */
const onDemandContentFrames = (text: string, maxCharsPerLine = 38): number => {
    const words = text.split(" ");
    let lines = 0;
    let currentLine = "";
    for (const word of words) {
        if ((currentLine + " " + word).trim().length > maxCharsPerLine && currentLine) {
            lines++;
            currentLine = word;
        } else {
            currentLine = currentLine ? currentLine + " " + word : word;
        }
    }
    if (currentLine.trim()) lines++;

    const needed = lines * 10 + 30;
    return Math.max(needed, MIN_CONTENT_FRAMES);
};

export const RemotionRoot: React.FC = () => {
    return (
        <>
            {/* Fun Fact — daily job animated video */}
            <Composition
                id="FunFact"
                component={FunFact}
                durationInFrames={360}
                fps={FPS}
                width={1080}
                height={1080}
                schema={funFactSchema}
                defaultProps={{
                    factText:
                        "The shortest war in history lasted just 38 minutes — between Britain and Zanzibar on August 27, 1896. Zanzibar surrendered after the British bombarded the palace. ⚔️",
                    emoji: "🧠",
                    brandName: "Sparktoship",
                }}
                calculateMetadata={({ props }) => {
                    const contentFrames = funFactContentFrames(props.factText);
                    return {
                        durationInFrames:
                            INTRO_FRAMES + contentFrames + OUTRO_FRAMES - TRANSITION_OVERLAP,
                    };
                }}
            />

            {/* On-demand video — /video command */}
            <Composition
                id="OnDemandVideo"
                component={OnDemandVideo}
                durationInFrames={360}
                fps={FPS}
                width={1080}
                height={1080}
                schema={onDemandSchema}
                defaultProps={{
                    title: "Did You Know?",
                    content:
                        "Octopuses have three hearts, nine brains, and blue blood. Two hearts pump blood to the gills, while the third pumps it to the rest of the body.",
                    emoji: "🐙",
                    brandName: "Sparktoship",
                    style: "facts" as const,
                }}
                calculateMetadata={({ props }) => {
                    const contentFrames = onDemandContentFrames(props.content);
                    return {
                        durationInFrames:
                            INTRO_FRAMES + contentFrames + OUTRO_FRAMES - TRANSITION_OVERLAP,
                    };
                }}
            />
        </>
    );
};
