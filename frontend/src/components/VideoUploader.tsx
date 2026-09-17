import React, { useState } from "react";
import { UploadCloud, Loader2, ArrowRight, AlertCircle } from "lucide-react";
import type { VideoMetadata } from "../types/subtitle";

const YoutubeIcon = ({ className = "w-4 h-4" }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
);

interface VideoUploaderProps {
  onUploadSuccess: (meta: VideoMetadata) => void;
  isUploading: boolean;
  setIsUploading: (val: boolean) => void;
}

export const VideoUploader: React.FC<VideoUploaderProps> = ({
  onUploadSuccess,
  isUploading,
  setIsUploading,
}) => {
  const [activeTab, setActiveTab] = useState<"file" | "youtube">("file");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getAuthHeader = (): Record<string, string> => {
    const token = localStorage.getItem("reel_user_token");
    return token ? { "Authorization": `Bearer ${token}` } : {};
  };

  const handleFile = async (file: File) => {
    setError(null);
    setIsUploading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        headers: getAuthHeader(),
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Upload failed");
      }

      const meta: VideoMetadata = await res.json();
      onUploadSuccess(meta);
    } catch (err: any) {
      setError(err.message || "Failed to upload video");
    } finally {
      setIsUploading(false);
    }
  };

  const handleYoutubeImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!youtubeUrl.trim()) return;

    setError(null);
    setIsUploading(true);

    try {
      const res = await fetch("/api/import-youtube", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader()
        },
        body: JSON.stringify({ url: youtubeUrl.trim() }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to download YouTube Short");
      }

      onUploadSuccess(data);
      setYoutubeUrl("");
    } catch (err: any) {
      setError(err.message || "Failed to import video from YouTube");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="w-full space-y-3">
      {/* Sub-Tabs: Upload File vs YouTube Link */}
      <div className="flex items-center gap-2 bg-gray-950 p-1 rounded-2xl border border-gray-800">
        <button
          type="button"
          onClick={() => { setActiveTab("file"); setError(null); }}
          className={`flex-1 py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition ${
            activeTab === "file"
              ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
              : "text-gray-400 hover:text-white"
          }`}
        >
          <UploadCloud className="w-3.5 h-3.5" />
          <span>Upload File</span>
        </button>

        <button
          type="button"
          onClick={() => { setActiveTab("youtube"); setError(null); }}
          className={`flex-1 py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition ${
            activeTab === "youtube"
              ? "bg-red-600 text-white shadow-md shadow-red-600/30"
              : "text-gray-400 hover:text-white"
          }`}
        >
          <YoutubeIcon className="w-3.5 h-3.5" />
          <span>YouTube / Shorts Link</span>
        </button>
      </div>

      {activeTab === "file" ? (
        /* Tab 1: Drag & Drop File */
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`relative border-2 border-dashed rounded-3xl p-7 text-center transition-all cursor-pointer ${
            dragOver
              ? "border-indigo-500 bg-indigo-500/10"
              : "border-gray-800 bg-gray-900/40 hover:border-gray-700 hover:bg-gray-900/60"
          }`}
          onClick={() => {
            const input = document.createElement("input");
            input.type = "file";
            input.accept = "video/mp4,video/quicktime,video/webm";
            input.onchange = (e: any) => {
              if (e.target.files && e.target.files[0]) {
                handleFile(e.target.files[0]);
              }
            };
            input.click();
          }}
        >
          <div className="flex flex-col items-center justify-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              {isUploading ? (
                <Loader2 className="w-6 h-6 animate-spin" />
              ) : (
                <UploadCloud className="w-6 h-6" />
              )}
            </div>

            <div>
              <h3 className="font-semibold text-white text-sm">
                {isUploading ? "Uploading & Probing Video..." : "Upload Reel / TikTok / Short"}
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">
                Drag & drop 9:16 vertical video (MP4, MOV, WebM)
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-gray-800 text-gray-400 font-mono">
                9:16 Vertical
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-gray-800 text-gray-400 font-mono">
                Max 200MB
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-300 font-mono border border-blue-500/20">
                3-Day Retention
              </span>
            </div>
          </div>
        </div>
      ) : (
        /* Tab 2: Paste YouTube / Shorts Link */
        <form onSubmit={handleYoutubeImport} className="border border-gray-800 bg-gray-900/40 rounded-3xl p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-9 h-9 rounded-xl bg-red-600/20 border border-red-500/30 flex items-center justify-center text-red-400">
              <YoutubeIcon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-white text-sm">Paste YouTube or Shorts Link</h3>
              <p className="text-[11px] text-gray-400">
                We download the Short to the server, subtitle it, and prepare your download.
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-2 mt-4">
            <input
              type="url"
              required
              disabled={isUploading}
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              placeholder="https://www.youtube.com/shorts/..."
              className="flex-1 bg-gray-950 border border-gray-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-red-500 font-mono"
            />
            <button
              type="submit"
              disabled={isUploading || !youtubeUrl.trim()}
              className="px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-semibold text-xs flex items-center justify-center gap-2 transition disabled:opacity-50 shadow-lg shadow-red-600/25 shrink-0"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Fetching Short...</span>
                </>
              ) : (
                <>
                  <span>Import & Subtitle</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>

          <div className="flex items-center justify-between text-[11px] text-gray-500 mt-3 pt-3 border-t border-gray-800/80">
            <span>Supports YouTube Shorts, youtu.be, and regular links (Up to 5 mins max)</span>
            <span className="text-blue-400 font-mono">Auto-purged in 3 days</span>
          </div>
        </form>
      )}

      {error && (
        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};
