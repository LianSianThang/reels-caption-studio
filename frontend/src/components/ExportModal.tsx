import React from "react";
import { Download, Film, FileText, CheckCircle2, X } from "lucide-react";
import { API_BASE_URL } from "../config";

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  downloadUrls: {
    video_url: string;
    download_url: string;
    srt_url: string;
    ass_url: string;
  } | null;
}

export const ExportModal: React.FC<ExportModalProps> = ({
  isOpen,
  onClose,
  downloadUrls,
}) => {
  if (!isOpen || !downloadUrls) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#151922] border border-gray-800 rounded-3xl w-full max-w-md p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-base">Export Ready!</h3>
              <p className="text-[11px] text-gray-400">Your stylized reel is rendered & ready</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Action Buttons */}
        <div className="space-y-3">
          {/* Burned MP4 Download */}
          <a
            href={`${API_BASE_URL}${downloadUrls.download_url}`}
            download
            className="w-full flex items-center justify-between p-4 rounded-2xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-medium shadow-lg shadow-indigo-600/30 transition group"
          >
            <div className="flex items-center gap-3">
              <Film className="w-5 h-5" />
              <div className="text-left">
                <div className="text-sm font-bold">Burned Video (MP4)</div>
                <div className="text-[10px] text-indigo-200">Hardcoded styled captions</div>
              </div>
            </div>
            <Download className="w-4 h-4 group-hover:translate-y-0.5 transition-transform" />
          </a>

          {/* Subtitle Downloads Row */}
          <div className="grid grid-cols-2 gap-3 pt-2">
            <a
              href={`${API_BASE_URL}${downloadUrls.srt_url}`}
              download
              className="flex items-center justify-between p-3 rounded-xl bg-gray-900 border border-gray-800 hover:border-gray-700 text-gray-300 hover:text-white transition text-xs font-medium"
            >
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-amber-400" />
                <span>Download .SRT</span>
              </div>
              <Download className="w-3.5 h-3.5" />
            </a>

            <a
              href={`${API_BASE_URL}${downloadUrls.ass_url}`}
              download
              className="flex items-center justify-between p-3 rounded-xl bg-gray-900 border border-gray-800 hover:border-gray-700 text-gray-300 hover:text-white transition text-xs font-medium"
            >
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-purple-400" />
                <span>Download .ASS</span>
              </div>
              <Download className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>

        <button
          onClick={onClose}
          className="w-full mt-6 py-2.5 rounded-xl bg-gray-800/80 hover:bg-gray-800 text-gray-300 text-xs font-medium transition"
        >
          Close
        </button>
      </div>
    </div>
  );
};
