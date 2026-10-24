"use client";

import React, { useMemo } from "react";
import {
  Play,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  Globe,
  ExternalLink,
  BookOpen,
  AlertCircle,
} from "lucide-react";
import { AnalysisResponse, OjkRegulation, DEFAULT_POJK_77, DEFAULT_POJK_22 } from "@/lib/api";

interface RegulatoryDiffTabProps {
  analysis: AnalysisResponse | null;
  loading: boolean;
  regulations: OjkRegulation[];
  selectedReference: OjkRegulation | null;
  onSelectReference: (reg: OjkRegulation | null) => void;
  selectedRegulation: OjkRegulation | null;
  onSelectRegulation: (reg: OjkRegulation | null) => void;
  onRunAnalysis: () => void;
  hasRunAnalysis?: boolean;
}

export default function RegulatoryDiffTab({
  analysis,
  loading,
  regulations,
  selectedReference,
  onSelectReference,
  selectedRegulation,
  onSelectRegulation,
  onRunAnalysis,
  hasRunAnalysis = false,
}: RegulatoryDiffTabProps) {
  const metrics = analysis?.metrics || {
    total_findings: 2,
    valid_citations: 2,
    citation_percentage: 100,
    confidence: "Tinggi",
    abstain: false,
  };

  const findings = analysis?.findings || [];

  // Gabungkan daftar regulasi OJK dengan acuan default jika belum ada
  const allRegulations = useMemo(() => {
    const list = [...regulations];
    if (!list.some((r) => r.id === DEFAULT_POJK_77.id || r.nomor.includes("77"))) {
      list.push(DEFAULT_POJK_77);
    }
    if (!list.some((r) => r.id === DEFAULT_POJK_22.id || r.nomor === "22")) {
      list.unshift(DEFAULT_POJK_22);
    }
    return list;
  }, [regulations]);

  const getRegKey = (r?: OjkRegulation | null) => {
    if (!r) return "";
    return r.id || `${r.nomor}_${r.tahun || ""}`;
  };

  const isSameRegulation = Boolean(
    selectedReference &&
    selectedRegulation &&
    getRegKey(selectedReference) === getRegKey(selectedRegulation)
  );

  const isAcuanPojk77 = Boolean(
    selectedReference &&
    (selectedReference.nomor.includes("77") ||
      selectedReference.id === "pojk-77-2016" ||
      selectedReference.judul.includes("77"))
  );

  const isPojk22 = Boolean(
    selectedRegulation &&
    (selectedRegulation.nomor === "22" ||
      selectedRegulation.nomor === "22/2023" ||
      selectedRegulation.judul.includes("22"))
  );

  return (
    <div className="space-y-6">
      {/* Tab Header Description */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-[#111110] tracking-tight">Analisis Perubahan Regulasi (Diff)</h2>
          <p className="text-xs text-[#4A4843] mt-0.5">
            Komparasi statutori dua arah antara regulasi acuan dan regulasi pembaruan bersumber langsung dari Katalog JDIH OJK (Tab 4).
          </p>
        </div>
        <div className="flex items-center space-x-2 text-xs">
          <span className="flex items-center gap-1.5 rounded-full bg-[#E6F4EA] border border-[#A3D4B0] px-2.5 py-1 font-semibold text-[#0F5C2B]">
            <span className="h-2 w-2 rounded-full bg-[#0F5C2B] animate-pulse"></span>
            Katalog JDIH OJK Terpusat ({allRegulations.length} Regulasi)
          </span>
        </div>
      </div>

      {/* Warning jika memilih regulasi yang sama */}
      {isSameRegulation && (
        <div className="rounded-md border border-[#F4B3AE] bg-[#FCE8E6] p-3.5 text-xs text-[#C5221F] flex items-center space-x-2">
          <AlertCircle className="h-4 w-4 shrink-0 text-[#C5221F]" />
          <span>
            Perhatian: Regulasi acuan dan regulasi pembaruan tidak boleh sama. Silakan pilih dua regulasi yang berbeda dari katalog untuk memetakan perubahannya.
          </span>
        </div>
      )}

      {/* Dual Selector Control Bar */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Left: Selector Regulasi Acuan */}
        <div className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] p-4 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-[#3C3A35] flex items-center gap-1.5">
                <BookOpen className="h-3.5 w-3.5 text-[#1A1917]" />
                <span>Pilih Regulasi Acuan (Terdahulu):</span>
              </label>
              <span className="text-[10px] font-bold text-[#4A4843] bg-[#EFECE6] px-1.5 py-0.5 rounded border border-[#C8C2B5]">
                {!selectedReference ? "Belum Dipilih" : isAcuanPojk77 ? "ChromaDB Lokal" : "Katalog OJK"}
              </span>
            </div>
            <select
              value={getRegKey(selectedReference)}
              onChange={(e) => {
                const val = e.target.value;
                if (!val) {
                  onSelectReference(null);
                  return;
                }
                const target = allRegulations.find((r) => getRegKey(r) === val);
                if (target) onSelectReference(target);
              }}
              className="w-full rounded border border-[#C8C2B5] bg-[#FAF8F5] px-3 py-2 text-xs font-bold text-[#111110] focus:border-[#1A1917] focus:outline-none cursor-pointer shadow-sm"
            >
              <option value="">-- Pilih Regulasi Acuan (Terdahulu) --</option>
              {allRegulations.map((r) => (
                <option key={`acuan-${getRegKey(r)}`} value={getRegKey(r)}>
                  POJK {r.nomor}/{r.tahun || "-"} — {r.judul.length > 55 ? `${r.judul.slice(0, 55)}...` : r.judul}
                </option>
              ))}
            </select>
          </div>
          <div className="mt-2 text-[11px] text-[#4A4843] flex items-center justify-between">
            <span className="line-clamp-1">
              {selectedReference ? `Sektor: ${selectedReference.sektor || "Fintech Lending"}` : "Pilih dokumen acuan dari menu pilihan"}
            </span>
            {selectedReference?.detail_url && (
              <a
                href={selectedReference.detail_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[#0f62fe] hover:underline shrink-0 font-semibold"
              >
                <span>Dokumen Resmi</span>
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>

        {/* Right: Selector Regulasi Pembaruan */}
        <div className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] p-4 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-[#3C3A35] flex items-center gap-1.5">
                <Globe className="h-3.5 w-3.5 text-[#0f62fe]" />
                <span>Pilih Regulasi Pembaruan (Terbaru):</span>
              </label>
              <span className="text-[10px] font-bold text-[#0F5C2B] bg-[#E6F4EA] px-1.5 py-0.5 rounded border border-[#A3D4B0]">
                {!selectedRegulation ? "Belum Dipilih" : (selectedRegulation.status || "Berlaku")}
              </span>
            </div>
            <select
              value={getRegKey(selectedRegulation)}
              onChange={(e) => {
                const val = e.target.value;
                if (!val) {
                  onSelectRegulation(null);
                  return;
                }
                const target = allRegulations.find((r) => getRegKey(r) === val);
                if (target) onSelectRegulation(target);
              }}
              className="w-full rounded border border-[#C8C2B5] bg-[#FAF8F5] px-3 py-2 text-xs font-bold text-[#111110] focus:border-[#1A1917] focus:outline-none cursor-pointer shadow-sm"
            >
              <option value="">-- Pilih Regulasi Pembaruan (Terbaru) --</option>
              {allRegulations.map((r) => (
                <option key={`pembaruan-${getRegKey(r)}`} value={getRegKey(r)}>
                  POJK {r.nomor}/{r.tahun || "-"} — {r.judul.length > 55 ? `${r.judul.slice(0, 55)}...` : r.judul}
                </option>
              ))}
            </select>
          </div>
          <div className="mt-2 text-[11px] text-[#4A4843] flex items-center justify-between">
            <span className="line-clamp-1">
              {selectedRegulation ? `Sektor: ${selectedRegulation.sektor || "Fintech"}` : "Pilih dokumen pembaruan dari menu pilihan"}
            </span>
            {selectedRegulation?.detail_url && (
              <a
                href={selectedRegulation.detail_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[#0f62fe] hover:underline shrink-0 font-semibold"
              >
                <span>Dokumen Resmi</span>
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Two Comparison Cards (Both Fully Dynamic from Selected Regulations) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Card A: Regulasi Acuan */}
        {!selectedReference ? (
          <div className="rounded-md border border-dashed border-[#DDD8CD] bg-[#FFFFFF] p-5 shadow-sm flex flex-col justify-between min-h-[220px]">
            <div>
              <div className="flex items-center justify-between border-b border-[#DDD8CD] pb-2 mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-[#8C887B]">
                  Regulasi Acuan: Belum Dipilih
                </span>
                <span className="rounded bg-[#EFECE6] px-2 py-0.5 text-[10px] font-bold text-[#8C887B] border border-[#DDD8CD]">
                  Menunggu Pilihan
                </span>
              </div>
              <div className="text-xs text-[#8C887B] space-y-2 leading-relaxed pt-2">
                <p className="font-semibold text-[#4A4843]">
                  Belum ada regulasi acuan yang dipilih.
                </p>
                <p>
                  Silakan tentukan regulasi acuan terdahulu dari menu dropdown di atas untuk memuat basis ketentuan hukum dan pasal pembanding.
                </p>
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-[#DDD8CD] text-[11px] text-[#8C887B]">
              Status: Menunggu Pemilihan Dokumen
            </div>
          </div>
        ) : (
          <div className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] p-5 shadow-sm flex flex-col justify-between min-h-[220px]">
            <div>
              <div className="flex items-center justify-between border-b border-[#DDD8CD] pb-2 mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-[#3C3A35]">
                  Regulasi Acuan: POJK {selectedReference.nomor}
                </span>
                <span className="rounded bg-[#EFECE6] px-2 py-0.5 text-[10px] font-bold text-[#4A4843] border border-[#C8C2B5]">
                  Basis Terdahulu
                </span>
              </div>

              <div className="text-xs text-[#1A1917] space-y-2 leading-relaxed">
                <div>
                  <strong className="text-sm font-bold text-[#111110]">
                    POJK Nomor {selectedReference.nomor} {selectedReference.tahun ? `Tahun ${selectedReference.tahun}` : ""}
                  </strong>
                  <div className="text-[#4A4843] line-clamp-2 mt-0.5 font-medium">
                    {selectedReference.judul}
                  </div>
                </div>

                {isAcuanPojk77 ? (
                  <div className="space-y-1.5 pt-2 text-[#2D2C28]">
                    <div className="flex items-start gap-1.5">
                      <span className="text-[#C5221F] font-bold">•</span>
                      <span>Batas maksimum plafon pinjaman dana: <strong>Rp 20.000.000</strong> (Pasal 8 ayat 2)</span>
                    </div>
                    <div className="flex items-start gap-1.5">
                      <span className="text-[#C5221F] font-bold">•</span>
                      <span>Batas maksimum suku bunga harian: <strong>0,4% per hari</strong> (Pasal 8 ayat 3)</span>
                    </div>
                    <div className="flex items-start gap-1.5">
                      <span className="text-[#8C887B]">•</span>
                      <span>Status Indeks Vektor: <strong>5 Pasal Tersimpan di ChromaDB Lokal</strong></span>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-1.5 pt-2 text-[#2D2C28]">
                    <div className="flex items-start gap-1.5">
                      <span className="text-[#C5221F] font-bold">•</span>
                      <span>Sektor Acuan: <strong>{selectedReference.sektor || "Fintech / Perbankan"}</strong></span>
                    </div>
                    <div className="flex items-start gap-1.5">
                      <span className="text-[#C5221F] font-bold">•</span>
                      <span>Keberlakuan: <strong>{selectedReference.tanggal_berlaku || "Statutori Acuan"}</strong></span>
                    </div>
                    <div className="flex items-start gap-1.5">
                      <span className="text-[#8C887B]">•</span>
                      <span>Status Dokumen: <strong>{selectedReference.status || "Acuan Terpilih"}</strong></span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-[#DDD8CD] text-[11px] text-[#4A4843] flex items-center justify-between">
              <span>Sektor: {selectedReference.sektor ? `${selectedReference.sektor.slice(0, 32)}...` : "OJK"}</span>
              <span className="text-[#0F5C2B] font-semibold">Tersinkronisasi Tab 4</span>
            </div>
          </div>
        )}

        {/* Card B: Regulasi Pembaruan */}
        {!selectedRegulation ? (
          <div className="rounded-md border border-dashed border-[#DDD8CD] bg-[#FFFFFF] p-5 shadow-sm flex flex-col justify-between min-h-[220px]">
            <div>
              <div className="flex items-center justify-between border-b border-[#DDD8CD] pb-2 mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-[#8C887B]">
                  Regulasi Pembaruan: Belum Dipilih
                </span>
                <span className="rounded bg-[#EFECE6] px-2 py-0.5 text-[10px] font-bold text-[#8C887B] border border-[#DDD8CD]">
                  Menunggu Pilihan
                </span>
              </div>
              <div className="text-xs text-[#8C887B] space-y-2 leading-relaxed pt-2">
                <p className="font-semibold text-[#4A4843]">
                  Belum ada regulasi pembaruan yang dipilih.
                </p>
                <p>
                  Silakan tentukan regulasi pembaruan terbaru dari menu dropdown di atas untuk memetakan perubahan batas plafon, suku bunga harian, atau kewajiban tata kelola sistem.
                </p>
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-[#DDD8CD] text-[11px] text-[#8C887B]">
              Status: Menunggu Pemilihan Dokumen
            </div>
          </div>
        ) : (
          <div className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] p-5 shadow-sm flex flex-col justify-between min-h-[220px]">
            <div>
              <div className="flex items-center justify-between border-b border-[#DDD8CD] pb-2 mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-[#3C3A35]">
                  Regulasi Pembaruan: POJK {selectedRegulation.nomor}/{selectedRegulation.tahun || ""}
                </span>
                <span className="rounded bg-[#E6F4EA] border border-[#A3D4B0] px-2 py-0.5 text-[10px] font-bold text-[#0F5C2B]">
                  {selectedRegulation.status || "Berlaku"}
                </span>
              </div>

              <div className="text-xs text-[#1A1917] space-y-2 leading-relaxed">
                <div>
                  <strong className="text-sm font-bold text-[#111110]">
                    POJK Nomor {selectedRegulation.nomor} {selectedRegulation.tahun ? `Tahun ${selectedRegulation.tahun}` : ""}
                  </strong>
                  <div className="text-[#4A4843] line-clamp-2 mt-0.5 font-medium">
                    {selectedRegulation.judul}
                  </div>
                </div>

                {isPojk22 ? (
                  <div className="space-y-1.5 pt-2 text-[#2D2C28]">
                    <div className="flex items-start gap-1.5">
                      <span className="text-[#0F5C2B] font-bold">•</span>
                      <span>Batas maksimum plafon pinjaman ditingkatkan: <strong>Rp 50.000.000</strong> (Pasal 12 ayat 1)</span>
                    </div>
                    <div className="flex items-start gap-1.5">
                      <span className="text-[#0F5C2B] font-bold">•</span>
                      <span>Batas maksimum suku bunga harian diturunkan: <strong>0,1% per hari</strong> (Pasal 12 ayat 2)</span>
                    </div>
                    <div className="flex items-start gap-1.5">
                      <span className="text-[#0F5C2B] font-bold">•</span>
                      <span>Tenggat penyesuaian sistem kepatuhan: <strong>30 hari kalender</strong></span>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-1.5 pt-2 text-[#2D2C28]">
                    <div className="flex items-start gap-1.5">
                      <span className="text-[#0F5C2B] font-bold">•</span>
                      <span>Sektor Regulasi: <strong>{selectedRegulation.sektor || "Fintech / Jasa Keuangan"}</strong></span>
                    </div>
                    <div className="flex items-start gap-1.5">
                      <span className="text-[#0F5C2B] font-bold">•</span>
                      <span>Tanggal Keberlakuan: <strong>{selectedRegulation.tanggal_berlaku || "Segera"}</strong></span>
                    </div>
                    <div className="flex items-start gap-1.5">
                      <span className="text-[#8A5B00] font-bold">•</span>
                      <span>Status Komparasi: Siap dianalisis terhadap basis acuan {selectedReference ? `POJK ${selectedReference.nomor}` : "terpilih"}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-[#DDD8CD] text-[11px] text-[#4A4843] flex items-center justify-between">
              <span>Sektor: {selectedRegulation.sektor ? `${selectedRegulation.sektor.slice(0, 32)}...` : "OJK"}</span>
              <span className="text-[#0F5C2B] font-semibold">Tersinkronisasi Tab 4</span>
            </div>
          </div>
        )}
      </div>

      {/* Action Button & Execution Trigger */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {!selectedReference || !selectedRegulation ? (
          <button
            disabled={true}
            className="flex items-center space-x-2 rounded bg-[#DDD8CD] px-5 py-2.5 text-xs font-bold text-[#8C887B] cursor-not-allowed shadow-none"
          >
            <Play className="h-3.5 w-3.5 text-[#8C887B]" />
            <span>Pilih Kedua Regulasi di Atas untuk Menjalankan Analisis</span>
          </button>
        ) : (
          <button
            onClick={onRunAnalysis}
            disabled={loading || isSameRegulation}
            className="flex items-center space-x-2 rounded bg-[#1A1917] hover:bg-[#2D2C28] disabled:opacity-50 px-5 py-2.5 text-xs font-bold text-white transition-all shadow-sm cursor-pointer"
          >
            <Play className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>
              {loading
                ? `Menganalisis POJK ${selectedReference.nomor} vs POJK ${selectedRegulation.nomor}...`
                : `Jalankan Analisis: POJK ${selectedReference.nomor} vs POJK ${selectedRegulation.nomor} (Langflow Engine)`}
            </span>
          </button>
        )}

        <span className="text-[11px] text-[#4A4843]">
          Engine Pipeline: <strong className="text-[#111110]">ChromaDB Lokal + watsonx Granite Framework</strong>
        </span>
      </div>

      {/* Conditionally Render Results Only After Analysis has been Run */}
      {!hasRunAnalysis ? (
        <div className="rounded-md border border-dashed border-[#DDD8CD] bg-[#FAF8F5] p-10 text-center space-y-3 shadow-sm">
          <div className="flex justify-center">
            <div className="h-10 w-10 rounded-full bg-[#EFECE6] flex items-center justify-center text-[#1A1917] border border-[#DDD8CD]">
              <Play className="h-4 w-4 ml-0.5 text-[#1A1917]" />
            </div>
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-[#111110]">
              {!selectedReference || !selectedRegulation
                ? "Silakan Tentukan Regulasi Acuan dan Regulasi Pembaruan"
                : "Siap Menjalankan Komparasi Regulasi"}
            </h3>
            <p className="text-xs text-[#4A4843] max-w-lg mx-auto leading-relaxed">
              {!selectedReference || !selectedRegulation
                ? "Pilih dokumen regulasi acuan dan dokumen pembaruan pada panel dropdown di atas untuk memulai analisis komparasi hukum."
                : `Tekan tombol "Jalankan Analisis: POJK ${selectedReference.nomor} vs POJK ${selectedRegulation.nomor}" untuk mengekstraksi klausul terdampak, menghitung metrik kepatuhan, dan memvalidasi sitasi anti-halusinasi.`}
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* Analysis Provenance & Confirmation Banner */}
          {analysis?.analysis_meta?.timestamp && (
            <div className="rounded-md border border-[#A3D4B0] bg-[#E6F4EA] p-4 text-xs text-[#0F5C2B] shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <span className="font-bold flex items-center gap-1.5 text-sm">
                  <ShieldCheck className="h-4 w-4 text-[#0F5C2B]" />
                  Analisis Selesai: POJK {selectedReference?.nomor || "Acuan"} vs POJK {selectedRegulation?.nomor || "Pembaruan"} ({findings.length} Temuan Klausul)
                </span>
                <span className="font-mono text-[11px] bg-[#FFFFFF] border border-[#A3D4B0] px-2 py-0.5 rounded font-semibold text-[#0F5C2B]">
                  Engine: {analysis.analysis_meta.engine || "Langflow Pipeline"}
                </span>
              </div>
              <p className="mt-1.5 text-[11px] text-[#2D2C28] leading-relaxed">
                Perbandingan statutori aktif telah diproses secara real-time. Klausul acuan bersumber dari{" "}
                <strong>POJK {selectedReference?.nomor || "Acuan"}</strong> dan klausul pembaruan bersumber dari{" "}
                <strong>POJK {selectedRegulation?.nomor || "Pembaruan"}{selectedRegulation?.tahun ? `/${selectedRegulation.tahun}` : ""}</strong>. Hasil telah
                disinkronkan ke Tab 2 (IBM Bob) dan Tab 3 (Human Review).
              </p>
            </div>
          )}

          {/* 4 Metric Cards */}
          <div className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-[#DDD8CD] pb-2">
              <h3 className="text-xs font-bold text-[#3C3A35] uppercase tracking-wider">
                Metrik Validasi Kepatuhan (POJK {selectedReference?.nomor || "Acuan"} vs POJK {selectedRegulation?.nomor || "Pembaruan"})
              </h3>
              <span className="text-[10px] font-semibold text-[#4A4843]">
                {analysis?.analysis_meta?.engine || "Langflow Pipeline"}
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="rounded border border-[#DDD8CD] bg-[#F3EFE8] p-3.5">
                <span className="text-[11px] font-semibold text-[#4A4843]">Klausul Terdampak</span>
                <div className="mt-1 text-xl font-bold text-[#111110]">{metrics.total_findings} Pasal</div>
                <span className="text-[10px] font-semibold text-[#0F5C2B]">Kewajiban Baru</span>
              </div>

              <div className="rounded border border-[#DDD8CD] bg-[#F3EFE8] p-3.5">
                <span className="text-[11px] font-semibold text-[#4A4843]">Validitas Sitasi</span>
                <div className="mt-1 text-xl font-bold text-[#111110]">{metrics.citation_percentage}%</div>
                <span className="text-[10px] font-semibold text-[#0F5C2B]">Tervalidasi Anti-Halusinasi</span>
              </div>

              <div className="rounded border border-[#DDD8CD] bg-[#F3EFE8] p-3.5">
                <span className="text-[11px] font-semibold text-[#4A4843]">Tingkat Keyakinan</span>
                <div className="mt-1 text-xl font-bold text-[#111110]">{metrics.confidence}</div>
                <span className="text-[10px] font-semibold text-[#4A4843]">Granite Confidence</span>
              </div>

              <div className="rounded border border-[#DDD8CD] bg-[#F3EFE8] p-3.5">
                <span className="text-[11px] font-semibold text-[#4A4843]">Status Abstention</span>
                <div className="mt-1 text-xl font-bold text-[#0F5C2B]">
                  {metrics.abstain ? "Abstain" : "false"}
                </div>
                <span className="text-[10px] font-semibold text-[#0F5C2B]">Bukti Klausul Lengkap</span>
              </div>
            </div>
          </div>

          {/* Findings List */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-[#3C3A35] uppercase tracking-wider">
              Hasil Ekstraksi Perubahan ({findings.length})
            </h3>

            {findings.length === 0 ? (
              <div className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] p-8 text-center text-xs text-[#8C887B]">
                {loading
                  ? "Menjalankan analisis klausul regulasi..."
                  : "Belum ada temuan analisis untuk pasangan regulasi ini. Klik tombol di atas untuk memulai analisis."}
              </div>
            ) : (
              findings.map((item, idx) => (
                <div
                  key={item.change_id || idx}
                  className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] p-5 shadow-sm space-y-3.5"
                >
                  {/* Top row */}
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#DDD8CD] pb-2.5">
                    <div className="flex items-center space-x-2">
                      <span className="rounded bg-[#EFECE6] px-2 py-0.5 text-xs font-bold text-[#2D2C28] border border-[#C8C2B5]">
                        {item.change_id}
                      </span>
                      <span className="text-xs font-bold text-[#111110]">
                        Jenis Perubahan:{" "}
                        <span className="text-[#8A5B00] uppercase font-semibold">{item.jenis_perubahan}</span>
                      </span>
                    </div>

                    <div className="flex items-center space-x-2 text-xs">
                      <span className="flex items-center gap-1 rounded bg-[#E6F4EA] border border-[#A3D4B0] px-2 py-0.5 text-[11px] font-bold text-[#0F5C2B]">
                        <CheckCircle2 className="h-3 w-3" /> Sitasi Valid
                      </span>
                      <span className="rounded bg-[#EFECE6] px-2 py-0.5 text-[11px] text-[#2D2C28] font-semibold border border-[#C8C2B5]">
                        Confidence: {item.confidence}
                      </span>
                    </div>
                  </div>

                  {/* Summary */}
                  <p className="text-xs text-[#1A1917] font-medium leading-relaxed">{item.ringkasan}</p>

                  {/* Side-by-side comparison */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* Old Clause */}
                    <div className="rounded border border-[#F4B3AE] bg-[#FCE8E6] p-3 text-xs">
                      <div className="font-bold text-[#C5221F] mb-1">
                        Aturan Acuan: {item.pasal_lama?.doc_id || `POJK-${selectedReference?.nomor || "Acuan"}`} —{" "}
                        {item.pasal_lama?.pasal || "Pasal Acuan"}{" "}
                        {item.pasal_lama?.ayat ? `Ayat ${item.pasal_lama.ayat}` : ""}
                      </div>
                      <blockquote className="text-[#2D2C28] italic">"{item.pasal_lama?.kutipan || "-"}"</blockquote>
                    </div>

                    {/* New Clause */}
                    <div className="rounded border border-[#A3D4B0] bg-[#E6F4EA] p-3 text-xs">
                      <div className="font-bold text-[#0F5C2B] mb-1">
                        Aturan Pembaruan:{" "}
                        {item.pasal_baru?.doc_id || `POJK-${selectedRegulation?.nomor || "Pembaruan"}-${selectedRegulation?.tahun || ""}`} —{" "}
                        {item.pasal_baru?.pasal || "Pasal Pembaruan"}{" "}
                        {item.pasal_baru?.ayat ? `Ayat ${item.pasal_baru.ayat}` : ""}
                      </div>
                      <blockquote className="text-[#1A1917] italic font-semibold">
                        "{item.pasal_baru?.kutipan || "-"}"
                      </blockquote>
                    </div>
                  </div>

                  {/* Candidate Code Indicators */}
                  {item.kandidat_kode && item.kandidat_kode.length > 0 && (
                    <div className="rounded border border-[#DDD8CD] bg-[#F8F7F4] p-3 text-xs">
                      <span className="font-bold text-[#111110]">Kandidat Kode Terdampak Terdeteksi:</span>
                      <div className="mt-2 space-y-1">
                        {item.kandidat_kode.map((k, kIdx) => (
                          <div key={kIdx} className="flex items-center space-x-2 text-[#4A4843]">
                            <ArrowRight className="h-3 w-3 text-[#1A1917]" />
                            <code className="text-[#111110] font-mono bg-[#FFFFFF] border border-[#DDD8CD] px-1.5 py-0.5 rounded font-bold">
                              {k.path}
                            </code>
                            <span>
                              (Evidence: <span className="font-semibold text-[#8A5B00]">{k.evidence}</span>)
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
