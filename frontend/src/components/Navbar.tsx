import React from "react";
import { Sparkles, Shield, LogIn, LogOut, Video } from "lucide-react";

interface NavbarProps {
  targetLanguage: string;
  setTargetLanguage: (lang: string) => void;
  user: any;
  userQuota: { used: number; limit: number; remaining: number; is_admin: boolean } | null;
  onOpenAuth: () => void;
  onLogoutUser: () => void;
  adminUser: any;
  onOpenAdminLogin: () => void;
  onOpenAdminDashboard: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  targetLanguage,
  setTargetLanguage,
  user,
  userQuota,
  onOpenAuth,
  onLogoutUser,
  adminUser,
  onOpenAdminLogin,
  onOpenAdminDashboard,
}) => {
  return (
    <header className="h-16 border-b border-gray-800 bg-[#0E131F]/90 backdrop-blur sticky top-0 z-40 px-4 md:px-6 flex items-center justify-between">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-amber-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="font-bold text-base md:text-lg text-white tracking-tight flex items-center gap-2">
            ReelCaption <span className="text-[10px] bg-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded-full font-mono border border-indigo-500/30">AI STUDIO</span>
          </h1>
          <p className="text-[10px] text-gray-400 hidden sm:block">Shorts, Reels & TikTok Auto-Captions</p>
        </div>
      </div>

      {/* Center / User Quota Indicator */}
      <div className="hidden md:flex items-center">
        {user ? (
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-gray-900 border border-gray-800 text-xs text-gray-300 shadow-inner">
            <Video className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-gray-400">Daily Quota:</span>
            {userQuota?.is_admin ? (
              <span className="font-mono text-amber-300 font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/25 text-[11px]">
                ⚡ Unlimited (Admin)
              </span>
            ) : (
              <div className="flex items-center gap-1.5 font-mono font-medium">
                <span className={userQuota && userQuota.used >= userQuota.limit ? "text-red-400 font-bold" : "text-emerald-400 font-bold"}>
                  {userQuota?.used ?? 0}
                </span>
                <span className="text-gray-500">/</span>
                <span className="text-gray-400">3 Videos</span>
                {userQuota && userQuota.remaining === 0 && (
                  <span className="text-[10px] text-amber-400 bg-amber-500/10 border border-amber-500/20 px-1.5 rounded ml-1">
                    Limit Reached
                  </span>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-900/60 border border-gray-800/80 text-xs text-gray-400">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>3 Free Videos / Day with Free Account</span>
          </div>
        )}
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2.5">
        {/* Target Language Select */}
        <div className="hidden sm:flex items-center gap-2 bg-gray-900 border border-gray-800 rounded-lg px-2.5 py-1.5">
          <span className="text-xs text-gray-400">Target:</span>
          <select
            value={targetLanguage}
            onChange={(e) => setTargetLanguage(e.target.value)}
            className="bg-transparent text-xs font-medium text-white focus:outline-none cursor-pointer"
          >
            <option value="Burmese" className="bg-gray-900">🇲🇲 Burmese (စကားပြောဟန်)</option>
            <option value="English" className="bg-gray-900">🇬🇧 English</option>
            <option value="Thai" className="bg-gray-900">🇹🇭 Thai</option>
            <option value="Chinese" className="bg-gray-900">🇨🇳 Chinese</option>
            <option value="Japanese" className="bg-gray-900">🇯🇵 Japanese</option>
            <option value="Korean" className="bg-gray-900">🇰🇷 Korean</option>
          </select>
        </div>

        {/* Admin Portal Trigger */}
        {adminUser ? (
          <button
            onClick={onOpenAdminDashboard}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/40 text-xs font-semibold transition"
          >
            <Shield className="w-3.5 h-3.5 text-amber-400" />
            <span>Admin Hub</span>
          </button>
        ) : (
          <button
            onClick={onOpenAdminLogin}
            className="p-2 rounded-lg bg-gray-900 hover:bg-gray-800 text-gray-500 hover:text-amber-400 transition"
            title="Admin Portal (Restricted IP)"
          >
            <Shield className="w-3.5 h-3.5" />
          </button>
        )}

        {/* User Account Button */}
        {user ? (
          <div className="flex items-center gap-2 bg-gray-900 border border-gray-800 rounded-lg px-2.5 py-1.5">
            <div className="w-5 h-5 rounded-full bg-indigo-600 flex items-center justify-center text-[10px] text-white font-bold">
              {user.username.charAt(0).toUpperCase()}
            </div>
            <span className="text-xs text-gray-300 font-medium max-w-[80px] truncate hidden md:inline">
              {user.username}
            </span>
            <button
              onClick={onLogoutUser}
              className="text-gray-400 hover:text-red-400 transition ml-1"
              title="Sign Out"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenAuth}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition shadow-md shadow-indigo-600/30"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Sign In</span>
          </button>
        )}
      </div>
    </header>
  );
};
