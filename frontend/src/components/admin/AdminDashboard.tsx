import React, { useState, useEffect } from "react";
import { 
  X, Shield, Users, HardDrive, Cpu, Trash2, RefreshCw, 
  Clock, AlertTriangle, CheckCircle, Database, LogOut, Key, Check, Lock
} from "lucide-react";

interface AdminDashboardProps {
  isOpen: boolean;
  onClose: () => void;
  adminUser: any;
  onLogout: () => void;
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({
  isOpen,
  onClose,
  adminUser,
  onLogout
}) => {
  const [stats, setStats] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Global Gemini Key Management
  const [geminiInfo, setGeminiInfo] = useState<{ configured: boolean; masked_key: string } | null>(null);
  const [newGeminiKey, setNewGeminiKey] = useState("");
  const [keySaving, setKeySaving] = useState(false);
  const [keyMsg, setKeyMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Admin Password Management
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [pwdSaving, setPwdSaving] = useState(false);
  const [pwdMsg, setPwdMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Live VPS RAM Footprint (Admin Telemetry)
  const [liveRam, setLiveRam] = useState<number | null>(null);

  const fetchAdminData = async () => {
    const token = localStorage.getItem("reel_admin_token");
    if (!token) return;

    setLoading(true);
    try {
      // 1. Fetch Stats
      const statsRes = await fetch("/api/admin/stats", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
        if (statsData?.vps_health?.app_ram_mb) {
          setLiveRam(statsData.vps_health.app_ram_mb);
        }
      }

      // 2. Fetch Users
      const usersRes = await fetch("/api/admin/users", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (usersRes.ok) {
        const usersData = await usersRes.json();
        setUsers(usersData.users || []);
      }

      // 3. Fetch Global Gemini Key
      const keyRes = await fetch("/api/admin/gemini-key", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (keyRes.ok) {
        const keyData = await keyRes.json();
        setGeminiInfo(keyData);
      }
    } catch (err: any) {
      setActionMsg({ type: "error", text: "Failed to fetch admin metrics." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchAdminData();
      // Live RAM health polling every 4s for Admin
      const interval = setInterval(async () => {
        try {
          const res = await fetch("/api/health");
          if (res.ok) {
            const h = await res.json();
            setLiveRam(h.app_ram_mb);
          }
        } catch {}
      }, 4000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  const handleUpdateGeminiKey = async () => {
    if (!newGeminiKey.trim()) return;
    const token = localStorage.getItem("reel_admin_token");
    if (!token) return;

    setKeySaving(true);
    setKeyMsg(null);
    try {
      const res = await fetch("/api/admin/gemini-key", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ gemini_key: newGeminiKey.trim() })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to update Gemini key");

      setKeyMsg({ type: "success", text: "Global Gemini API Key verified & saved to server!" });
      setGeminiInfo({ configured: true, masked_key: data.masked_key });
      setNewGeminiKey("");
    } catch (err: any) {
      setKeyMsg({ type: "error", text: err.message });
    } finally {
      setKeySaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (!oldPassword || !newPassword) {
      setPwdMsg({ type: "error", text: "Please enter both your current password and new password." });
      return;
    }
    if (newPassword.length < 8) {
      setPwdMsg({ type: "error", text: "New password must be at least 8 characters long." });
      return;
    }
    const token = localStorage.getItem("reel_admin_token");
    if (!token) return;

    setPwdSaving(true);
    setPwdMsg(null);
    try {
      const res = await fetch("/api/admin/change-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to update password");
      setPwdMsg({ type: "success", text: "Admin password updated successfully! Please use your new password next time." });
      setOldPassword("");
      setNewPassword("");
    } catch (err: any) {
      setPwdMsg({ type: "error", text: err.message });
    } finally {
      setPwdSaving(false);
    }
  };

  const handleManualCleanup = async (days = 3.0) => {
    const token = localStorage.getItem("reel_admin_token");
    if (!token) return;

    setCleanupLoading(true);
    setActionMsg(null);

    try {
      const res = await fetch("/api/admin/cleanup", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ days })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Cleanup failed");

      setActionMsg({
        type: "success",
        text: `Successfully purged ${data.deleted_count} files older than ${days} days, freeing ${data.reclaimed_mb} MB!`
      });
      // Refresh metrics
      fetchAdminData();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message });
    } finally {
      setCleanupLoading(false);
    }
  };

  const handlePurgeUserFiles = async (userId: number, username: string) => {
    if (!confirm(`Are you sure you want to delete all uploaded and processed files for ${username}?`)) return;

    const token = localStorage.getItem("reel_admin_token");
    if (!token) return;

    try {
      const res = await fetch(`/api/admin/users/${userId}/purge`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "User purge failed");

      setActionMsg({
        type: "success",
        text: `Purged files for ${username}: freed ${data.reclaimed_mb} MB.`
      });
      fetchAdminData();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message });
    }
  };

  const handleDeleteUser = async (userId: number, username: string) => {
    if (!confirm(`CAUTION: Are you sure you want to permanently delete user "${username}" and all their files?`)) return;

    const token = localStorage.getItem("reel_admin_token");
    if (!token) return;

    try {
      const res = await fetch(`/api/admin/users/${userId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Delete user failed");

      setActionMsg({ type: "success", text: `User ${username} permanently deleted.` });
      fetchAdminData();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-3 md:p-6 overflow-y-auto">
      <div className="bg-[#0E121B] border border-gray-800 rounded-3xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl relative overflow-hidden">
        
        {/* Top Header */}
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between bg-[#131824]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center">
              <Shield className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                ADMIN CONTROL CENTER
                <span className="text-[10px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full font-mono border border-amber-500/30">
                  CONFIDENTIAL
                </span>
              </h2>
              <p className="text-xs text-gray-400">
                Logged in as <span className="text-amber-400 font-mono">{adminUser?.email || "Admin"}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchAdminData}
              disabled={loading}
              className="p-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 transition"
              title="Refresh Stats"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-amber-400" : ""}`} />
            </button>
            <button
              onClick={onLogout}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 text-xs font-semibold transition"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Admin Logout</span>
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-gray-400 hover:text-white transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* Action Notification */}
          {actionMsg && (
            <div className={`p-3.5 rounded-2xl flex items-center gap-2.5 text-xs font-medium ${
              actionMsg.type === "success" 
                ? "bg-emerald-500/15 border border-emerald-500/30 text-emerald-300"
                : "bg-red-500/15 border border-red-500/30 text-red-300"
            }`}>
              {actionMsg.type === "success" ? (
                <CheckCircle className="w-4 h-4 shrink-0 text-emerald-400" />
              ) : (
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
              )}
              <span>{actionMsg.text}</span>
            </div>
          )}

          {/* Metric Cards Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 1. Users */}
            <div className="bg-[#141926] border border-gray-800 rounded-2xl p-4 flex flex-col justify-between">
              <div className="flex items-center justify-between text-gray-400 text-xs font-medium mb-2">
                <span>Total Users</span>
                <Users className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="text-2xl font-bold text-white">
                {stats?.users?.total ?? 0}
              </div>
              <div className="text-[11px] text-gray-400 mt-2 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                <span>{stats?.users?.active_24h ?? 0} active in last 24h</span>
              </div>
            </div>

            {/* 2. Disk Storage */}
            <div className="bg-[#141926] border border-gray-800 rounded-2xl p-4 flex flex-col justify-between">
              <div className="flex items-center justify-between text-gray-400 text-xs font-medium mb-2">
                <span>Storage Occupied</span>
                <HardDrive className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-2xl font-bold text-white font-mono">
                {stats?.media?.total_disk_mb ?? 0} <span className="text-sm font-sans font-normal text-gray-400">MB</span>
              </div>
              <div className="text-[11px] text-gray-400 mt-2">
                Uploads: {stats?.media?.uploads_folder_mb ?? 0} MB • Outputs: {stats?.media?.outputs_folder_mb ?? 0} MB
              </div>
            </div>

            {/* 3. 1GB VPS RAM Status (Live Telemetry) */}
            <div className="bg-[#141926] border border-gray-800 rounded-2xl p-4 flex flex-col justify-between">
              <div className="flex items-center justify-between text-gray-400 text-xs font-medium mb-2">
                <span>1GB VPS RAM Footprint</span>
                <Cpu className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-bold text-emerald-400 font-mono flex items-baseline gap-2">
                {liveRam !== null ? liveRam : (stats?.vps_health?.app_ram_mb ?? 0)}{" "}
                <span className="text-sm font-sans font-normal text-gray-400">MB</span>
              </div>
              <div className="text-[11px] text-emerald-400 mt-2 flex items-center gap-1.5">
                <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                <span>Live server footprint (&lt; 100MB)</span>
              </div>
            </div>

            {/* 4. Retention Policy */}
            <div className="bg-[#141926] border border-gray-800 rounded-2xl p-4 flex flex-col justify-between">
              <div className="flex items-center justify-between text-gray-400 text-xs font-medium mb-2">
                <span>Data Retention</span>
                <Clock className="w-4 h-4 text-blue-400" />
              </div>
              <div className="text-2xl font-bold text-blue-400">
                3 Days <span className="text-sm font-sans font-normal text-gray-400">(72h)</span>
              </div>
              <div className="text-[11px] text-gray-400 mt-2 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
                <span>Auto-cleans hourly</span>
              </div>
            </div>
          </div>

          {/* Retention & Manual Storage Clean Hub */}
          <div className="bg-[#141926] border border-gray-800 rounded-2xl p-5">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Database className="w-4 h-4 text-amber-400" />
                  <span>3-Day Data Retention & Purge Hub</span>
                </h3>
                <p className="text-xs text-gray-400 mt-1">
                  Uploaded files and burned outputs older than 3 days are purged automatically every hour. You can also trigger an immediate purge manually.
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => handleManualCleanup(3.0)}
                  disabled={cleanupLoading}
                  className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-semibold text-xs flex items-center gap-2 transition disabled:opacity-50 shadow-lg shadow-amber-500/20"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>{cleanupLoading ? "Cleaning..." : "Run 3-Day Cleanup Now"}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Global Gemini API Key & Rate Limit Hub */}
          <div className="bg-[#141926] border border-gray-800 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-amber-500/15 border border-amber-500/25 flex items-center justify-center">
                  <Key className="w-4 h-4 text-amber-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    Global Gemini API Key & Rate Limiting
                    {geminiInfo?.configured ? (
                      <span className="text-[10px] bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-full font-mono font-medium">
                        ACTIVE • {geminiInfo.masked_key}
                      </span>
                    ) : (
                      <span className="text-[10px] bg-red-500/15 text-red-300 border border-red-500/30 px-2 py-0.5 rounded-full font-mono font-medium">
                        NOT CONFIGURED
                      </span>
                    )}
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    This key powers AI transcription and Burmese translation for all registered users globally.
                  </p>
                </div>
              </div>
            </div>

            <p className="text-xs text-gray-400 mb-4 leading-relaxed bg-[#0F131F] border border-gray-800/80 p-3 rounded-xl">
              🛡️ <strong className="text-gray-200">Host Quota Protection:</strong> Non-admin users are strictly limited to{" "}
              <span className="text-amber-400 font-semibold">3 videos per day</span>. Admins enjoy unlimited processing. Public users cannot view or alter this key.
            </p>

            {keyMsg && (
              <div className={`p-3 rounded-xl mb-3 text-xs font-medium flex items-center gap-2 ${
                keyMsg.type === "success" 
                  ? "bg-emerald-500/15 border border-emerald-500/30 text-emerald-300"
                  : "bg-red-500/15 border border-red-500/30 text-red-300"
              }`}>
                {keyMsg.type === "success" ? <Check className="w-3.5 h-3.5 shrink-0" /> : <AlertTriangle className="w-3.5 h-3.5 shrink-0" />}
                <span>{keyMsg.text}</span>
              </div>
            )}

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
              <input
                type="password"
                value={newGeminiKey}
                onChange={(e) => setNewGeminiKey(e.target.value)}
                placeholder="Paste new Gemini API Key to update (e.g. AIzaSy...)"
                className="flex-1 bg-gray-950 border border-gray-700 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-amber-500 font-mono transition"
              />
              <button
                onClick={handleUpdateGeminiKey}
                disabled={keySaving || !newGeminiKey.trim()}
                className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-black font-semibold text-xs flex items-center justify-center gap-2 transition disabled:opacity-50 shrink-0 shadow-lg shadow-amber-500/20"
              >
                <Key className="w-3.5 h-3.5" />
                <span>{keySaving ? "Verifying with Google..." : "Verify & Save Globally"}</span>
              </button>
            </div>
          </div>

          {/* Admin Security & Password Change */}
          <div className="bg-[#141926] border border-gray-800 rounded-2xl p-5">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="w-8 h-8 rounded-xl bg-amber-500/15 border border-amber-500/25 flex items-center justify-center">
                <Lock className="w-4 h-4 text-amber-400" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  Admin Security & Password
                </h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  Update default admin password with a strong custom password (min 8 characters).
                </p>
              </div>
            </div>

            {pwdMsg && (
              <div className={`p-3 rounded-xl mb-3 text-xs font-medium flex items-center gap-2 ${
                pwdMsg.type === "success" 
                  ? "bg-emerald-500/15 border border-emerald-500/30 text-emerald-300"
                  : "bg-red-500/15 border border-red-500/30 text-red-300"
              }`}>
                {pwdMsg.type === "success" ? <Check className="w-3.5 h-3.5 shrink-0" /> : <AlertTriangle className="w-3.5 h-3.5 shrink-0" />}
                <span>{pwdMsg.text}</span>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
              <div>
                <label className="block text-[11px] font-medium text-gray-400 mb-1">Current Password</label>
                <input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  placeholder="Current password (default: Admin@123456)"
                  className="w-full bg-gray-950 border border-gray-700 rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-amber-500 font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-400 mb-1">New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  className="w-full bg-gray-950 border border-gray-700 rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-amber-500 font-mono"
                />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleChangePassword}
                disabled={pwdSaving || !oldPassword || !newPassword}
                className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-semibold text-xs flex items-center gap-2 transition disabled:opacity-50 shadow-lg shadow-amber-500/20"
              >
                <Lock className="w-3.5 h-3.5" />
                <span>{pwdSaving ? "Updating Password..." : "Update Admin Password"}</span>
              </button>
            </div>
          </div>

          {/* User Management Table */}
          <div className="bg-[#141926] border border-gray-800 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Users className="w-4 h-4 text-indigo-400" />
                <span>User Directory ({users.length})</span>
              </h3>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-gray-300">
                <thead className="bg-[#1B2132] text-gray-400 uppercase font-mono text-[10px]">
                  <tr>
                    <th className="px-3.5 py-2.5 rounded-l-xl">User</th>
                    <th className="px-3.5 py-2.5">Role</th>
                    <th className="px-3.5 py-2.5">Videos</th>
                    <th className="px-3.5 py-2.5">Storage</th>
                    <th className="px-3.5 py-2.5">Registered</th>
                    <th className="px-3.5 py-2.5">Last Active</th>
                    <th className="px-3.5 py-2.5 text-right rounded-r-xl">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-800/30 transition">
                      <td className="px-3.5 py-3">
                        <div className="font-medium text-white">{u.username}</div>
                        <div className="text-[11px] text-gray-400 font-mono">{u.email}</div>
                      </td>
                      <td className="px-3.5 py-3">
                        <span className={`px-2 py-0.5 rounded-full font-mono text-[10px] ${
                          u.role === "admin" 
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                            : "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                        }`}>
                          {u.role.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-3.5 py-3 font-mono font-medium text-white">
                        {u.total_videos}
                      </td>
                      <td className="px-3.5 py-3 font-mono text-gray-300">
                        {u.total_mb_used} MB
                      </td>
                      <td className="px-3.5 py-3 text-gray-400">
                        {u.created_at?.slice(0, 10) || "N/A"}
                      </td>
                      <td className="px-3.5 py-3 text-gray-400 font-mono text-[11px]">
                        {u.last_login ? u.last_login.slice(0, 16) : "Never"}
                      </td>
                      <td className="px-3.5 py-3 text-right">
                        {u.role !== "admin" ? (
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handlePurgeUserFiles(u.id, u.username)}
                              className="px-2 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 text-amber-400 text-[11px] transition"
                              title="Wipe files for this user"
                            >
                              Purge Files
                            </button>
                            <button
                              onClick={() => handleDeleteUser(u.id, u.username)}
                              className="px-2 py-1 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 text-[11px] transition"
                              title="Delete user account"
                            >
                              Delete
                            </button>
                          </div>
                        ) : (
                          <span className="text-[11px] text-gray-500 italic">Protected</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};
