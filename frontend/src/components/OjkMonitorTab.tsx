"use client";

import React, { useState } from "react";
import { RefreshCw, ExternalLink, Download, FileText, CheckCircle2, Clock, Filter, AlertTriangle } from "lucide-react";
import { OjkRegulation } from "@/lib/api";

interface OjkMonitorTabProps {
  regulations: OjkRegulation[];
  loading: boolean;
  onRefresh: () => void;
  onSelectForAnalysis: (reg: OjkRegulation) => void;
  onSelectAsReference: (reg: OjkRegulation) => void;
}

export default function OjkMonitorTab({
  regulations,
  loading,
  onRefresh,
  onSelectForAnalysis,
  onSelectAsReference,
}: OjkMonitorTabProps) {
  const [selectedSector, setSelectedSector] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState<string>("");

  const filtered = regulations.filter((reg) => {
    const matchesSector = selectedSector === "all" || reg.sektor_id === selectedSector;
    const matchesSearch =
      reg.judul.toLowerCase().includes(searchTerm.toLowerCase()) ||
      reg.nomor.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSector && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner / Sync Info */}
      <div className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="flex h-2.5 w-2.5 rounded-full bg-[#0F5C2B]"></span>
              <h2 className="text-lg font-bold text-[#111110] tracking-tight">
                Pemantau Regulasi Otomatis — JDIH Otoritas Jasa Keuangan (OJK)
              </h2>
            </div>
            <p className="mt-1 text-sm text-[#4A4843]">
              Sistem secara otomatis memantau portal regulasi resmi OJK (<code>jdih.ojk.go.id</code>) untuk mendeteksi
              penerbitan POJK baru di sektor Fintech, LPBBTI (P2P Lending), dan Pelindungan Konsumen secara berkala.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={onRefresh}
              disabled={loading}
              className="flex items-center space-x-2 rounded bg-[#1A1917] hover:bg-[#2D2C28] disabled:opacity-50 px-4 py-2 text-sm font-semibold text-white transition-all shadow-sm"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              <span>{loading ? "Menyinkronkan..." : "Periksa Pembaruan OJK Sekarang"}</span>
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="mt-6 flex flex-col md:flex-row items-center justify-between gap-3 border-t border-[#DDD8CD] pt-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-[#4A4843] flex items-center gap-1">
              <Filter className="h-3 w-3" /> Sektor:
            </span>
            {[
              { id: "all", label: "Semua Sektor" },
              { id: "10", label: "ITSK / Fintech / Kripto" },
              { id: "09", label: "P2P Lending (LPBBTI)" },
              { id: "04", label: "Pelindungan Konsumen" },
            ].map((sec) => (
              <button
                key={sec.id}
                onClick={() => setSelectedSector(sec.id)}
                className={`rounded px-3 py-1 text-xs font-semibold transition-colors ${
                  selectedSector === sec.id
                    ? "bg-[#1A1917] text-white"
                    : "bg-[#EFECE6] text-[#2D2C28] border border-[#C8C2B5] hover:bg-[#F3EFE8]"
                }`}
              >
                {sec.label}
              </button>
            ))}
          </div>

          <div className="w-full md:w-64">
            <input
              type="text"
              placeholder="Cari nomor atau judul POJK..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded border border-[#C8C2B5] bg-[#FFFFFF] px-3 py-1.5 text-xs text-[#1A1917] placeholder-[#8C887B] focus:border-[#1A1917] focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Regulation Table */}
      <div className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#EFECE6] text-[#111110] uppercase tracking-wider font-bold border-b border-[#DDD8CD]">
              <tr>
                <th className="px-4 py-3">Nomor & Tahun</th>
                <th className="px-4 py-3">Judul Regulasi</th>
                <th className="px-4 py-3">Sektor</th>
                <th className="px-4 py-3">Keberlakuan</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#DDD8CD]">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-[#8C887B]">
                    {loading ? "Memuat data dari JDIH OJK..." : "Tidak ada regulasi yang cocok dengan filter."}
                  </td>
                </tr>
              ) : (
                filtered.map((reg) => (
                  <tr key={reg.id} className="hover:bg-[#F8F7F4] transition-colors">
                    <td className="px-4 py-3 font-bold text-[#111110] whitespace-nowrap">
                      POJK {reg.nomor.includes(reg.tahun) ? reg.nomor : `${reg.nomor}/${reg.tahun || "-"}`}
                    </td>
                    <td className="px-4 py-3 text-[#1A1917] max-w-md">
                      <div className="line-clamp-2 font-medium">{reg.judul}</div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="rounded bg-[#EFECE6] px-2 py-0.5 text-[11px] font-semibold text-[#2D2C28] border border-[#C8C2B5]">
                        {reg.sektor}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[#4A4843] whitespace-nowrap">
                      {reg.tanggal_berlaku || "-"}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-bold border ${
                          reg.status.toLowerCase().includes("tidak")
                            ? "bg-[#FCE8E6] text-[#C5221F] border-[#F4B3AE]"
                            : "bg-[#E6F4EA] text-[#0F5C2B] border-[#A3D4B0]"
                        }`}
                      >
                        <CheckCircle2 className="h-3 w-3" />
                        {reg.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end space-x-1.5">
                        {reg.detail_url && (
                          <a
                            href={reg.detail_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rounded p-1.5 text-[#4A4843] hover:text-[#111110] hover:bg-[#EFECE6]"
                            title="Buka Halaman Resmi JDIH OJK"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        )}
                        {reg.download_url && (
                          <a
                            href={reg.download_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rounded p-1.5 text-[#0f62fe] hover:text-[#0043ce] hover:bg-[#EBF3FB]"
                            title="Unduh Berkas PDF Asli OJK"
                          >
                            <Download className="h-3.5 w-3.5" />
                          </a>
                        )}
                        <button
                          onClick={() => onSelectAsReference(reg)}
                          className="rounded border border-[#C8C2B5] bg-[#FFFFFF] hover:bg-[#F3EFE8] text-[#1A1917] px-2 py-1 text-xs font-semibold transition-colors shadow-sm"
                          title="Pilih regulasi ini sebagai acuan terdahulu di Tab 1"
                        >
                          Set Acuan
                        </button>
                        <button
                          onClick={() => onSelectForAnalysis(reg)}
                          className="rounded border border-[#1A1917] bg-[#1A1917] hover:bg-[#2D2C28] text-white px-2.5 py-1 text-xs font-semibold transition-colors shadow-sm"
                          title="Analisis dampak regulasi ini terhadap aturan acuan di Tab 1"
                        >
                          Analisis Dampak
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
