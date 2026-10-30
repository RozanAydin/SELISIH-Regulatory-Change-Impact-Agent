"use client";

import React, { useState } from "react";
import {
  X,
  FolderGit2,
  CheckCircle2,
  AlertTriangle,
  Plus,
  Building2,
  HardDrive,
} from "lucide-react";
import { CompanyProfile, CompanyRepo } from "@/lib/api";

interface RepoManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  company: CompanyProfile | null;
  onAddRepo: (name: string, path: string) => Promise<void>;
}

export default function RepoManagerModal({
  isOpen,
  onClose,
  company,
  onAddRepo,
}: RepoManagerModalProps) {
  const [repoName, setRepoName] = useState("");
  const [repoPath, setRepoPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  if (!isOpen || !company) return null;

  const isQuotaFull =
    company.repo_limit !== -1 && company.active_repos >= company.repo_limit;

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoName.trim() || !repoPath.trim()) {
      setErrorMsg("Nama repositori dan path direktori lokal wajib diisi.");
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await onAddRepo(repoName.trim(), repoPath.trim());
      setSuccessMsg(`Repositori "${repoName.trim()}" berhasil didaftarkan.`);
      setRepoName("");
      setRepoPath("");
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setErrorMsg(err.message || "Gagal mendaftarkan repositori.");
    } finally {
      setLoading(false);
    }
  };

  const percentage =
    company.repo_limit < 0
      ? 100
      : Math.min(100, Math.round((company.active_repos / company.repo_limit) * 100));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#1A1917]/50 backdrop-blur-xs p-4">
      <div className="w-full max-w-2xl rounded-lg border border-[#C8C2B5] bg-[#FFFFFF] shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-[#DDD8CD] px-6 py-4 bg-[#FAF8F5]">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-md bg-[#1A1917] text-white flex items-center justify-center">
              <FolderGit2 className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-[#111110]">
                Manajer Repositori Terpadu
              </h3>
              <p className="text-xs text-[#4A4843]">
                Pendaftaran &amp; pemetaan repositori lokal perusahaan (Zero-Cloud Data Privacy)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[#8C887B] hover:text-[#111110] p-1.5 rounded-md hover:bg-[#EFECE6] transition-colors cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Company & Quota Banner */}
          <div className="rounded-md border border-[#DDD8CD] bg-[#FAF8F5] p-4 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center space-x-2">
                <Building2 className="h-4 w-4 text-[#1A1917]" />
                <span className="text-xs font-bold text-[#111110]">
                  {company.organization}
                </span>
                <span className="rounded bg-[#EFECE6] px-2 py-0.5 text-[10px] font-bold text-[#2D2C28] border border-[#C8C2B5]">
                  {company.plan_label}
                </span>
              </div>
              <div>
                <span
                  className={`rounded px-2 py-0.5 text-[10px] font-bold border ${
                    company.can_run
                      ? "bg-[#E6F4EA] border-[#A3D4B0] text-[#0F5C2B]"
                      : "bg-[#FCE8E6] border-[#F4B3AE] text-[#C5221F]"
                  }`}
                >
                  {company.status_label}
                </span>
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[#4A4843]">Penggunaan Kuota Repositori:</span>
                <span className="font-bold text-[#111110]">
                  {company.repo_limit < 0
                    ? `${company.active_repos}`
                    : `${company.active_repos} / ${company.repo_limit} Repositori`}
                </span>
              </div>
              <div className="w-full bg-[#DDD8CD] h-2 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    !company.can_run
                      ? "bg-[#C5221F]"
                      : company.repo_limit < 0
                      ? "bg-[#0F5C2B]"
                      : "bg-[#1A1917]"
                  }`}
                  style={{ width: `${percentage}%` }}
                ></div>
              </div>
            </div>

            <p className="text-[11px] text-[#4A4843] leading-relaxed">
              {company.message}
            </p>
          </div>

          {/* Alert Messages */}
          {errorMsg && (
            <div className="rounded-md border border-[#F4B3AE] bg-[#FCE8E6] p-3 text-xs text-[#C5221F] flex items-start space-x-2">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="rounded-md border border-[#A3D4B0] bg-[#E6F4EA] p-3 text-xs text-[#0F5C2B] flex items-start space-x-2">
              <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Registered Repositories List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-[#3C3A35] uppercase tracking-wider">
                Daftar Repositori Terdaftar ({company.repositories.length})
              </h4>
              <span className="text-[11px] text-[#8C887B]">
                Privat di Lingkungan Perusahaan
              </span>
            </div>

            <div className="space-y-2">
              {company.repositories.map((repo, idx) => (
                <div
                  key={repo.id || idx}
                  className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] p-3 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <div className="flex items-start space-x-2.5">
                    <HardDrive className="h-4 w-4 text-[#1A1917] shrink-0 mt-0.5" />
                    <div>
                      <div className="text-xs font-bold text-[#111110]">
                        {repo.name}
                      </div>
                      <div className="text-[11px] font-mono text-[#8C887B]">
                        Path: {repo.path}
                      </div>
                    </div>
                  </div>

                  <div>
                    {repo.is_active ? (
                      <span className="rounded bg-[#E6F4EA] border border-[#A3D4B0] px-2 py-0.5 text-[10px] font-bold text-[#0F5C2B]">
                        Target Pemindaian Aktif
                      </span>
                    ) : (
                      <span className="rounded bg-[#FAF8F5] border border-[#DDD8CD] px-2 py-0.5 text-[10px] font-bold text-[#4A4843]">
                        Tersedia di Registry
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Form Register New Repository */}
          <div className="rounded-md border border-[#DDD8CD] bg-[#FAF8F5] p-5 space-y-3">
            <div className="flex items-center space-x-2">
              <Plus className="h-4 w-4 text-[#1A1917]" />
              <h4 className="text-xs font-bold text-[#111110] uppercase tracking-wider">
                Daftarkan Repositori Baru ke Entitas Perusahaan
              </h4>
            </div>

            {isQuotaFull ? (
              <div className="rounded-md border border-[#F5D68B] bg-[#FEF7E0] p-3 text-xs text-[#8A5B00] leading-relaxed">
                <strong>Batas Kuota Paket Tercapai:</strong> Kuota repositori untuk entitas{" "}
                <strong>{company.organization}</strong> ({company.active_repos}/
                {company.repo_limit}) telah penuh. Tingkatkan paket ke Professional atau
                Enterprise untuk mendaftarkan repositori tambahan.
              </div>
            ) : (
              <form onSubmit={handleRegister} className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-[#3C3A35] mb-1">
                      Nama Layanan / Repositori
                    </label>
                    <input
                      type="text"
                      value={repoName}
                      onChange={(e) => setRepoName(e.target.value)}
                      placeholder="contoh: loan-underwriting-service"
                      className="w-full rounded border border-[#C8C2B5] bg-[#FFFFFF] px-3 py-1.5 text-xs text-[#111110] focus:border-[#1A1917] focus:outline-none shadow-xs font-sans"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-[#3C3A35] mb-1">
                      Path Folder Lokal di Komputer
                    </label>
                    <input
                      type="text"
                      value={repoPath}
                      onChange={(e) => setRepoPath(e.target.value)}
                      placeholder="contoh: D:/projects/fintech/loan-service"
                      className="w-full rounded border border-[#C8C2B5] bg-[#FFFFFF] px-3 py-1.5 text-xs text-[#111110] focus:border-[#1A1917] focus:outline-none shadow-xs font-mono"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1">
                  <span className="text-[10px] text-[#8C887B]">
                    Kode sumber tetap 100% lokal. Tidak ada kode yang diunggah ke cloud.
                  </span>
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex items-center space-x-1.5 rounded bg-[#1A1917] hover:bg-[#2D2C28] disabled:opacity-50 px-4 py-2 text-xs font-bold text-white transition-colors cursor-pointer shadow-xs"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    <span>{loading ? "Mendaftarkan..." : "Daftarkan Repositori"}</span>
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="border-t border-[#DDD8CD] px-6 py-3 bg-[#FAF8F5] flex justify-end">
          <button
            onClick={onClose}
            className="rounded border border-[#C8C2B5] bg-[#FFFFFF] hover:bg-[#F3EFE8] px-4 py-1.5 text-xs font-semibold text-[#1A1917] transition-colors cursor-pointer"
          >
            Tutup
          </button>
        </div>
      </div>
    </div>
  );
}
