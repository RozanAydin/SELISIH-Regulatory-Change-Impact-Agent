"use client";

import React, { useEffect, useState } from "react";
import { X, History, UserCheck, Clock, FileText, CheckCircle2 } from "lucide-react";
import { AuditLog, fetchAuditLogs } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

interface AuditTrailModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AuditTrailModal({ isOpen, onClose }: AuditTrailModalProps) {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      fetchAuditLogs()
        .then((data) => setLogs(data))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-3xl rounded-md border border-[#DDD8CD] bg-[#FFFFFF] shadow-xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-[#DDD8CD] px-6 py-4 bg-[#F3EFE8]">
          <div className="flex items-center space-x-2">
            <History className="h-5 w-5 text-[#8A5B00]" />
            <h3 className="text-base font-bold text-[#111110] tracking-tight">
              Jejak Audit Enterprise (Audit Trail Log)
            </h3>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-[#4A4843] hover:text-[#111110] hover:bg-[#EFECE6] transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3 bg-[#FAF8F5]">
          {loading ? (
            <div className="py-12 text-center text-sm text-[#8C887B]">Memuat riwayat jejak audit...</div>
          ) : logs.length === 0 ? (
            <div className="py-12 text-center text-sm text-[#8C887B]">Belum ada aktivitas tercatat.</div>
          ) : (
            logs.map((log) => (
              <div
                key={log.id}
                className="rounded border border-[#DDD8CD] bg-[#FFFFFF] p-4 text-xs space-y-2 shadow-sm"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#DDD8CD] pb-2">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono font-bold text-[#1A1917]">{log.id}</span>
                    <span className="rounded bg-[#EFECE6] border border-[#C8C2B5] px-2 py-0.5 text-[10px] font-bold text-[#2D2C28]">
                      {log.action}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2 text-[#4A4843]">
                    <Clock className="h-3.5 w-3.5" />
                    <span>{formatDateTime(log.timestamp)}</span>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <UserCheck className="h-3.5 w-3.5 text-[#0F5C2B]" />
                  <span className="text-[#4A4843]">Peninjau:</span>
                  <span className="font-bold text-[#111110]">{log.actor}</span>
                </div>

                <p className="text-[#1A1917] leading-relaxed">{log.details}</p>

                {log.note && (
                  <div className="rounded bg-[#F8F7F4] border border-[#DDD8CD] p-2 text-[#3C3A35] italic font-medium">
                    Catatan: "{log.note}"
                  </div>
                )}

                {log.backups && log.backups.length > 0 && (
                  <div className="text-[11px] font-mono text-[#8C887B]">
                    Backup: {log.backups.join(", ")}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Modal Footer */}
        <div className="border-t border-[#DDD8CD] px-6 py-3 bg-[#F3EFE8] text-right">
          <button
            onClick={onClose}
            className="rounded border border-[#C8C2B5] bg-[#FFFFFF] hover:bg-[#F8F7F4] px-4 py-1.5 text-xs font-bold text-[#1A1917] transition-colors shadow-sm"
          >
            Tutup
          </button>
        </div>
      </div>
    </div>
  );
}
