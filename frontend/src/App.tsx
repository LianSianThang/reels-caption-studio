import { useState, useRef, useEffect } from "react";
import { Navbar } from "./components/Navbar";
import { VideoUploader } from "./components/VideoUploader";
import { ReelPreview } from "./components/ReelPreview";
import { StyleToolbar } from "./components/StyleToolbar";
import { SubtitleEditor } from "./components/SubtitleEditor";
import { ExportModal } from "./components/ExportModal";
import { AuthModal } from "./components/auth/AuthModal";
import { AdminLoginModal } from "./components/admin/AdminLoginModal";
import { AdminDashboard } from "./components/admin/AdminDashboard";
import type { VideoMetadata, SubtitleSegment, StyleSettings } from "./types/subtitle";
import { Sparkles, Mic, Globe, Film, PlayCircle, Loader2, Trash2 } from "lucide-react";
import { API_BASE_URL } from "./config";

export function App() {

  // Authentication State
  const [user, setUser] = useState<any>(null);
  const [adminUser, setAdminUser] = useState<any>(null);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [isAdminLoginOpen, setIsAdminLoginOpen] = useState(false);
  const [isAdminDashboardOpen, setIsAdminDashboardOpen] = useState(false);

  // Video & Editor State
  const [metadata, setMetadata] = useState<VideoMetadata | null>(null);
  const [segments, setSegments] = useState<SubtitleSegment[]>([]);
  const [targetLanguage, setTargetLanguage] = useState("Burmese");
  const [userQuota, setUserQuota] = useState<{ used: number; limit: number; remaining: number; is_admin: boolean } | null>(null);
  
  const [styleSettings, setStyleSettings] = useState<StyleSettings>({
    aspect_ratio: "9:16",
    font_name: "Myanmar Text",
    font_size: 70,
    primary_color: "#FFFFFF",
    highlight_color: "#FFDD00",
    outline_color: "#000000",
    bg_color: "#000000",
    style_preset: "karaoke",
    position: "bottom",
  });

  const [currentTime, setCurrentTime] = useState(0);
  const [activeTab, setActiveTab] = useState<"style" | "subtitles">("style");
  
  // Loading states
  const [isUploading, setIsUploading] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");

  // Export
  const [exportUrls, setExportUrls] = useState<{
    video_url: string;
    download_url: string;
    srt_url: string;
    ass_url: string;
  } | null>(null);
  const [isExportOpen, setIsExportOpen] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);

  const fetchUserQuota = async () => {
    const token = localStorage.getItem("reel_user_token");
    if (!token) {
      setUserQuota(null);
      return;
    }
    try {
      const res = await fetch("/api/user/quota", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUserQuota(data);
      }
    } catch {}
  };

  // Initialize Session (Auto restore User and Admin sessions)
  useEffect(() => {
    // 1. Restore User session
    const userToken = localStorage.getItem("reel_user_token");
    if (userToken) {
      fetch("/api/auth/me", {
        headers: { "Authorization": `Bearer ${userToken}` }
      })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) {
          setUser(data);
          fetchUserQuota();
        }
      })
      .catch(() => {});
    }

    // 2. Restore Admin session
    const adminToken = localStorage.getItem("reel_admin_token");
    if (adminToken) {
      fetch("/api/admin/stats", {
        headers: { "Authorization": `Bearer ${adminToken}` }
      })
      .then((res) => {
        if (res.ok) {
          setAdminUser({ email: "admin@reels.ai", role: "admin" });
        }
      })
      .catch(() => {});
    }

    // Check if ?admin=true is present in URL
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("admin") === "true" || window.location.pathname.startsWith("/admin")) {
      if (adminToken) {
        setIsAdminDashboardOpen(true);
      } else {
        setIsAdminLoginOpen(true);
      }
    }
  }, []);

  const getAuthHeader = (): Record<string, string> => {
    const token = localStorage.getItem("reel_user_token");
    return token ? { "Authorization": `Bearer ${token}` } : {};
  };

  const parseErrorResponse = async (res: Response, defaultMsg: string): Promise<string> => {
    try {
      const data = await res.json();
      return data.detail || data.message || defaultMsg;
    } catch {
      try {
        const text = await res.text();
        return text || defaultMsg;
      } catch {
        return defaultMsg;
      }
    }
  };

  const handleDeleteCurrentVideo = async () => {
    if (!metadata) return;
    if (metadata.video_id !== "demo_reel") {
      const confirmDelete = window.confirm("Delete this video from the server to free storage space?");
      if (!confirmDelete) return;
      try {
        await fetch(`${API_BASE_URL}/api/video/${metadata.video_id}`, {
          method: "DELETE",
          headers: getAuthHeader(),
        });
      } catch (e) {
        console.error("Failed to delete video:", e);
      }
    }
    setMetadata(null);
    setSegments([]);
  };

  // Load Pre-generated Demo Reel

  const handleLoadDemo = async () => {
    try {
      setStatusMsg("Loading demo vertical reel...");
      const res = await fetch("/api/demo");
      if (!res.ok) {
        const errMsg = await parseErrorResponse(res, "Could not load demo");
        throw new Error(errMsg);
      }
      const data: VideoMetadata = await res.json();
      setMetadata(data);
      setStyleSettings((prev) => ({ ...prev, aspect_ratio: data.aspect_ratio }));
      
      // Auto transcribe demo
      await triggerTranscribe(data.video_id);
    } catch (err: any) {
      alert(err.message || "Failed to load demo");
    } finally {
      setStatusMsg("");
    }
  };

  // 1. Transcribe STT
  const triggerTranscribe = async (videoId?: string) => {
    const vid = videoId || metadata?.video_id;
    if (!vid) return;

    // Must be logged in to transcribe
    if (!user) {
      setIsAuthOpen(true);
      alert("Please sign in or create a free account to transcribe videos. (You get 3 free videos every day!)");
      return;
    }

    // Daily rate limiting check (3 videos/day for regular users)
    if (userQuota && !userQuota.is_admin && userQuota.remaining <= 0) {
      alert("Daily quota reached (3/3 videos used today). Regular accounts are limited to 3 videos per day. Please come back tomorrow!");
      return;
    }

    setIsTranscribing(true);
    setStatusMsg("Transcribing speech with word timestamps (0MB server RAM)...");

    try {
      const headers: Record<string, string> = { 
        "Content-Type": "application/json",
        ...getAuthHeader()
      };

      const res = await fetch("/api/transcribe", {
        method: "POST",
        headers,
        body: JSON.stringify({ video_id: vid }),
      });

      if (!res.ok) {
        const errMsg = await parseErrorResponse(res, "Transcription failed");
        throw new Error(errMsg);
      }

      const data = await res.json();
      setSegments(data.segments);
      setActiveTab("subtitles");
      setStatusMsg("Transcription complete!");
      // Refresh user daily quota count
      fetchUserQuota();
    } catch (err: any) {
      alert(`Transcription error: ${err.message}`);
    } finally {
      setIsTranscribing(false);
    }
  };

  // 2. Translate LLM
  const triggerTranslate = async () => {
    if (segments.length === 0) return;

    // Must be logged in to translate
    if (!user) {
      setIsAuthOpen(true);
      alert("Please sign in or create a free account to translate subtitles.");
      return;
    }

    setIsTranslating(true);
    setStatusMsg(`Translating naturally to ${targetLanguage} (Colloquial Reel style)...`);

    try {
      const headers: Record<string, string> = { 
        "Content-Type": "application/json",
        ...getAuthHeader()
      };

      const res = await fetch("/api/translate", {
        method: "POST",
        headers,
        body: JSON.stringify({
          segments,
          target_language: targetLanguage,
        }),
      });

      if (!res.ok) {
        const errMsg = await parseErrorResponse(res, "Translation failed");
        throw new Error(errMsg);
      }

      const data = await res.json();
      setSegments(data.segments);
      setStatusMsg("Translation complete!");
    } catch (err: any) {
      alert(`Translation error: ${err.message}`);
    } finally {
      setIsTranslating(false);
    }
  };

  // 3. Burn & Export
  const triggerRender = async () => {
    if (!metadata || segments.length === 0) return;

    setIsRendering(true);
    setStatusMsg("Burning styled subtitles into video with FFmpeg & HarfBuzz...");

    try {
      const res = await fetch("/api/render", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          ...getAuthHeader()
        },
        body: JSON.stringify({
          video_id: metadata.video_id,
          segments,
          aspect_ratio: styleSettings.aspect_ratio,
          font_name: styleSettings.font_name,
          font_size: styleSettings.font_size,
          primary_color: styleSettings.primary_color,
          highlight_color: styleSettings.highlight_color,
          outline_color: styleSettings.outline_color,
          bg_color: styleSettings.bg_color,
          style_preset: styleSettings.style_preset,
          position: styleSettings.position,
        }),
      });

      if (!res.ok) {
        const errMsg = await parseErrorResponse(res, "Rendering failed");
        throw new Error(errMsg);
      }

      const data = await res.json();
      setExportUrls(data);
      setIsExportOpen(true);
      setStatusMsg("Burn ready!");
    } catch (err: any) {
      alert(`Burn error: ${err.message}`);
    } finally {
      setIsRendering(false);
    }
  };

  const handleLogoutUser = () => {
    localStorage.removeItem("reel_user_token");
    setUser(null);
    setUserQuota(null);
  };

  const handleLogoutAdmin = () => {
    localStorage.removeItem("reel_admin_token");
    setAdminUser(null);
    setIsAdminDashboardOpen(false);
  };

  return (
    <div className="min-h-screen bg-[#090C10] text-gray-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <Navbar
        targetLanguage={targetLanguage}
        setTargetLanguage={setTargetLanguage}
        user={user}
        userQuota={userQuota}
        onOpenAuth={() => setIsAuthOpen(true)}
        onLogoutUser={handleLogoutUser}
        adminUser={adminUser}
        onOpenAdminLogin={() => setIsAdminLoginOpen(true)}
        onOpenAdminDashboard={() => setIsAdminDashboardOpen(true)}
      />

      {/* Main Studio Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Live Video & Karaoke Subtitle Preview */}
        <section className="lg:col-span-5 xl:col-span-5 flex flex-col items-center justify-center bg-[#0F131D]/80 border border-gray-800 rounded-3xl p-4 shadow-xl">
          <ReelPreview
            metadata={metadata}
            segments={segments}
            styleSettings={styleSettings}
            currentTime={currentTime}
            setCurrentTime={setCurrentTime}
            videoRef={videoRef}
          />
        </section>

        {/* Right Column: Workflow Pipeline & Controls */}
        <section className="lg:col-span-7 xl:col-span-7 flex flex-col gap-5">
          {/* Video Status & Action Bar */}
          <div className="bg-[#121622] border border-gray-800 rounded-3xl p-5 shadow-lg">
            {!metadata ? (
              <div className="space-y-4">
                <VideoUploader
                  onUploadSuccess={(meta) => {
                    setMetadata(meta);
                    setStyleSettings((prev) => ({ ...prev, aspect_ratio: meta.aspect_ratio }));
                    setSegments([]);
                  }}
                  isUploading={isUploading}
                  setIsUploading={setIsUploading}
                  onRequireAuth={() => setIsAuthOpen(true)}
                />
                
                <div className="text-center">
                  <span className="text-xs text-gray-500">OR</span>
                  <div className="mt-2">
                    <button
                      onClick={handleLoadDemo}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-semibold transition"
                    >
                      <PlayCircle className="w-4 h-4" />
                      <span>Load Sample 9:16 Reel ("I went to Yangon...")</span>
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {/* File Header */}
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-white text-sm truncate max-w-xs">
                      {metadata.filename}
                    </h3>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {metadata.width}x{metadata.height} • {metadata.duration.toFixed(1)}s • {metadata.aspect_ratio}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    {metadata.video_id !== "demo_reel" && (
                      <button
                        onClick={handleDeleteCurrentVideo}
                        title="Delete video and purge files from server"
                        className="text-xs text-rose-400 hover:text-rose-300 px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 flex items-center gap-1.5 transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>Delete Reel</span>
                      </button>
                    )}
                    <button
                      onClick={() => {
                        setMetadata(null);
                        setSegments([]);
                      }}
                      className="text-xs text-gray-400 hover:text-white px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 transition"
                    >
                      Close Video
                    </button>
                  </div>
                </div>


                {/* 3 Step Action Workflow Buttons */}
                <div className="grid grid-cols-3 gap-3 pt-1">
                  {/* Step 1: Transcribe */}
                  <button
                    onClick={() => triggerTranscribe()}
                    disabled={isTranscribing}
                    className="flex flex-col items-center justify-center p-3 rounded-2xl bg-gray-900 border border-gray-800 hover:border-indigo-500 text-white transition disabled:opacity-50"
                  >
                    {isTranscribing ? (
                      <Loader2 className="w-5 h-5 text-indigo-400 animate-spin mb-1" />
                    ) : (
                      <Mic className="w-5 h-5 text-indigo-400 mb-1" />
                    )}
                    <span className="text-xs font-bold">1. Transcribe</span>
                    <span className="text-[10px] text-gray-500">Speech-to-Text</span>
                  </button>

                  {/* Step 2: Translate */}
                  <button
                    onClick={triggerTranslate}
                    disabled={segments.length === 0 || isTranslating}
                    className="flex flex-col items-center justify-center p-3 rounded-2xl bg-gray-900 border border-gray-800 hover:border-amber-500 text-white transition disabled:opacity-50"
                  >
                    {isTranslating ? (
                      <Loader2 className="w-5 h-5 text-amber-400 animate-spin mb-1" />
                    ) : (
                      <Globe className="w-5 h-5 text-amber-400 mb-1" />
                    )}
                    <span className="text-xs font-bold">2. Translate</span>
                    <span className="text-[10px] text-gray-500">{targetLanguage} Spoken</span>
                  </button>

                  {/* Step 3: Burn & Export */}
                  <button
                    onClick={triggerRender}
                    disabled={segments.length === 0 || isRendering}
                    className="flex flex-col items-center justify-center p-3 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white transition shadow-lg shadow-indigo-600/30 disabled:opacity-50"
                  >
                    {isRendering ? (
                      <Loader2 className="w-5 h-5 animate-spin mb-1" />
                    ) : (
                      <Film className="w-5 h-5 mb-1" />
                    )}
                    <span className="text-xs font-bold">3. Burn & Export</span>
                    <span className="text-[10px] text-indigo-200">MP4 + SRT + ASS</span>
                  </button>
                </div>

                {statusMsg && (
                  <p className="text-xs text-indigo-300 font-medium text-center bg-indigo-950/40 border border-indigo-900/50 py-1.5 px-3 rounded-xl">
                    {statusMsg}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Configuration & Editor Tabs */}
          <div className="bg-[#121622] border border-gray-800 rounded-3xl p-5 shadow-lg flex-1 flex flex-col">
            {/* Tabs Header */}
            <div className="flex items-center gap-2 border-b border-gray-800 pb-3 mb-4">
              <button
                onClick={() => setActiveTab("style")}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
                  activeTab === "style"
                    ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Caption Styling & Presets</span>
              </button>

              <button
                onClick={() => setActiveTab("subtitles")}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
                  activeTab === "subtitles"
                    ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                <span>Transcript & Timings</span>
                {segments.length > 0 && (
                  <span className="px-2 py-0.5 rounded-full bg-indigo-500/30 text-indigo-300 text-[10px]">
                    {segments.length}
                  </span>
                )}
              </button>
            </div>

            {/* Tab Contents */}
            <div className="flex-1">
              {activeTab === "style" ? (
                <StyleToolbar
                  styleSettings={styleSettings}
                  setStyleSettings={setStyleSettings}
                />
              ) : (
                <SubtitleEditor
                  segments={segments}
                  setSegments={setSegments}
                  currentTime={currentTime}
                  onSeek={(time) => {
                    setCurrentTime(time);
                    if (videoRef.current) {
                      videoRef.current.currentTime = time;
                    }
                  }}
                />
              )}
            </div>
          </div>
        </section>
      </main>

      {/* Export Ready Modal */}
      <ExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        downloadUrls={exportUrls}
      />

      {/* Public User Auth Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onAuthSuccess={(u) => {
          setUser(u);
          fetchUserQuota();
        }}
      />

      {/* Dedicated Admin Login Modal (Restricted IP) */}
      <AdminLoginModal
        isOpen={isAdminLoginOpen}
        onClose={() => setIsAdminLoginOpen(false)}
        onAdminSuccess={(admin) => {
          setAdminUser(admin);
          setIsAdminDashboardOpen(true);
        }}
      />

      {/* Dedicated Admin Dashboard */}
      <AdminDashboard
        isOpen={isAdminDashboardOpen}
        onClose={() => setIsAdminDashboardOpen(false)}
        adminUser={adminUser}
        onLogout={handleLogoutAdmin}
      />
    </div>
  );
}
