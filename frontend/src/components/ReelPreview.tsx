import React, { useState } from "react";
import { Play, Pause, RotateCcw, Volume2, VolumeX } from "lucide-react";
import type { VideoMetadata, SubtitleSegment, StyleSettings } from "../types/subtitle";
import { API_BASE_URL } from "../config";

interface ReelPreviewProps {
  metadata: VideoMetadata | null;
  segments: SubtitleSegment[];
  styleSettings: StyleSettings;
  currentTime: number;
  setCurrentTime: (t: number) => void;
  videoRef: React.RefObject<HTMLVideoElement | null>;
}

export const ReelPreview: React.FC<ReelPreviewProps> = ({
  metadata,
  segments,
  styleSettings,
  currentTime,
  setCurrentTime,
  videoRef,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);

  // Toggle play/pause
  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play();
      setIsPlaying(true);
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (videoRef.current) {
      videoRef.current.currentTime = time;
    }
  };

  // Find active segment
  const activeSegment = segments.find(
    (s) => currentTime >= s.start && currentTime <= s.end
  );

  // Format time mm:ss.d
  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const ms = Math.floor((sec % 1) * 10);
    return `${m}:${s < 10 ? "0" : ""}${s}.${ms}`;
  };

  // Aspect Ratio Dimensions for Preview Mockup
  const getContainerAspect = () => {
    if (styleSettings.aspect_ratio === "1:1") return "aspect-square max-w-[420px]";
    if (styleSettings.aspect_ratio === "16:9") return "aspect-video max-w-[620px]";
    return "aspect-[9/16] max-w-[340px]"; // 9:16 phone
  };

  // Subtitle Vertical Position
  const getSubtitlePositionStyle = () => {
    if (styleSettings.position === "top") return { top: "15%", transform: "translateX(-50%)" };
    if (styleSettings.position === "center") return { top: "50%", transform: "translate(-50%, -50%)" };
    return { bottom: "18%", transform: "translateX(-50%)" }; // Bottom Reels Safe Zone
  };

  return (
    <div className="flex flex-col items-center justify-center h-full p-4 select-none">
      {/* Phone/Frame Wrapper */}
      <div
        className={`relative w-full ${getContainerAspect()} bg-black rounded-3xl overflow-hidden shadow-2xl border-4 border-gray-800 flex items-center justify-center`}
      >
        {/* HTML5 Video Element */}
        {metadata ? (
          <video
            ref={videoRef}
            src={`${API_BASE_URL}${metadata.video_url}`}
            className="w-full h-full object-cover"
            onTimeUpdate={handleTimeUpdate}
            onEnded={() => setIsPlaying(false)}
            playsInline
            muted={isMuted}
          />
        ) : (
          <div className="text-center p-6 text-gray-500">
            <p className="text-sm font-medium">No Reel Loaded</p>
            <p className="text-xs mt-1">Upload a vertical video or load demo</p>
          </div>
        )}

        {/* Live Subtitle Overlay */}
        {metadata && activeSegment && (
          <div
            style={{
              ...getSubtitlePositionStyle(),
              fontFamily: styleSettings.font_name,
            }}
            className={`absolute left-1/2 w-[88%] text-center cursor-move transition-all duration-75 z-20 ${
              styleSettings.style_preset === "neon_box"
                ? "bg-black/75 px-4 py-2.5 rounded-2xl border border-white/10 shadow-lg"
                : ""
            }`}
          >
            <div
              className="font-bold leading-relaxed tracking-wide transition-all"
              style={{
                fontSize: `${Math.round(styleSettings.font_size * 0.28)}px`, // Scaled for preview
                color: styleSettings.primary_color,
                textShadow:
                  styleSettings.style_preset !== "neon_box"
                    ? `0 2px 4px ${styleSettings.outline_color}, 0 -2px 4px ${styleSettings.outline_color}, 2px 0 4px ${styleSettings.outline_color}, -2px 0 4px ${styleSettings.outline_color}`
                    : "none",
              }}
            >
              {/* Karaoke mode with word-level highlight */}
              {styleSettings.style_preset === "karaoke" &&
              activeSegment.words &&
              activeSegment.words.length > 0 ? (
                <div className="flex flex-wrap items-center justify-center gap-x-1.5 gap-y-1">
                  {activeSegment.words.map((w, wIdx) => {
                    const isWordActive =
                      currentTime >= w.start && currentTime <= w.end;
                    return (
                      <span
                        key={wIdx}
                        style={{
                          color: isWordActive
                            ? styleSettings.highlight_color
                            : styleSettings.primary_color,
                          transform: isWordActive ? "scale(1.08)" : "scale(1)",
                        }}
                        className={`inline-block transition-transform duration-100 ${
                          isWordActive ? "font-extrabold" : "font-normal opacity-90"
                        }`}
                      >
                        {w.text}
                      </span>
                    );
                  })}
                </div>
              ) : (
                <span>{activeSegment.text}</span>
              )}
            </div>
          </div>
        )}

        {/* 9:16 Safe Zone Guides (Overlay indicator) */}
        {metadata && styleSettings.aspect_ratio === "9:16" && (
          <div className="absolute inset-0 pointer-events-none border-dashed border-gray-700/40 rounded-2xl m-3 flex flex-col justify-between p-2">
            <span className="text-[10px] text-gray-500/60 text-right">TikTok Top Bar</span>
            <span className="text-[10px] text-gray-500/60 text-left">TikTok Safe Margin (Above Caption)</span>
          </div>
        )}
      </div>

      {/* Video Playback Controls Bar */}
      {metadata && (
        <div className="w-full max-w-md mt-4 bg-gray-900/80 backdrop-blur border border-gray-800 rounded-2xl p-3 flex flex-col gap-2">
          {/* Progress Slider */}
          <div className="flex items-center gap-3">
            <span className="text-[11px] font-mono text-gray-400 w-12 text-right">
              {formatTime(currentTime)}
            </span>
            <input
              type="range"
              min="0"
              max={metadata.duration || 10}
              step="0.05"
              value={currentTime}
              onChange={handleSeek}
              className="flex-1 accent-indigo-500 h-1.5 bg-gray-700 rounded-lg cursor-pointer"
            />
            <span className="text-[11px] font-mono text-gray-400 w-12">
              {formatTime(metadata.duration || 0)}
            </span>
          </div>

          {/* Buttons Row */}
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-2">
              <button
                onClick={togglePlay}
                className="w-8 h-8 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white flex items-center justify-center transition shadow-lg shadow-indigo-600/30"
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
              </button>
              <button
                onClick={() => {
                  if (videoRef.current) {
                    videoRef.current.currentTime = 0;
                    setCurrentTime(0);
                  }
                }}
                className="p-1.5 text-gray-400 hover:text-white transition"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsMuted(!isMuted)}
                className="p-1.5 text-gray-400 hover:text-white transition"
              >
                {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              </button>
            </div>

            <div className="text-xs text-gray-400 font-medium">
              {styleSettings.aspect_ratio} Mode
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
