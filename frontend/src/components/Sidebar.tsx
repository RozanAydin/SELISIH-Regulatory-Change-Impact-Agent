"use client";

import React from "react";
import { History, Building2, FolderGit2 } from "lucide-react";
import { SystemHealth, CompanyProfile } from "@/lib/api";

interface SidebarProps {
  health: SystemHealth | null;
  activeCompanyId: string;
  companyProfiles: CompanyProfile[];
  onCompanyChange: (id: string) => void;
  onOpenAudit: () => void;
  onOpenRepoManager: () => void;
}

export default function Sidebar({
  health,
  activeCompanyId,
  companyProfiles,
  onCompanyChange,
  onOpenAudit,
  onOpenRepoManager,
}: SidebarProps) {
  const lic = health?.license;
  const comps = health?.components;

  const langflowConnected = comps ? Boolean(comps.langflow?.connected) : Boolean(health?.langflow?.connected);
  const chromadbConnected = comps ? Boolean(comps.chromadb?.connected) : false;
  const bobConnected = comps ? Boolean(comps.bob?.connected) : false;

  const fallbackProfiles: CompanyProfile[] = [
    {
      id: "bank_digital",
      organization: "PT Bank Digital Nusantara",
      plan: "enterprise",
      plan_label: "Enterprise Plan",
      status: "active",
      status_label: "Aktif",
      repo_limit: -1,
      active_repos: 3,
      quota_ok: true,
      can_run: true,
      message: "Lisensi valid. Kuota repositori tidak dibatasi.",
      repositories: [],
    },
    {
      id: "dana_mandiri",
      organization: "PT Dana Mandiri Fintech",
      plan: "professional",
      plan_label: "Professional Plan",
      status: "active",
      status_label: "Aktif",
      repo_limit: 25,
      active_repos: 18,
      quota_ok: true,
      can_run: true,
      message: "Lisensi valid. Kuota repositori 18/25.",
      repositories: [],
    },
    {
      id: "pinjaman_kilat",
      organization: "PT Pinjaman Kilat Indonesia",
      plan: "starter",
      plan_label: "Starter Plan",
      status: "suspended",
      status_label: "Kuota Penuh (5/5)",
      repo_limit: 5,
      active_repos: 5,
      quota_ok: false,
      can_run: false,
      message: "Kuota repositori paket Starter telah terlampaui (5/5). Aksi penerapan patch dinonaktifkan.",
      repositories: [],
    },
  ];

  const profilesToRender = companyProfiles.length > 0 ? companyProfiles : fallbackProfiles;

  return (
    <aside className="w-full md:w-72 bg-[#F3EFE8] border-r border-[#E6E1D8] p-5 flex flex-col space-y-6 text-xs text-[#1A1917] shrink-0 min-h-screen">
      {/* Entitas Perusahaan (B2B License Switcher) */}
      <div className="space-y-2">
        <div className="flex items-center space-x-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#1A1917] text-white font-bold text-xs">
            <Building2 className="h-4 w-4" />
          </div>
          <div>
            <div className="font-bold text-sm text-[#111110]">Entitas Perusahaan</div>
            <div className="text-[11px] text-[#4A4843]">Lisensi Kepatuhan B2B</div>
          </div>
        </div>

        <div className="pt-1">
          <label className="text-[11px] font-bold text-[#4A4843] uppercase tracking-wider block mb-1">
            Organisasi Terdaftar:
          </label>
          <select
            value={activeCompanyId}
            onChange={(e) => onCompanyChange(e.target.value)}
            className="w-full rounded border border-[#C8C2B5] bg-[#FFFFFF] px-2 py-1.5 font-bold text-xs text-[#111110] focus:border-[#1A1917] focus:outline-none shadow-sm cursor-pointer"
          >
            {profilesToRender.map((c) => (
              <option key={c.id} value={c.id}>
                {c.organization} ({c.plan_label})
              </option>
            ))}
          </select>
        </div>
      </div>

      <hr className="border-[#DDD8CD]" />

      {/* Integrasi Komponen */}
      <div className="space-y-2">
        <div className="text-[11px] font-bold uppercase tracking-wider text-[#3C3A35]">
          Integrasi Komponen
        </div>
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-[#4A4843]">Langflow Pipeline:</span>
            <span
              className={`font-bold flex items-center gap-1.5 ${
                langflowConnected ? "text-[#0F5C2B]" : "text-[#C5221F]"
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  langflowConnected ? "bg-[#0F5C2B]" : "bg-[#C5221F]"
                }`}
              />
              {langflowConnected ? "Terhubung" : "Terputus"}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[#4A4843]">ChromaDB Lokal:</span>
            <span
              className={`font-bold flex items-center gap-1.5 ${
                chromadbConnected ? "text-[#0F5C2B]" : "text-[#C5221F]"
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  chromadbConnected ? "bg-[#0F5C2B]" : "bg-[#C5221F]"
                }`}
              />
              {chromadbConnected ? "Terhubung" : "Terputus"}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[#4A4843]">IBM Bob (MCP):</span>
            <span
              className={`font-bold flex items-center gap-1.5 ${
                bobConnected ? "text-[#0F5C2B]" : "text-[#C5221F]"
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  bobConnected ? "bg-[#0F5C2B]" : "bg-[#C5221F]"
                }`}
              />
              {bobConnected ? "Terhubung" : "Terputus"}
            </span>
          </div>
        </div>
      </div>

      <hr className="border-[#DDD8CD]" />

      {/* Langganan & Lisensi */}
      <div className="space-y-2.5">
        <div className="text-[11px] font-bold uppercase tracking-wider text-[#3C3A35]">
          Langganan &amp; Lisensi
        </div>
        <div className="space-y-1 text-xs">
          <div><strong>Organisasi:</strong> {lic?.organization || "PT Bank Digital Nusantara"}</div>
          <div><strong>Paket:</strong> {lic?.plan || "Enterprise Plan"}</div>
          <div className="flex items-center gap-1.5">
            <strong>Status:</strong>
            <span
              className={`rounded border px-1.5 py-0.2 text-[10px] font-bold ${
                lic?.is_valid !== false
                  ? "bg-[#E6F4EA] border-[#A3D4B0] text-[#0F5C2B]"
                  : "bg-[#FCE8E6] border-[#F4B3AE] text-[#C5221F]"
              }`}
            >
              {lic?.status_label || (lic?.is_valid !== false ? "Aktif" : "Dibatasi")}
            </span>
          </div>
          <div>
            <strong>Repositori Aktif:</strong>{" "}
            {(lic?.repo_limit ?? -1) < 0
              ? `${lic?.active_repos ?? 3}`
              : `${lic?.active_repos ?? 3} / ${lic?.repo_limit} Repositori`}
          </div>

          {/* Dynamic Progress Bar */}
          <div className="w-full bg-[#DDD8CD] h-1.5 rounded-full mt-1.5 overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                lic?.is_valid === false
                  ? "bg-[#C5221F]"
                  : (lic?.repo_limit ?? -1) < 0
                  ? "bg-[#0F5C2B]"
                  : "bg-[#1A1917]"
              }`}
              style={{
                width:
                  (lic?.repo_limit ?? -1) < 0
                    ? "100%"
                    : `${Math.min(
                        100,
                        Math.round(((lic?.active_repos ?? 3) / (lic?.repo_limit || 5)) * 100)
                      )}%`,
              }}
            ></div>
          </div>

          <p
            className={`text-[11px] pt-1 leading-relaxed ${
              lic?.is_valid !== false ? "text-[#4A4843]" : "text-[#C5221F] font-semibold"
            }`}
          >
            {lic?.message || "Lisensi valid. Kuota repositori tidak dibatasi."}
          </p>

          <div className="pt-1.5">
            <button
              onClick={onOpenRepoManager}
              className="w-full flex items-center justify-center space-x-1.5 rounded border border-[#C8C2B5] bg-[#FFFFFF] hover:bg-[#FAF8F5] px-2.5 py-1.5 text-[11px] font-bold text-[#1A1917] transition-colors cursor-pointer shadow-xs"
            >
              <FolderGit2 className="h-3.5 w-3.5 text-[#1A1917]" />
              <span>Kelola Repositori ({lic?.active_repos ?? 3})</span>
            </button>
          </div>
        </div>
      </div>

      <hr className="border-[#DDD8CD]" />

      {/* Prinsip Keamanan Enterprise */}
      <div className="space-y-2">
        <div className="text-[11px] font-bold uppercase tracking-wider text-[#3C3A35]">
          Prinsip Keamanan
        </div>
        <div className="space-y-2 text-xs">
          <label className="flex items-center space-x-2 cursor-default">
            <input type="checkbox" checked readOnly className="accent-[#1A1917] rounded" />
            <span className="font-medium text-[#111110]">Kebijakan Abstention Aktif</span>
          </label>
          <label className="flex items-center space-x-2 cursor-default">
            <input type="checkbox" checked readOnly className="accent-[#1A1917] rounded" />
            <span className="font-medium text-[#111110]">Penyimpanan Kode Terisolasi</span>
          </label>
          <p className="text-[11px] text-[#4A4843] leading-relaxed">
            Kode sumber diproses secara lokal di lingkungan klien tanpa transmisi ke repositori eksternal.
          </p>
        </div>
      </div>

      {/* Audit Trail Button */}
      <div className="pt-2 mt-auto">
        <button
          onClick={onOpenAudit}
          className="w-full flex items-center justify-center space-x-1.5 rounded border border-[#C8C2B5] bg-[#FFFFFF] hover:bg-[#F8F7F4] p-2 text-xs font-bold text-[#1A1917] transition-all shadow-sm cursor-pointer"
        >
          <History className="h-3.5 w-3.5 text-[#8A5B00]" />
          <span>Lihat Jejak Audit Lengkap</span>
        </button>
      </div>
    </aside>
  );
}
