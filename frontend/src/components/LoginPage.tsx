"use client";

import React, { useState } from "react";
import { Building2, CheckCircle2, AlertCircle, ArrowRight, ShieldCheck, KeyRound, Lock, User } from "lucide-react";
import { CompanyProfile } from "@/lib/api";

interface LoginPageProps {
  companyProfiles: CompanyProfile[];
  onSelectCompany: (companyId: string) => void;
}

export default function LoginPage({ companyProfiles, onSelectCompany }: LoginPageProps) {
  const [manualUsername, setManualUsername] = useState("");
  const [manualPassword, setManualPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

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
      message: "Kuota repositori paket Starter telah terlampaui (5/5).",
      repositories: [],
    },
  ];

  const profiles = companyProfiles.length > 0 ? companyProfiles : fallbackProfiles;

  const handleManualLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    const u = manualUsername.trim().toLowerCase();
    const p = manualPassword.trim();

    if (!u || !p) {
      setErrorMsg("Silakan masukkan username dan password.");
      return;
    }

    // Aturan yang diminta: password harus sama persis dengan username
    if (u !== p.toLowerCase()) {
      setErrorMsg("Kredensial tidak valid: Password harus sama persis dengan username.");
      return;
    }

    // Cari profil yang cocok berdasarkan ID atau nama organisasi
    const found = profiles.find(
      (c) => c.id.toLowerCase() === u || c.organization.toLowerCase().includes(u)
    );

    if (found) {
      onSelectCompany(found.id);
    } else {
      // Jika username kustom yang valid (misal admin), default ke bank_digital
      onSelectCompany("bank_digital");
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] text-[#1A1917] flex flex-col justify-center items-center py-12 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-4xl w-full space-y-8">
        {/* Brand & Header */}
        <div className="text-center space-y-3">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded bg-[#1A1917] text-white font-bold text-2xl tracking-wider shadow-md">
            S
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-[#111110]">
            SELISIH Enterprise
          </h1>
          <p className="text-xs text-[#4A4843] max-w-lg mx-auto">
            Regulatory Change &amp; Code Impact System — IBM watsonx &amp; IBM Bob
          </p>
          <div className="inline-block rounded-full bg-[#EFECE6] border border-[#DDD8CD] px-4 py-1 text-xs font-semibold text-[#3C3A35]">
            Portal Klien &amp; Manajemen Lisensi B2B
          </div>
        </div>

        {/* 3 Contoh Profil Klien & Paketnya (1-Klik Login) */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-[#DDD8CD] pb-2">
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#3C3A35] flex items-center gap-2">
              <Building2 className="h-4 w-4 text-[#1A1917]" />
              <span>Pilih Contoh Klien Terdaftar (1-Klik Masuk)</span>
            </h2>
            <span className="text-xs text-[#8C887B]">Tersedia 3 Pilihan Paket</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {profiles.map((client) => {
              const isSuspended = !client.can_run || client.status === "suspended";

              return (
                <div
                  key={client.id}
                  onClick={() => onSelectCompany(client.id)}
                  className={`rounded-lg border bg-[#FFFFFF] p-5 shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col justify-between relative group ${
                    isSuspended
                      ? "border-[#F4B3AE] hover:border-[#C5221F]"
                      : "border-[#C8C2B5] hover:border-[#1A1917]"
                  }`}
                >
                  <div className="space-y-3">
                    {/* Header Kartu */}
                    <div>
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <span
                          className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase border ${
                            isSuspended
                              ? "bg-[#FCE8E6] text-[#C5221F] border-[#F4B3AE]"
                              : "bg-[#EFECE6] text-[#1A1917] border-[#C8C2B5]"
                          }`}
                        >
                          {client.plan_label}
                        </span>

                        <span
                          className={`text-[11px] font-semibold flex items-center gap-1 ${
                            client.can_run ? "text-[#0F5C2B]" : "text-[#C5221F]"
                          }`}
                        >
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${
                              client.can_run ? "bg-[#0F5C2B]" : "bg-[#C5221F]"
                            }`}
                          ></span>
                          {client.status_label}
                        </span>
                      </div>

                      <h3 className="font-bold text-sm text-[#111110] leading-snug group-hover:text-[#0F5C2B] transition-colors">
                        {client.organization}
                      </h3>
                    </div>

                    {/* Rincian Kuota Repositori */}
                    <div className="rounded border border-[#EFECE6] bg-[#FAF8F5] p-2.5 text-xs space-y-1">
                      <div className="flex justify-between items-center text-[#4A4843]">
                        <span>Repositori Aktif:</span>
                        <span className="font-bold text-[#111110]">
                          {client.repo_limit < 0
                            ? `${client.active_repos}`
                            : `${client.active_repos} / ${client.repo_limit} Repositori`}
                        </span>
                      </div>
                      <div className="text-[11px] text-[#8C887B]">
                        Username: <code className="bg-[#EFECE6] px-1 py-0.2 rounded font-mono text-[#111110]">{client.id}</code>
                      </div>
                    </div>

                    <p className="text-[11px] text-[#4A4843] line-clamp-2 leading-relaxed">
                      {client.message}
                    </p>
                  </div>

                  <div className="pt-4 mt-3 border-t border-[#EFECE6]">
                    <button
                      type="button"
                      className="w-full py-2 px-3 rounded text-xs font-bold flex items-center justify-center gap-1.5 transition-all bg-[#EFECE6] hover:bg-[#DDD8CD] text-[#111110]"
                    >
                      <span>Masuk sebagai {client.organization.replace("PT ", "")}</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Masuk Manual dengan Username & Password */}
        <div className="rounded-lg border border-[#DDD8CD] bg-[#FFFFFF] p-6 shadow-sm">
          <div className="mb-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#3C3A35] flex items-center gap-1.5">
              <KeyRound className="h-4 w-4 text-[#1A1917]" />
              <span>Atau Masuk dengan Kredensial Manual</span>
            </h3>
            <p className="text-[11px] text-[#4A4843] mt-0.5">
              Untuk pengujian: Masukkan username dan password (<strong>password dibuat sama persis dengan username</strong>).
              Contoh: username <code className="bg-[#EFECE6] px-1 py-0.2 rounded font-mono text-[#111110]">bank_digital</code> dan password <code className="bg-[#EFECE6] px-1 py-0.2 rounded font-mono text-[#111110]">bank_digital</code>.
            </p>
          </div>

          {errorMsg && (
            <div className="mb-4 rounded-md border border-[#F4B3AE] bg-[#FCE8E6] p-3 text-xs text-[#C5221F] flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleManualLogin} className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
            <div>
              <label className="block text-[11px] font-bold text-[#4A4843] uppercase mb-1">
                Username Perusahaan
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-[#8C887B]">
                  <User className="h-3.5 w-3.5" />
                </div>
                <input
                  type="text"
                  value={manualUsername}
                  onChange={(e) => setManualUsername(e.target.value)}
                  placeholder="mis: bank_digital"
                  className="w-full pl-8 pr-3 py-2 text-xs rounded border border-[#C8C2B5] bg-[#FAF8F5] text-[#111110] focus:border-[#1A1917] focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-[#4A4843] uppercase mb-1">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-[#8C887B]">
                  <Lock className="h-3.5 w-3.5" />
                </div>
                <input
                  type="password"
                  value={manualPassword}
                  onChange={(e) => setManualPassword(e.target.value)}
                  placeholder="sama dengan username"
                  className="w-full pl-8 pr-3 py-2 text-xs rounded border border-[#C8C2B5] bg-[#FAF8F5] text-[#111110] focus:border-[#1A1917] focus:outline-none"
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                className="w-full py-2 px-4 rounded bg-[#1A1917] hover:bg-[#2D2C28] text-white text-xs font-bold shadow-sm transition-all flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <span>Masuk ke Dashboard</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </form>
        </div>

        {/* Footer Info */}
        <div className="text-center text-[11px] text-[#8C887B]">
          Hak Cipta &copy; 2026 SELISIH Platform — Hackathon IBM x Hacktiv8 (IT-Finance)
        </div>
      </div>
    </div>
  );
}
