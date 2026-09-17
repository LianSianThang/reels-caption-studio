import React from "react";
import type { StyleSettings } from "../types/subtitle";
import { Type, Sparkles, LayoutTemplate, Palette, AlignVerticalJustifyCenter } from "lucide-react";

interface StyleToolbarProps {
  styleSettings: StyleSettings;
  setStyleSettings: React.Dispatch<React.SetStateAction<StyleSettings>>;
}

export const StyleToolbar: React.FC<StyleToolbarProps> = ({
  styleSettings,
  setStyleSettings,
}) => {
  const updateStyle = (key: keyof StyleSettings, val: any) => {
    setStyleSettings((prev) => ({ ...prev, [key]: val }));
  };

  const PRESET_HIGHLIGHT_COLORS = [
    { name: "Neon Gold", hex: "#FFDD00" },
    { name: "Cyber Green", hex: "#00FF66" },
    { name: "Sky Cyan", hex: "#00E5FF" },
    { name: "TikTok Coral", hex: "#FF3366" },
    { name: "Clean White", hex: "#FFFFFF" },
  ];

  return (
    <div className="space-y-6 text-sm">
      {/* Aspect Ratio Switcher */}
      <div>
        <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1.5 mb-2.5">
          <LayoutTemplate className="w-3.5 h-3.5 text-indigo-400" />
          Format Preset
        </label>
        <div className="grid grid-cols-3 gap-2">
          {(["9:16", "1:1", "16:9"] as const).map((ratio) => (
            <button
              key={ratio}
              onClick={() => updateStyle("aspect_ratio", ratio)}
              className={`py-2 px-3 rounded-xl font-medium text-xs border transition flex flex-col items-center gap-1 ${
                styleSettings.aspect_ratio === ratio
                  ? "bg-indigo-600/20 border-indigo-500 text-indigo-300 shadow-md shadow-indigo-600/10"
                  : "bg-gray-900 border-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              <span className="font-bold">{ratio}</span>
              <span className="text-[10px] text-gray-500">
                {ratio === "9:16" ? "Reels/TikTok" : ratio === "1:1" ? "Square" : "Landscape"}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Animation & Preset Style */}
      <div>
        <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1.5 mb-2.5">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          Caption Style
        </label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { id: "karaoke", label: "Karaoke", desc: "Active word pop" },
            { id: "neon_box", label: "Neon Box", desc: "Pill background" },
            { id: "minimal", label: "Minimal", desc: "Subtle shadow" },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => updateStyle("style_preset", item.id)}
              className={`p-2.5 rounded-xl border text-left transition ${
                styleSettings.style_preset === item.id
                  ? "bg-indigo-600/20 border-indigo-500 text-white"
                  : "bg-gray-900 border-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              <div className="font-semibold text-xs">{item.label}</div>
              <div className="text-[10px] text-gray-500">{item.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Active Word Highlight Color */}
      <div>
        <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1.5 mb-2.5">
          <Palette className="w-3.5 h-3.5 text-emerald-400" />
          Active Word Color
        </label>
        <div className="flex items-center gap-3">
          {PRESET_HIGHLIGHT_COLORS.map((col) => (
            <button
              key={col.hex}
              onClick={() => updateStyle("highlight_color", col.hex)}
              style={{ backgroundColor: col.hex }}
              title={col.name}
              className={`w-7 h-7 rounded-full transition transform hover:scale-110 shadow-md ${
                styleSettings.highlight_color.toLowerCase() === col.hex.toLowerCase()
                  ? "ring-2 ring-white ring-offset-2 ring-offset-gray-900 scale-110"
                  : "opacity-80"
              }`}
            />
          ))}
        </div>
      </div>

      {/* Typography: Font Family & Size */}
      <div className="space-y-3">
        <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
          <Type className="w-3.5 h-3.5 text-blue-400" />
          Typography
        </label>

        <div>
          <span className="text-xs text-gray-400 block mb-1">Font Family</span>
          <select
            value={styleSettings.font_name}
            onChange={(e) => updateStyle("font_name", e.target.value)}
            className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 cursor-pointer"
          >
            <option value="Myanmar Text">Myanmar Text (Recommended for Burmese)</option>
            <option value="Noto Sans Myanmar">Noto Sans Myanmar</option>
            <option value="Impact">Impact / Bold</option>
            <option value="Arial">Arial Black</option>
            <option value="Montserrat">Montserrat</option>
          </select>
        </div>

        <div>
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>Font Size</span>
            <span className="font-mono text-white">{styleSettings.font_size}px</span>
          </div>
          <input
            type="range"
            min="40"
            max="110"
            value={styleSettings.font_size}
            onChange={(e) => updateStyle("font_size", parseInt(e.target.value))}
            className="w-full accent-indigo-500 h-1.5 bg-gray-800 rounded-lg cursor-pointer"
          />
        </div>
      </div>

      {/* Vertical Position */}
      <div>
        <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1.5 mb-2.5">
          <AlignVerticalJustifyCenter className="w-3.5 h-3.5 text-purple-400" />
          Vertical Position
        </label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { id: "bottom", label: "Bottom", desc: "Reels Safe Zone" },
            { id: "center", label: "Center", desc: "Hook Center" },
            { id: "top", label: "Top", desc: "Reaction Top" },
          ].map((pos) => (
            <button
              key={pos.id}
              onClick={() => updateStyle("position", pos.id)}
              className={`p-2 rounded-xl border text-center transition ${
                styleSettings.position === pos.id
                  ? "bg-indigo-600/20 border-indigo-500 text-white"
                  : "bg-gray-900 border-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              <div className="font-semibold text-xs">{pos.label}</div>
              <div className="text-[9px] text-gray-500">{pos.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
