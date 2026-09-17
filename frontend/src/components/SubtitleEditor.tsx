import React from "react";
import type { SubtitleSegment } from "../types/subtitle";
import { Play, Trash2, Globe, Plus, Scissors, PlusCircle } from "lucide-react";

interface SubtitleEditorProps {
  segments: SubtitleSegment[];
  setSegments: React.Dispatch<React.SetStateAction<SubtitleSegment[]>>;
  currentTime: number;
  onSeek: (time: number) => void;
}

export const SubtitleEditor: React.FC<SubtitleEditorProps> = ({
  segments,
  setSegments,
  currentTime,
  onSeek,
}) => {
  const handleTextChange = (id: number, newText: string) => {
    setSegments((prev) =>
      prev.map((s) => (s.id === id ? { ...s, text: newText } : s))
    );
  };

  const handleDelete = (id: number) => {
    setSegments((prev) => prev.filter((s) => s.id !== id));
  };

  const handleAdjustTime = (id: number, field: "start" | "end", delta: number) => {
    setSegments((prev) =>
      prev.map((s) => {
        if (s.id !== id) return s;
        let newStart = s.start;
        let newEnd = s.end;
        if (field === "start") {
          newStart = Math.max(0, Math.round((s.start + delta) * 10) / 10);
          if (newStart >= s.end) newStart = s.end - 0.2;
        } else {
          newEnd = Math.max(s.start + 0.2, Math.round((s.end + delta) * 10) / 10);
        }
        return { ...s, start: newStart, end: newEnd };
      })
    );
  };

  // Split a long subtitle segment into two segments (useful for long replies)
  const handleSplitSegment = (seg: SubtitleSegment) => {
    const duration = seg.end - seg.start;
    const midTime = Math.round((seg.start + duration / 2) * 10) / 10;
    
    // Attempt to split text cleanly by spaces/words if available
    const words = seg.text.trim().split(/\s+/);
    let part1Text = seg.text;
    let part2Text = "...";

    if (words.length >= 2) {
      const midWord = Math.ceil(words.length / 2);
      part1Text = words.slice(0, midWord).join(" ");
      part2Text = words.slice(midWord).join(" ");
    }

    const newId = Date.now() + Math.floor(Math.random() * 1000);
    const seg1: SubtitleSegment = {
      ...seg,
      end: midTime,
      text: part1Text
    };
    const seg2: SubtitleSegment = {
      id: newId,
      start: midTime,
      end: seg.end,
      text: part2Text,
      source_text: seg.source_text ? `(Part 2) ${seg.source_text}` : undefined,
      words: []
    };

    setSegments((prev) => {
      const idx = prev.findIndex((s) => s.id === seg.id);
      if (idx === -1) return [...prev, seg2];
      const copy = [...prev];
      copy.splice(idx, 1, seg1, seg2);
      return copy;
    });
  };

  // Insert a new subtitle right after the current one
  const handleInsertAfter = (seg: SubtitleSegment) => {
    const newStart = Math.round(seg.end * 10) / 10;
    const newEnd = Math.round((newStart + 2.0) * 10) / 10;
    const newId = Date.now() + Math.floor(Math.random() * 1000);

    const newSeg: SubtitleSegment = {
      id: newId,
      start: newStart,
      end: newEnd,
      text: "စကားပြောစာသားထည့်ပါ...",
      words: []
    };

    setSegments((prev) => {
      const idx = prev.findIndex((s) => s.id === seg.id);
      if (idx === -1) return [...prev, newSeg];
      const copy = [...prev];
      copy.splice(idx + 1, 0, newSeg);
      return copy;
    });
  };

  // Add subtitle at current video playback position
  const handleAddAtCurrentTime = () => {
    const start = Math.round(currentTime * 10) / 10;
    const end = Math.round((start + 2.0) * 10) / 10;
    const newId = Date.now() + Math.floor(Math.random() * 1000);

    const newSeg: SubtitleSegment = {
      id: newId,
      start,
      end,
      text: "စာသားထည့်ပါ...",
      words: []
    };

    setSegments((prev) => {
      const updated = [...prev, newSeg].sort((a, b) => a.start - b.start);
      return updated;
    });
  };

  const formatSec = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    const ms = Math.floor((s % 1) * 10);
    return `${m}:${sec < 10 ? "0" : ""}${sec}.${ms}`;
  };

  if (segments.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center text-gray-500 border-2 border-dashed border-gray-800 rounded-2xl p-6">
        <Globe className="w-8 h-8 text-gray-600 mb-2" />
        <p className="text-sm font-medium">No Subtitles Yet</p>
        <p className="text-xs mt-1 mb-4">Upload a video or YouTube Short, then click "Transcribe" or add manually.</p>
        <button
          onClick={handleAddAtCurrentTime}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-semibold transition"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>+ Add First Subtitle</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Editor Header Toolbar */}
      <div className="flex items-center justify-between px-1 pb-1 border-b border-gray-800/80">
        <span className="text-xs font-medium text-gray-400">
          Total: <strong className="text-white font-mono">{segments.length}</strong> segments
        </span>
        <button
          onClick={handleAddAtCurrentTime}
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-600/15 hover:bg-indigo-600/25 text-indigo-300 border border-indigo-500/30 text-[11px] font-semibold transition"
          title="Insert a new subtitle at current video playhead"
        >
          <PlusCircle className="w-3 h-3" />
          <span>+ Add Subtitle at {formatSec(currentTime)}</span>
        </button>
      </div>

      {/* Subtitles List */}
      <div className="space-y-3 overflow-y-auto max-h-[500px] pr-1">
        {segments.map((seg) => {
          const isActive = currentTime >= seg.start && currentTime <= seg.end;
          return (
            <div
              key={seg.id}
              className={`p-3 rounded-2xl border transition-all ${
                isActive
                  ? "bg-indigo-950/30 border-indigo-500/80 shadow-md shadow-indigo-900/20 ring-1 ring-indigo-500/30"
                  : "bg-gray-900/60 border-gray-800 hover:border-gray-700"
              }`}
            >
              {/* Top Timing & Action Bar */}
              <div className="flex items-center justify-between mb-2">
                {/* Seek & Play Timing Badge */}
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => onSeek(seg.start)}
                    className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-gray-800 hover:bg-indigo-600/30 text-[11px] font-mono text-gray-300 hover:text-indigo-300 transition"
                    title="Click to jump video to this segment"
                  >
                    <Play className="w-2.5 h-2.5 fill-current" />
                    <span>{formatSec(seg.start)} - {formatSec(seg.end)}</span>
                  </button>

                  {/* Fine-tune duration (+/- 0.5s) */}
                  <div className="flex items-center gap-0.5 ml-1 text-[10px] font-mono text-gray-400">
                    <button
                      onClick={() => handleAdjustTime(seg.id, "end", -0.5)}
                      className="px-1 py-0.5 rounded bg-gray-800/80 hover:bg-gray-700 hover:text-white transition"
                      title="Shorten duration by 0.5s"
                    >
                      -0.5s
                    </button>
                    <button
                      onClick={() => handleAdjustTime(seg.id, "end", 0.5)}
                      className="px-1 py-0.5 rounded bg-gray-800/80 hover:bg-gray-700 hover:text-white transition"
                      title="Extend duration by 0.5s"
                    >
                      +0.5s
                    </button>
                  </div>
                </div>

                {/* Split, Add Below & Delete Controls */}
                <div className="flex items-center gap-1">
                  {/* Split Long Segment Button */}
                  <button
                    onClick={() => handleSplitSegment(seg)}
                    className="flex items-center gap-1 px-1.5 py-0.5 rounded-lg bg-gray-800 hover:bg-amber-500/20 text-gray-400 hover:text-amber-300 border border-gray-700 text-[10px] transition"
                    title="Split long sentence into 2 separate segments"
                  >
                    <Scissors className="w-2.5 h-2.5" />
                    <span>Split</span>
                  </button>

                  {/* Insert Subtitle After */}
                  <button
                    onClick={() => handleInsertAfter(seg)}
                    className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-lg bg-gray-800 hover:bg-indigo-600/30 text-gray-400 hover:text-indigo-300 border border-gray-700 text-[10px] transition"
                    title="Insert a new subtitle right after this one"
                  >
                    <Plus className="w-2.5 h-2.5" />
                    <span>Add Next</span>
                  </button>

                  {/* Delete Segment */}
                  <button
                    onClick={() => handleDelete(seg.id)}
                    className="p-1 text-gray-500 hover:text-red-400 transition ml-0.5"
                    title="Delete segment"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Source Original Text (if translated) */}
              {seg.source_text && (
                <p className="text-[11px] text-gray-400 mb-1.5 italic font-sans px-1 truncate">
                  "{seg.source_text}"
                </p>
              )}

              {/* Multi-line Editable Subtitle Textarea (Optimal for long speaker replies & Burmese) */}
              <textarea
                rows={2}
                value={seg.text}
                onChange={(e) => handleTextChange(seg.id, e.target.value)}
                placeholder="Enter translated or transcribed subtitle..."
                className="w-full bg-gray-950 border border-gray-800 rounded-xl px-3 py-2 text-sm text-white font-medium focus:outline-none focus:border-indigo-500 transition resize-y leading-relaxed font-sans"
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};
