"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  Play,
  FileCode,
  Check,
  RotateCcw,
  AlertCircle,
  ArrowRight,
  ExternalLink,
  X,
  Download,
  BookOpen,
  CheckSquare,
  Square,
  FileText,
} from "lucide-react";
import {
  ImpactRecord,
  DryRunResponse,
  ApplyPatchResponse,
  TestResultResponse,
  AnalysisResponse,
  OjkRegulation,
  fetchComplianceReport,
} from "@/lib/api";

interface ImpactReviewTabProps {
  records: ImpactRecord[];
  activeRole: string;
  onDryRun: () => Promise<DryRunResponse>;
  onApplyPatch: (note: string, selectedIds?: string[]) => Promise<ApplyPatchResponse>;
  onRollback?: () => Promise<any>;
  onRunTest: () => Promise<TestResultResponse>;
  onOpenAudit?: () => void;
  analysis?: AnalysisResponse | null;
  selectedReference?: OjkRegulation | null;
  selectedRegulation?: OjkRegulation | null;
  hasRunAnalysis?: boolean;
  hasRunBob?: boolean;
  onNavigateToTab?: (tab: "diff" | "bob") => void;
  canRunPatch?: boolean;
  licenseMessage?: string;
}

export default function ImpactReviewTab({
  records,
  activeRole,
  onDryRun,
  onApplyPatch,
  onRollback,
  onRunTest,
  onOpenAudit,
  analysis,
  selectedReference,
  selectedRegulation,
  hasRunAnalysis = false,
  hasRunBob = false,
  onNavigateToTab,
  canRunPatch = true,
  licenseMessage,
}: ImpactReviewTabProps) {
  const isReadOnlyRole = activeRole.includes("Read-Only");
  const meta = analysis?.analysis_meta;
  const targetRepoObj = meta?.target_repository;
  const targetRepoName = targetRepoObj?.name || targetRepoObj?.path || "mock_fintech_repo";
  const companyOrg = meta?.organization || "PT Bank Digital Nusantara";

  const acuanLabel = meta?.selected_acuan
    ? `POJK ${meta.selected_acuan.nomor || meta.selected_acuan.doc_id}`
    : selectedReference
    ? `POJK ${selectedReference.nomor || "77/2016"}`
    : "POJK 77/2016";

  const pembaruanLabel = meta?.selected_ojk
    ? `POJK ${meta.selected_ojk.nomor}/${meta.selected_ojk.tahun}`
    : selectedRegulation
    ? `POJK ${selectedRegulation.nomor}/${selectedRegulation.tahun}`
    : "POJK 22/2023";

  const [dryRunData, setDryRunData] = useState<DryRunResponse | null>(null);
  const [dryRunLoading, setDryRunLoading] = useState<boolean>(false);

  const [patchApplied, setPatchApplied] = useState<boolean>(false);
  const [applyLoading, setApplyLoading] = useState<boolean>(false);
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);
  const [rollbackLoading, setRollbackLoading] = useState<boolean>(false);
  const [rollbackSuccess, setRollbackSuccess] = useState<string | null>(null);
  const [downloadingCert, setDownloadingCert] = useState<boolean>(false);

  const [reviewerNote, setReviewerNote] = useState<string>(
    `Persetujuan kepatuhan: Penerapan perubahan batas operasional per ${pembaruanLabel} terhadap acuan ${acuanLabel}.`
  );

  const [testResult, setTestResult] = useState<TestResultResponse | null>(null);
  const [testLoading, setTestLoading] = useState<boolean>(false);

  // Pisahkan records menjadi kandidat kode dan tindakan kebijakan
  const codeRecords = records.filter(
    (r: any) => r.category !== "policy_action_required" && r.path
  );
  const policyRecords = records.filter(
    (r: any) => r.category === "policy_action_required" || !r.path
  );

  // Granular selection state untuk kandidat kode
  const [selectedChangeIds, setSelectedChangeIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (codeRecords.length > 0) {
      const initial = new Set(
        codeRecords.map((r) => r.change_id).filter(Boolean) as string[]
      );
      setSelectedChangeIds(initial);
    }
  }, [records]);

  useEffect(() => {
    setReviewerNote(
      `Persetujuan kepatuhan: Penerapan perubahan batas operasional per ${pembaruanLabel} terhadap acuan ${acuanLabel}.`
    );
  }, [acuanLabel, pembaruanLabel]);

  const toggleChangeSelection = (cid: string) => {
    setSelectedChangeIds((prev) => {
      const next = new Set(prev);
      if (next.has(cid)) next.delete(cid);
      else next.add(cid);
      return next;
    });
  };

  const selectAllChanges = () => {
    setSelectedChangeIds(
      new Set(codeRecords.map((r) => r.change_id).filter(Boolean) as string[])
    );
  };

  const deselectAllChanges = () => {
    setSelectedChangeIds(new Set());
  };

  const handleDryRun = async () => {
    setDryRunLoading(true);
    try {
      const res = await onDryRun();
      setDryRunData(res);
    } catch (err: any) {
      alert(`Gagal melakukan dry-run: ${err.message || err}`);
    } finally {
      setDryRunLoading(false);
    }
  };

  const handleConfirmApply = async () => {
    if (isReadOnlyRole) {
      alert(`Akses ditolak: Peran '${activeRole}' tidak memiliki wewenang untuk memutasi repositori bank.`);
      return;
    }
    setShowConfirmModal(false);
    setApplyLoading(true);
    setRollbackSuccess(null);
    try {
      await onApplyPatch(reviewerNote, Array.from(selectedChangeIds));
      setPatchApplied(true);
    } catch (err: any) {
      alert(`Gagal menerapkan patch: ${err.message}`);
    } finally {
      setApplyLoading(false);
    }
  };

  const handleRollback = async () => {
    if (!onRollback || isReadOnlyRole) {
      if (isReadOnlyRole) {
        alert(`Akses ditolak: Peran '${activeRole}' tidak memiliki wewenang untuk memutasi repositori bank.`);
      }
      return;
    }
    setRollbackLoading(true);
    try {
      const res = await onRollback();
      setPatchApplied(false);
      setRollbackSuccess(res?.message || "Cadangan (.bak) berhasil dipulihkan.");
      setTimeout(() => setRollbackSuccess(null), 6000);
    } catch (err: any) {
      alert(`Gagal memulihkan cadangan: ${err.message}`);
    } finally {
      setRollbackLoading(false);
    }
  };

  const handleRunTest = async () => {
    setTestLoading(true);
    try {
      const res = await onRunTest();
      setTestResult(res);
    } catch (err) {
      alert("Gagal menjalankan unit test");
    } finally {
      setTestLoading(false);
    }
  };

  const handleDownloadCertificate = async () => {
    setDownloadingCert(true);
    try {
      const cert = await fetchComplianceReport();
      const certMd =
        `# ${cert.title}\n` +
        `Nomor Berita Acara: ${cert.report_id}\n` +
        `Waktu Penerbitan: ${cert.generated_at}\n` +
        `Organisasi Klien: ${cert.organization}\n` +
        `Repositori Target: ${cert.target_repository} (${cert.target_path})\n\n` +
        `---\n\n` +
        `## 1. Regulasi Acuan vs Pembaruan\n` +
        `- Regulasi Acuan: ${cert.regulations.acuan}\n` +
        `- Regulasi Pembaruan: ${cert.regulations.pembaruan} (${cert.regulations.judul_pembaruan})\n\n` +
        `## 2. Pernyataan Persetujuan Tata Kelola (Governance Sign-off)\n` +
        `- Peran Peninjau: ${cert.governance_signoff.reviewer_role}\n` +
        `- Catatan Peninjau: ${cert.governance_signoff.reviewer_note}\n` +
        `- Waktu Penandatanganan: ${cert.governance_signoff.signed_at || "Belum ditandatangani"}\n` +
        `- Provenance Checksum: ${cert.governance_signoff.provenance_checksum}\n` +
        `- Status Tata Kelola: ${cert.governance_signoff.status}\n\n` +
        `## 3. Ringkasan Kepatuhan\n` +
        `- Total Temuan Kepatuhan: ${cert.summary.total_findings}\n` +
        `- Draf Perubahan Kode Diterapkan: ${cert.summary.code_patches_applied}\n` +
        `- Draf Perubahan Kode Ditunda: ${cert.summary.code_patches_pending}\n` +
        `- Tindakan Kebijakan / SOP Organisasi: ${cert.summary.policy_action_items}\n\n` +
        `## 4. Rincian Patch Kode yang Diterapkan\n` +
        (cert.applied_patches.length > 0
          ? cert.applied_patches.map((p: any) => `- [${p.change_id}] ${p.path}:${p.line || 1} -> \`${p.proposed_code}\``).join("\n")
          : "- Tidak ada perubahan kode yang ditulis.") +
        `\n\n` +
        `## 5. Rincian Tindakan Tata Kelola & Kebijakan Organisasi\n` +
        (cert.policy_actions.length > 0
          ? cert.policy_actions.map((p: any) => `- [${p.change_id}] ${p.ringkasan}`).join("\n")
          : "- Tidak ada kewajiban kebijakan non-kode.");

      const blob = new Blob([certMd], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Berita_Acara_Kepatuhan_${cert.report_id}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert("Gagal mengunduh Berita Acara Kepatuhan: " + (err.message || err));
    } finally {
      setDownloadingCert(false);
    }
  };

  const hasAnyPatched = records.some((r) => r.status === "already_or_no_match") || patchApplied;

  // Parsing angka test riil dari output pytest
  const stdout = testResult?.stdout || "";
  const passedMatch = stdout.match(/(\d+)\s+passed/);
  const passedCount = passedMatch ? parseInt(passedMatch[1], 10) : 0;
  const failedMatch = stdout.match(/(\d+)\s+failed/);
  const failedCount = failedMatch ? parseInt(failedMatch[1], 10) : 0;

  if (!hasRunBob) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-[#111110] tracking-tight">
              Tata Kelola &amp; Tinjauan Manusia (Human-in-the-Loop)
            </h2>
            <p className="text-xs text-[#4A4843] mt-0.5">
              Pemeriksaan statutori, simulasi dry-run tanpa mutasi disk, dan penerapan patch aman dengan pencadangan fisik (.bak).
            </p>
          </div>
          <div className="flex items-center space-x-2 text-xs">
            <span className="flex items-center gap-1.5 rounded-full bg-[#FAF8F5] border border-[#DDD8CD] px-2.5 py-1 font-semibold text-[#8C887B]">
              <span className="h-2 w-2 rounded-full bg-[#8C887B]"></span>
              Status: Menunggu Pemetaan IBM Bob (Langkah 2)
            </span>
          </div>
        </div>

        <div className="rounded-md border border-dashed border-[#DDD8CD] bg-[#FAF8F5] p-12 text-center space-y-4">
          <div className="flex justify-center">
            <div className="h-12 w-12 rounded-full bg-[#EFECE6] flex items-center justify-center text-[#1A1917] border border-[#DDD8CD]">
              <FileCode className="h-6 w-6 text-[#1A1917]" />
            </div>
          </div>
          <div className="space-y-1.5 max-w-lg mx-auto">
            <span className="inline-block rounded bg-[#EBF3FB] border border-[#AECBFA] px-2.5 py-0.5 text-[11px] font-bold text-[#1A73E8] uppercase tracking-wider mb-1">
              Langkah 2 Belum Dilakukan
            </span>
            <h3 className="text-base font-bold text-[#111110]">
              Menunggu Pemetaan Kode oleh Agen IBM Bob
            </h3>
            <p className="text-xs text-[#4A4843] leading-relaxed">
              Sistem tata kelola human-in-the-loop memerlukan hasil pemetaan dampak kode dan paket artefak dari agen IBM Bob (Tab 2) sebelum dapat meninjau dan menerapkan patch kepatuhan ke repositori fintech.
            </p>
          </div>
          {onNavigateToTab && (
            <div className="pt-2">
              <button
                onClick={() => onNavigateToTab("bob")}
                className="inline-flex items-center space-x-2 rounded bg-[#1A1917] hover:bg-[#2D2C28] px-4 py-2 text-xs font-semibold text-white transition-colors cursor-pointer shadow-sm"
              >
                <span>Menuju Tab 2: Pemetaan Kode (IBM Bob)</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner & Human Review Principle */}
      <div className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <ShieldCheck className="h-5 w-5 text-[#0F5C2B]" />
              <h2 className="text-lg font-bold text-[#111110] tracking-tight">
                Tata Kelola &amp; Tinjauan Manusia (Human-in-the-Loop Review)
              </h2>
            </div>
            <p className="mt-1 text-sm text-[#4A4843]">
              Prinsip <strong>Draft-Only</strong>: Tidak ada kode yang langsung di-deploy tanpa persetujuan manusia.
              Setiap penulisan patch mewajibkan uji coba (<em>dry-run</em>), pencatatan peran peninjau (
              <strong>{activeRole}</strong>), seleksi klausul granular, dan penciptaan salinan cadangan otomatis (
              <code>.bak.&lt;timestamp&gt;</code>).
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            {/* Step 1: Dry-Run */}
            <button
              onClick={handleDryRun}
              disabled={dryRunLoading}
              className={`flex items-center space-x-2 rounded border px-4 py-2 text-xs font-bold transition-all shadow-sm cursor-pointer ${
                dryRunData
                  ? "border-[#A3D4B0] bg-[#E6F4EA] text-[#0F5C2B]"
                  : "border-[#C8C2B5] bg-[#FFFFFF] hover:bg-[#F8F7F4] text-[#1A1917]"
              }`}
            >
              <Check className="h-3.5 w-3.5 text-[#0F5C2B]" />
              <span>{dryRunLoading ? "Menguji..." : dryRunData ? "1. Uji Coba Lolos" : "1. Uji Coba (Dry-Run)"}</span>
            </button>

            {/* Step 2: Apply Patch */}
            <button
              onClick={() => {
                if (isReadOnlyRole) {
                  alert(`Akses ditolak: Peran '${activeRole}' tidak memiliki wewenang untuk memutasi repositori bank.`);
                  return;
                }
                if (canRunPatch === false) {
                  alert(`Aksi diblokir oleh lisensi: ${licenseMessage || "Kuota repositori terlampaui"}`);
                  return;
                }
                if (selectedChangeIds.size === 0) {
                  alert("Silakan pilih minimal satu kandidat kode untuk diterapkan.");
                  return;
                }
                setShowConfirmModal(true);
              }}
              disabled={applyLoading || canRunPatch === false || isReadOnlyRole || selectedChangeIds.size === 0}
              className={`flex items-center space-x-2 rounded px-4 py-2 text-xs font-bold transition-all shadow-sm ${
                canRunPatch === false || isReadOnlyRole || selectedChangeIds.size === 0
                  ? "bg-[#DDD8CD] text-[#8C887B] cursor-not-allowed border border-[#C8C2B5]"
                  : "bg-[#1A1917] hover:bg-[#2D2C28] disabled:opacity-50 text-white cursor-pointer"
              }`}
            >
              <ShieldCheck className={`h-3.5 w-3.5 ${canRunPatch === false || isReadOnlyRole ? "text-[#8C887B]" : "text-[#A3D4B0]"}`} />
              <span>
                {applyLoading
                  ? "Menerapkan..."
                  : isReadOnlyRole
                  ? "2. Ditolak (Peran Read-Only)"
                  : canRunPatch === false
                  ? "2. Dibatasi Lisensi (Kuota Penuh)"
                  : `2. Terapkan ${selectedChangeIds.size} Patch Terpilih`}
              </span>
            </button>

            {/* Step 3: Rollback / Revert Option */}
            {onRollback && hasAnyPatched && (
              <button
                onClick={handleRollback}
                disabled={rollbackLoading || isReadOnlyRole}
                className={`flex items-center space-x-1.5 rounded border border-[#C8C2B5] px-3 py-2 text-xs font-bold transition-all shadow-sm ${
                  isReadOnlyRole
                    ? "bg-[#DDD8CD] text-[#8C887B] cursor-not-allowed"
                    : "bg-[#FAF8F5] hover:bg-[#F3EFE8] disabled:opacity-50 text-[#4A4843] cursor-pointer"
                }`}
                title={isReadOnlyRole ? "Aksi dinonaktifkan untuk peran Read-Only" : "Pulihkan file asli dari cadangan (.bak) terakhir"}
              >
                <RotateCcw className={`h-3.5 w-3.5 ${isReadOnlyRole ? "text-[#8C887B]" : "text-[#4A4843]"} ${rollbackLoading ? "animate-spin" : ""}`} />
                <span>{rollbackLoading ? "Memulihkan..." : "Pulihkan Cadangan (.bak)"}</span>
              </button>
            )}

            {/* Download Certificate */}
            <button
              onClick={handleDownloadCertificate}
              disabled={downloadingCert}
              className="flex items-center space-x-1.5 rounded border border-[#0F5C2B] bg-[#0F5C2B] hover:bg-[#0D4E24] text-white px-3.5 py-2 text-xs font-bold transition-all shadow-sm cursor-pointer disabled:opacity-50"
              title="Unduh dokumen Berita Acara Kepatuhan resmi untuk audit OJK"
            >
              <Download className={`h-3.5 w-3.5 ${downloadingCert ? "animate-spin" : ""}`} />
              <span>{downloadingCert ? "Mengunduh..." : "Berita Acara Kepatuhan"}</span>
            </button>
          </div>
        </div>

        {/* Read-Only Role Warning Banner */}
        {isReadOnlyRole && (
          <div className="mt-4 rounded-md border border-[#F4B3AE] bg-[#FCE8E6] p-3.5 text-xs text-[#C5221F] flex items-start space-x-2">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Akses Ditolak (Otorisasi RBAC): </span>
              <span>
                Peran aktif saat ini adalah <strong>{activeRole}</strong>. Pengguna dengan peran ini hanya memiliki hak akses baca (*read-only*) dan tidak diperbolehkan menerapkan patch atau memulihkan berkas repositori bank.
              </span>
            </div>
          </div>
        )}

        {/* License Gating Banner */}
        {canRunPatch === false && (
          <div className="mt-4 rounded-md border border-[#F4B3AE] bg-[#FCE8E6] p-3.5 text-xs text-[#C5221F] flex items-start space-x-2">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Aksi Penerapan Patch Dinonaktifkan: </span>
              <span>
                {licenseMessage ||
                  "Kuota repositori paket Starter telah terlampaui (5/5). Tingkatkan paket lisensi untuk menerapkan patch kepatuhan."}
              </span>
            </div>
          </div>
        )}

        {/* Dry-Run Result Banner */}
        {dryRunData && (
          <div className="mt-4 rounded-md border border-[#A3D4B0] bg-[#E6F4EA] p-4 text-xs text-[#0F5C2B] shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <span className="font-bold flex items-center gap-1.5 text-sm">
                <Check className="h-4 w-4 text-[#0F5C2B]" />
                Hasil Uji Coba (Dry-Run): {dryRunData.results.filter((r) => r.status === "dry_run_ok").length} dari{" "}
                {dryRunData.results.length} target valid dan siap ditulis
              </span>
              <span className="rounded bg-[#FFFFFF] border border-[#A3D4B0] px-2 py-0.5 font-mono text-[11px] text-[#0F5C2B] font-semibold">
                Simulasi Aman (Zero Disk Mutation)
              </span>
            </div>
            <div className="mt-3 space-y-1.5 border-t border-[#C3E6CB] pt-2">
              {dryRunData.results.map((r, i) => (
                <div key={i} className="flex items-center justify-between font-mono text-[11px]">
                  <span className="font-semibold">{r.path}</span>
                  <span className="rounded bg-[#FFFFFF] px-2 py-0.5 border border-[#A3D4B0] text-[#0F5C2B] font-bold">
                    {r.message || r.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Patch Applied Success Banner */}
        {patchApplied && (
          <div className="mt-4 rounded-md border border-[#A3D4B0] bg-[#E6F4EA] p-4 text-xs text-[#0F5C2B] shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-2">
              <ShieldCheck className="h-5 w-5 text-[#0F5C2B] shrink-0" />
              <div>
                <span className="font-bold text-sm block">Patch Kepatuhan Berhasil Diterapkan</span>
                <span className="text-[11px] text-[#2D2C28]">
                  Perubahan kode telah ditulis ke <code>{targetRepoName}</code> dan salinan cadangan fisik (<code>.bak.&lt;timestamp&gt;</code>) telah diamankan.
                </span>
              </div>
            </div>

            <div className="flex items-center space-x-2 shrink-0">
              <button
                onClick={handleDownloadCertificate}
                className="rounded bg-[#0F5C2B] hover:bg-[#0D4E24] text-white font-bold px-3 py-1.5 text-xs transition-colors shadow-sm cursor-pointer flex items-center space-x-1"
              >
                <Download className="h-3 w-3" />
                <span>Unduh Berita Acara</span>
              </button>
              {onOpenAudit && (
                <button
                  onClick={onOpenAudit}
                  className="rounded bg-[#FFFFFF] border border-[#A3D4B0] hover:bg-[#FAF8F5] text-[#0F5C2B] font-bold px-3 py-1.5 text-xs transition-colors shadow-sm cursor-pointer"
                >
                  Buka Jejak Audit
                </button>
              )}
            </div>
          </div>
        )}

        {/* Rollback Success Banner */}
        {rollbackSuccess && (
          <div className="mt-4 rounded-md border border-[#DDD8CD] bg-[#F8F7F4] p-4 text-xs text-[#1A1917] shadow-sm flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <RotateCcw className="h-4 w-4 text-[#4A4843]" />
              <span className="font-semibold">{rollbackSuccess}</span>
            </div>
            <span className="text-[10px] font-mono text-[#8C887B]">Status: Restored</span>
          </div>
        )}

        {/* Reviewer Note Input */}
        <div className="mt-5 border-t border-[#DDD8CD] pt-4">
          <label className="block text-xs font-bold text-[#3C3A35] mb-1">
            Catatan Peninjau Kepatuhan ({activeRole}):
          </label>
          <input
            type="text"
            value={reviewerNote}
            onChange={(e) => setReviewerNote(e.target.value)}
            className="w-full rounded border border-[#C8C2B5] bg-[#FAF8F5] px-3 py-2 text-xs text-[#1A1917] focus:border-[#1A1917] focus:outline-none"
          />
        </div>
      </div>

      {/* Bagian 1: Kandidat Baris Kode Terdampak (Granular Selection) */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-xs font-bold text-[#3C3A35] uppercase tracking-wider flex items-center gap-1.5">
              <FileCode className="h-4 w-4 text-[#1A1917]" />
              <span>1. Remediasi Baris Kode Otomatis ({codeRecords.length})</span>
            </h3>
            <p className="text-[11px] text-[#4A4843] mt-0.5">
              Klausul statutori yang terdeteksi pada konstanta kode dan siap ditambal secara terprogram.
            </p>
          </div>

          {codeRecords.length > 1 && (
            <div className="flex items-center space-x-2 text-xs">
              <button
                onClick={selectAllChanges}
                className="text-[11px] font-semibold text-[#1A73E8] hover:underline cursor-pointer"
              >
                Pilih Semua
              </button>
              <span className="text-[#8C887B]">|</span>
              <button
                onClick={deselectAllChanges}
                className="text-[11px] font-semibold text-[#8C887B] hover:underline cursor-pointer"
              >
                Batal Pilih
              </button>
              <span className="rounded bg-[#EFECE6] px-2 py-0.5 text-[10px] font-mono font-bold text-[#4A4843]">
                {selectedChangeIds.size}/{codeRecords.length} Terpilih
              </span>
            </div>
          )}
        </div>

        {codeRecords.length === 0 ? (
          <div className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] p-8 text-center text-xs text-[#8C887B]">
            Tidak ada kandidat baris kode yang terdampak langsung dalam repositori aktif.
          </div>
        ) : (
          codeRecords.map((rec, idx) => {
            const lineStr =
              rec.lines && rec.lines.length > 0
                ? `Baris ${rec.lines.join(", ")}`
                : rec.line
                ? `Baris ${rec.line}`
                : "Baris tidak terdeteksi";

            const isApplied = patchApplied || rec.status === "already_or_no_match";
            const isSelected = selectedChangeIds.has(rec.change_id || "");

            const statusBadge = isApplied
              ? {
                  label: "Telah Disesuaikan & Patuh",
                  bg: "bg-[#E6F4EA]",
                  text: "text-[#0F5C2B]",
                  border: "border-[#A3D4B0]",
                }
              : rec.status === "patchable"
              ? {
                  label: isSelected ? "Siap Diterapkan (Dipilih)" : "Ditunda (Tidak Dipilih)",
                  bg: isSelected ? "bg-[#FEF7E0]" : "bg-[#F8F7F4]",
                  text: isSelected ? "text-[#8A5B00]" : "text-[#8C887B]",
                  border: isSelected ? "border-[#F5D68B]" : "border-[#DDD8CD]",
                }
              : {
                  label: "File Tidak Ditemukan",
                  bg: "bg-[#FCE8E6]",
                  text: "text-[#C5221F]",
                  border: "border-[#F4B3AE]",
                };

            return (
              <div
                key={idx}
                className={`rounded-md border p-5 shadow-sm space-y-3 transition-colors ${
                  isSelected ? "border-[#1A1917] bg-[#FFFFFF]" : "border-[#DDD8CD] bg-[#FAF8F5]/80"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#DDD8CD] pb-2">
                  <div className="flex items-center space-x-3 font-mono text-xs">
                    {/* Checkbox seleksi granular */}
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleChangeSelection(rec.change_id || "")}
                      disabled={isApplied || isReadOnlyRole}
                      className="h-4 w-4 rounded border-[#C8C2B5] text-[#1A1917] focus:ring-0 cursor-pointer disabled:opacity-40"
                      title={isApplied ? "Klausul sudah diterapkan" : "Pilih untuk diterapkan"}
                    />
                    <FileCode className="h-4 w-4 text-[#1A1917]" />
                    <span className="font-bold text-[#111110]">{rec.path}</span>
                    <span className="rounded bg-[#EFECE6] px-2 py-0.5 text-[11px] font-bold text-[#1A1917] border border-[#DDD8CD]">
                      {lineStr}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {rec.change_id && (
                      <span className="font-mono text-[10px] text-[#8C887B] uppercase font-semibold">
                        {rec.change_id}
                      </span>
                    )}
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase border ${statusBadge.bg} ${statusBadge.text} ${statusBadge.border}`}
                    >
                      {statusBadge.label}
                    </span>
                  </div>
                </div>

                {rec.ringkasan && (
                  <p className="text-xs text-[#4A4843] leading-relaxed">{rec.ringkasan}</p>
                )}

                {/* Diff Preview */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                  <div className="rounded border border-[#F4B3AE] bg-[#FCE8E6] p-3">
                    <div className="text-[10px] font-bold text-[#C5221F] uppercase mb-1">
                      Kode Acuan ({acuanLabel})
                    </div>
                    <div className="text-[#C5221F] font-semibold break-all">{rec.old_code}</div>
                  </div>
                  <div className="rounded border border-[#A3D4B0] bg-[#E6F4EA] p-3">
                    <div className="text-[10px] font-bold text-[#0F5C2B] uppercase mb-1">
                      Kode Usulan Pembaruan ({pembaruanLabel})
                    </div>
                    <div className="text-[#0F5C2B] font-semibold break-all">{rec.proposed_code}</div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Bagian 2: Tindakan Kepatuhan & Tata Kelola Organisasi (Policy & SOP) */}
      {policyRecords.length > 0 && (
        <div className="space-y-4 pt-2">
          <div>
            <h3 className="text-xs font-bold text-[#3C3A35] uppercase tracking-wider flex items-center gap-1.5">
              <BookOpen className="h-4 w-4 text-[#1A73E8]" />
              <span>2. Tindakan Kepatuhan &amp; Tata Kelola Organisasi ({policyRecords.length})</span>
            </h3>
            <p className="text-[11px] text-[#4A4843] mt-0.5">
              Kewajiban regulasi prosedural dan tata kelola yang memerlukan penyesuaian SOP atau dokumen kebijakan (non-code action).
            </p>
          </div>

          <div className="space-y-3">
            {policyRecords.map((rec, idx) => (
              <div
                key={idx}
                className="rounded-md border border-[#AECBFA] bg-[#F4F8FE] p-5 shadow-sm space-y-2.5"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#D2E3FC] pb-2">
                  <div className="flex items-center space-x-2 font-mono text-xs">
                    <BookOpen className="h-4 w-4 text-[#1A73E8]" />
                    <span className="font-bold text-[#111110]">Panduan SOP Organisasional</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {rec.change_id && (
                      <span className="font-mono text-[10px] text-[#1A73E8] uppercase font-bold">
                        {rec.change_id}
                      </span>
                    )}
                    <span className="rounded bg-[#E8F0FE] border border-[#AECBFA] px-2 py-0.5 text-[10px] font-bold uppercase text-[#1A73E8]">
                      Tindakan Tata Kelola / Non-Code
                    </span>
                  </div>
                </div>

                <div className="text-xs space-y-1.5">
                  <div className="font-bold text-[#111110]">
                    Kewajiban: {rec.ringkasan}
                  </div>
                  {rec.evidence && (
                    <div className="rounded border border-[#D2E3FC] bg-[#FFFFFF] p-2.5 text-[11px] text-[#4A4843]">
                      <span className="font-bold text-[#1A73E8] block mb-0.5">Kutipan Klausul Regulasi:</span>
                      &quot;{rec.evidence}&quot;
                    </div>
                  )}
                  {rec.alasan && (
                    <p className="text-[11px] text-[#4A4843]">
                      <strong className="text-[#111110]">Rekomendasi Tindakan:</strong> {rec.alasan}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Verification & Test Runner */}
      <div className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-[#111110] tracking-tight">
              3. Verifikasi Suite Pengujian Repositori ({targetRepoName})
            </h3>
            <p className="text-xs text-[#4A4843] mt-0.5">
              Menjalankan pengujian regresi kepatuhan langsung terhadap kode sumber repositori fintech dan draf pengujian statutori Bob.
            </p>
          </div>

          <button
            onClick={handleRunTest}
            disabled={testLoading}
            className="flex items-center space-x-2 rounded bg-[#1A1917] hover:bg-[#2D2C28] disabled:opacity-50 px-4 py-2 text-xs font-semibold text-white transition-all shadow-sm cursor-pointer"
          >
            <Play className={`h-3.5 w-3.5 ${testLoading ? "animate-spin" : ""}`} />
            <span>{testLoading ? "Mengeksekusi..." : "Jalankan Pytest Sekarang"}</span>
          </button>
        </div>

        {/* Pytest Output Console */}
        {testResult && (
          <div className="mt-3 rounded bg-[#FAF8F5] border border-[#DDD8CD] p-4 font-mono text-xs max-h-60 overflow-y-auto">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2 pb-2 border-b border-[#DDD8CD]">
              <span className="text-[11px] font-bold text-[#3C3A35]">Output Konsol Pytest</span>
              <div className="flex items-center space-x-2">
                {passedCount > 0 && (
                  <span className="rounded px-2 py-0.5 text-[10px] font-bold bg-[#E6F4EA] text-[#0F5C2B] border border-[#A3D4B0]">
                    {passedCount} Passed
                  </span>
                )}
                {failedCount > 0 && (
                  <span className="rounded px-2 py-0.5 text-[10px] font-bold bg-[#FCE8E6] text-[#C5221F] border border-[#F4B3AE]">
                    {failedCount} Failed
                  </span>
                )}
                {testResult.generated_tests && (
                  <span
                    className={`rounded px-2 py-0.5 text-[10px] font-bold border ${
                      testResult.generated_tests.passed
                        ? "bg-[#E6F4EA] text-[#0F5C2B] border-[#A3D4B0]"
                        : "bg-[#FEF7E0] text-[#8A5B00] border-[#F5D68B]"
                    }`}
                  >
                    Bob Statutory Test: {testResult.generated_tests.passed ? "Lolos" : "Evaluasi"}
                  </span>
                )}
              </div>
            </div>
            {testResult.cmd && (
              <div className="text-[10px] text-[#8C887B] mb-2 font-mono break-all">
                $ {testResult.cmd}
              </div>
            )}
            <pre className="text-[#1A1917] whitespace-pre-wrap leading-relaxed">
              {testResult.stdout || testResult.stderr}
            </pre>
          </div>
        )}
      </div>

      {/* In-App Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#1A1917]/50 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg rounded-lg border border-[#C8C2B5] bg-[#FFFFFF] shadow-xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-[#DDD8CD] pb-3">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="h-5 w-5 text-[#0F5C2B]" />
                <h3 className="text-base font-bold text-[#111110]">
                  Konfirmasi Persetujuan Patch Kepatuhan
                </h3>
              </div>
              <button
                onClick={() => setShowConfirmModal(false)}
                className="text-[#8C887B] hover:text-[#111110] p-1 rounded transition-colors cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="text-xs text-[#2D2C28] space-y-3 leading-relaxed">
              <p>
                Anda akan menerapkan perubahan statutori langsung ke basis kode repositori fintech. Sesuai prinsip kehati-hatian, sistem akan membuat salinan cadangan fisik <code>.bak.&lt;timestamp&gt;</code> sebelum berkas ditulis.
              </p>

              <div className="rounded border border-[#DDD8CD] bg-[#FAF8F5] p-3.5 space-y-2 font-mono text-[11px]">
                <div>
                  <span className="text-[#8C887B]">Entitas Perusahaan:</span>{" "}
                  <strong className="text-[#111110]">{companyOrg}</strong>
                </div>
                <div>
                  <span className="text-[#8C887B]">Peran Peninjau:</span>{" "}
                  <strong className="text-[#111110]">{activeRole}</strong>
                </div>
                <div>
                  <span className="text-[#8C887B]">Target Berkas:</span>{" "}
                  <strong className="text-[#111110]">{selectedChangeIds.size} dari {codeRecords.length} lokasi terpilih</strong> di <code>{targetRepoName}</code>
                </div>
                <div>
                  <span className="text-[#8C887B]">Catatan Kepatuhan:</span>{" "}
                  <span className="text-[#111110] italic">&quot;{reviewerNote}&quot;</span>
                </div>
                <div>
                  <span className="text-[#8C887B]">Status Simulasi:</span>{" "}
                  <span className="font-bold text-[#0F5C2B]">
                    {dryRunData ? "Dry-Run Terverifikasi (Zero Disk Mutation)" : "Belum Dilakukan Dry-Run"}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-3 border-t border-[#DDD8CD]">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="rounded border border-[#C8C2B5] bg-[#FFFFFF] hover:bg-[#F8F7F4] px-4 py-2 text-xs font-semibold text-[#1A1917] transition-colors cursor-pointer"
              >
                Batal
              </button>
              <button
                onClick={handleConfirmApply}
                className="rounded bg-[#1A1917] hover:bg-[#2D2C28] px-4 py-2 text-xs font-bold text-white transition-colors cursor-pointer shadow-sm"
              >
                Konfirmasi &amp; Terapkan {selectedChangeIds.size} Patch
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
