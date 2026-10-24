"use client";

import React, { useState } from "react";
import {
  Terminal,
  Play,
  Copy,
  FileCode,
  Check,
  ShieldCheck,
  CheckCircle2,
  ArrowRight,
  RotateCcw,
  Download,
  AlertCircle,
} from "lucide-react";
import { AnalysisResponse, OjkRegulation } from "@/lib/api";

interface BobShellConsoleTabProps {
  artifacts: Array<{ name: string; size: number; content: string }>;
  onRefreshArtifacts: () => void;
  analysis: AnalysisResponse | null;
  selectedReference: OjkRegulation | null;
  selectedRegulation: OjkRegulation | null;
  hasRunAnalysis?: boolean;
  hasRunBob?: boolean;
  onBobExecuted?: () => void;
  mcpConnected?: boolean;
  onNavigateToReview?: () => void;
}

interface LogEntry {
  type: string;
  tool?: string;
  msg: string;
}

export default function BobShellConsoleTab({
  artifacts,
  onRefreshArtifacts,
  analysis,
  selectedReference,
  selectedRegulation,
  hasRunAnalysis = false,
  hasRunBob = false,
  onBobExecuted,
  mcpConnected = true,
  onNavigateToReview,
}: BobShellConsoleTabProps) {
  const [running, setRunning] = useState<boolean>(false);
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      type: "ready",
      msg: "[IBM Bob Shell] Lingkungan CLI terhubung ke jembatan MCP lokal (127.0.0.1:8765). Siap mengeksekusi agen pada hasil analisis Tab 1.",
    },
  ]);
  const [activeArtifactTab, setActiveArtifactTab] = useState<string>("proposed_patch.diff");
  const [copied, setCopied] = useState<boolean>(false);

  const hasFindings = Boolean(
    hasRunAnalysis &&
    selectedReference &&
    selectedRegulation &&
    analysis &&
    analysis.findings &&
    analysis.findings.length > 0
  );
  const refLabel = selectedReference?.nomor ? `POJK ${selectedReference.nomor}` : null;
  const ojkLabel = selectedRegulation?.nomor
    ? `POJK ${selectedRegulation.nomor}${selectedRegulation.tahun ? `/${selectedRegulation.tahun}` : ""}`
    : null;
  const findingsCount = hasFindings ? (analysis?.findings?.length || 0) : 0;
  const isHandoffDone = Boolean(hasRunBob && logs.some((l) => l.type === "success"));

  const startBobAgent = () => {
    if (!hasFindings) {
      alert("Belum ada data temuan analisis untuk sesi ini. Silakan pilih regulasi acuan dan regulasi pembaruan, lalu tekan 'Jalankan Analisis' di Tab 1 terlebih dahulu.");
      return;
    }
    setRunning(true);
    setLogs([
      {
        type: "init",
        msg: `[IBM Bob Shell] Memulai sesi interaktif penalaran agen AI untuk ${refLabel || "Regulasi Acuan"} vs ${ojkLabel || "Regulasi Target"}...`,
      },
    ]);

    const eventSource = new EventSource("http://127.0.0.1:8000/api/bob/stream");

    eventSource.onmessage = (event) => {
      try {
        const data: LogEntry = JSON.parse(event.data);
        setLogs((prev) => [...prev, data]);
        if (data.type === "success") {
          onBobExecuted?.();
        }
      } catch (err) {
        console.error("Gagal parse SSE:", err);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      setRunning(false);
      onRefreshArtifacts();
      onBobExecuted?.();
    };
  };

  const clearLogs = () => {
    setLogs([
      {
        type: "ready",
        msg: "[IBM Bob Shell] Lingkungan CLI terhubung ke jembatan MCP lokal (127.0.0.1:8765). Siap mengeksekusi agen pada hasil analisis Tab 1.",
      },
    ]);
  };

  const currentArtifact = artifacts.find((a) => a.name === activeArtifactTab);

  const copyContent = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadArtifact = (filename: string, content: string) => {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Execution Control */}
      <div className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="flex h-2.5 w-2.5 rounded-full bg-[#1A1917] animate-pulse"></span>
              <h2 className="text-lg font-bold text-[#111110] tracking-tight">
                Konsol Agen IBM Bob Shell (In-Dashboard Runner)
              </h2>
            </div>
            <p className="mt-1 text-sm text-[#4A4843]">
              Mengeksekusi agen IBM Bob secara <em>headless</em> langsung di dalam dashboard web. Agen berinteraksi dengan repositori
              fintech lokal melalui protokol <strong>Model Context Protocol (MCP)</strong> tanpa perlu membuka aplikasi desktop.
            </p>
          </div>

          <button
            onClick={startBobAgent}
            disabled={running || !hasFindings}
            className={`flex items-center space-x-2 rounded px-5 py-2.5 text-sm font-semibold transition-all shadow-sm shrink-0 ${
              !hasFindings
                ? "bg-[#DDD8CD] text-[#8C887B] cursor-not-allowed border border-[#C8C2B5]"
                : "bg-[#1A1917] hover:bg-[#2D2C28] disabled:opacity-50 text-white cursor-pointer"
            }`}
          >
            <Play className={`h-4 w-4 ${running ? "animate-spin" : ""}`} />
            <span>
              {running
                ? "Agen Sedang Bekerja..."
                : !hasFindings
                ? "Menunggu Analisis Tab 1"
                : "Jalankan IBM Bob"}
            </span>
          </button>
        </div>
      </div>

      {/* Guarded Warning if Tab 1 has no findings */}
      {!hasFindings && (
        <div className="rounded-md border border-[#F4B3AE] bg-[#FCE8E6] p-4 text-xs text-[#C5221F] flex items-center space-x-2.5 shadow-sm">
          <AlertCircle className="h-4 w-4 shrink-0 text-[#C5221F]" />
          <span>
            Perhatian: Analisis komparasi regulasi belum dijalankan pada sesi aktif ini. Silakan tentukan regulasi acuan dan regulasi pembaruan lalu tekan{" "}
            <strong>"Jalankan Analisis"</strong> di Tab 1 terlebih dahulu agar IBM Bob memetakan klausul kepatuhan yang valid.
          </span>
        </div>
      )}

      {/* Active Regulatory Diff Context from Tab 1 */}
      <div className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] p-5 shadow-sm space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#DDD8CD] pb-2.5">
          <div className="flex items-center space-x-2">
            <span className={`h-2 w-2 rounded-full ${hasFindings ? "bg-[#0F5C2B]" : "bg-[#8C887B]"}`}></span>
            <span className="text-xs font-bold uppercase tracking-wider text-[#3C3A35]">
              Konteks Input Temuan Regulasi (dari Tab 1 Analisis Diff)
            </span>
          </div>
          <span className={`rounded border px-2 py-0.5 text-[10px] font-mono font-bold ${
            hasFindings
              ? "bg-[#E6F4EA] border-[#A3D4B0] text-[#0F5C2B]"
              : "bg-[#EFECE6] border-[#C8C2B5] text-[#8C887B]"
          }`}>
            {hasFindings ? "Konteks Aktif: Siap Dipetakan" : "Menunggu Analisis Tab 1"}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="rounded border border-[#DDD8CD] bg-[#F8F7F4] p-3">
            <span className="text-[10px] font-bold uppercase text-[#4A4843] block">Regulasi Acuan (Lama):</span>
            <span className="font-bold text-[#111110] mt-0.5 block">
              {refLabel || "Belum Dipilih (Menunggu Tab 1)"}
            </span>
            <span className="text-[11px] text-[#4A4843] line-clamp-1 mt-0.5">
              {selectedReference?.judul || "Pilih dokumen acuan di Tab 1"}
            </span>
          </div>

          <div className="rounded border border-[#DDD8CD] bg-[#F8F7F4] p-3">
            <span className="text-[10px] font-bold uppercase text-[#4A4843] block">Regulasi Pembaruan (Target):</span>
            <span className="font-bold text-[#111110] mt-0.5 block">
              {ojkLabel || "Belum Dipilih (Menunggu Tab 1)"}
            </span>
            <span className="text-[11px] text-[#4A4843] line-clamp-1 mt-0.5">
              {selectedRegulation?.judul || "Pilih dokumen pembaruan di Tab 1"}
            </span>
          </div>

          <div className="rounded border border-[#DDD8CD] bg-[#F8F7F4] p-3">
            <span className="text-[10px] font-bold uppercase text-[#4A4843] block">Klausul Kepatuhan Teridentifikasi:</span>
            <span className={`font-bold mt-0.5 block text-sm ${hasFindings ? "text-[#0F5C2B]" : "text-[#8C887B]"}`}>
              {hasFindings ? `${findingsCount} Klausul Siap Dipetakan` : "Belum Dianalisis (Menunggu Tab 1)"}
            </span>
            <span className="text-[11px] text-[#4A4843] mt-0.5 block">
              Target Repo:{" "}
              {hasFindings ? (
                <code className="font-mono font-bold text-[#111110]">mock_fintech_repo/</code>
              ) : (
                <span className="text-[#8C887B]">Menunggu Analisis Tab 1</span>
              )}
            </span>
          </div>
        </div>
      </div>

      {/* Terminal View */}
      <div className="rounded-md border border-[#C8C2B5] bg-[#1A1917] overflow-hidden shadow-sm">
        <div className="flex items-center justify-between bg-[#2D2C28] px-4 py-2.5 border-b border-[#3C3A35]">
          <div className="flex items-center space-x-2">
            <Terminal className="h-4 w-4 text-[#A3D4B0]" />
            <span className="text-xs font-mono font-bold text-white">
              ibm-bob-shell --workspace mock_fintech_repo --input data/temuan.json --mcp-config .bob/mcp.json
            </span>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={clearLogs}
              disabled={running}
              className="flex items-center space-x-1 text-[11px] font-mono text-[#DDD8CD] hover:text-white px-2 py-0.5 rounded bg-[#3C3A35] hover:bg-[#4A4843] transition-colors cursor-pointer disabled:opacity-50"
              title="Bersihkan log konsol"
            >
              <RotateCcw className="h-3 w-3" />
              <span>Bersihkan Log</span>
            </button>
            {mcpConnected ? (
              <span className="text-[11px] font-mono text-[#A3D4B0] flex items-center gap-1.5 font-bold">
                <span className="h-2 w-2 rounded-full bg-[#A3D4B0] animate-pulse"></span>
                MCP Server Terhubung
              </span>
            ) : (
              <span className="text-[11px] font-mono text-[#F4B3AE] flex items-center gap-1.5 font-bold">
                <span className="h-2 w-2 rounded-full bg-[#C5221F]"></span>
                MCP Server Terputus
              </span>
            )}
          </div>
        </div>

        <div className="p-4 font-mono text-xs space-y-2 max-h-80 overflow-y-auto">
          {logs.map((log, idx) => {
            let color = "text-[#EFECE6]";
            let badge = null;

            if (log.type === "tool_call") {
              color = "text-[#A3D4B0]";
              badge = <span className="rounded bg-[#FFFFFF]/10 text-[#A3D4B0] px-1.5 py-0.5 text-[10px] mr-2 font-bold border border-[#A3D4B0]/30">MCP Tool</span>;
            } else if (log.type === "thought") {
              color = "text-[#F8F7F4]";
              badge = <span className="rounded bg-[#F5D68B]/20 text-[#F5D68B] px-1.5 py-0.5 text-[10px] mr-2 font-bold border border-[#F5D68B]/30">Bob Reasoning</span>;
            } else if (log.type === "success") {
              color = "text-[#A3D4B0]";
              badge = <span className="rounded bg-[#A3D4B0]/20 text-[#A3D4B0] px-1.5 py-0.5 text-[10px] mr-2 font-bold border border-[#A3D4B0]/30">Handoff</span>;
            }

            return (
              <div key={idx} className={`leading-relaxed ${color}`}>
                {badge}
                <span>{log.msg}</span>
              </div>
            );
          })}
          {running && (
            <div className="flex items-center space-x-2 text-[#C8C2B5] animate-pulse">
              <span className="inline-block h-3 w-1 bg-[#A3D4B0]"></span>
              <span>Menunggu output eksekusi Bob berikutnya...</span>
            </div>
          )}
        </div>
      </div>

      {/* Success Banner & Call-to-Action to Tab 3 */}
      {isHandoffDone && onNavigateToReview && (
        <div className="rounded-md border border-[#A3D4B0] bg-[#E6F4EA] p-4 text-xs text-[#0F5C2B] shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="h-5 w-5 text-[#0F5C2B] shrink-0" />
            <div>
              <span className="font-bold text-sm block">Handoff IBM Bob Berhasil</span>
              <span className="text-[11px] text-[#2D2C28]">
                Paket artefak telah dibuat di folder <code>artifacts/</code>. Baris kode siap ditinjau secara human-in-the-loop.
              </span>
            </div>
          </div>
          <button
            onClick={onNavigateToReview}
            className="flex items-center space-x-1.5 rounded bg-[#1A1917] hover:bg-[#2D2C28] text-white px-4 py-2 font-bold text-xs transition-colors shrink-0 shadow-sm cursor-pointer"
          >
            <span>Lanjut ke Tab 3: Tata Kelola & Tinjauan</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Generated Artifacts Viewer */}
      <div className="rounded-md border border-[#DDD8CD] bg-[#FFFFFF] p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#DDD8CD] pb-3">
          <div className="flex items-center space-x-2">
            <FileCode className="h-5 w-5 text-[#1A1917]" />
            <h3 className="text-sm font-bold text-[#111110] tracking-tight">
              Paket Artefak Handoff IBM Bob (artifacts/)
            </h3>
          </div>

          {/* Artifact File Tabs */}
          {hasRunBob && (
            <div className="flex items-center space-x-2">
              {["proposed_patch.diff", "generated_tests.py", "impact_report.json"].map((fileName) => (
                <button
                  key={fileName}
                  onClick={() => setActiveArtifactTab(fileName)}
                  className={`rounded px-3 py-1 text-xs font-mono font-bold transition-colors cursor-pointer ${
                    activeArtifactTab === fileName
                      ? "bg-[#1A1917] text-white"
                      : "bg-[#EFECE6] text-[#2D2C28] border border-[#C8C2B5] hover:bg-[#F3EFE8]"
                  }`}
                >
                  {fileName}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Content Box */}
        {!hasRunBob ? (
          <div className="rounded-md border border-dashed border-[#DDD8CD] bg-[#FAF8F5] p-10 text-center space-y-3">
            <div className="flex justify-center">
              <div className="h-10 w-10 rounded-full bg-[#EFECE6] flex items-center justify-center text-[#1A1917] border border-[#DDD8CD]">
                <FileCode className="h-4 w-4 text-[#1A1917]" />
              </div>
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-bold text-[#111110]">
                Artefak Handoff Belum Dibuat di Sesi Ini
              </h4>
              <p className="text-xs text-[#4A4843] max-w-lg mx-auto leading-relaxed">
                Tekan tombol <strong>"Jalankan IBM Bob"</strong> di atas untuk memindai repositori lokal{" "}
                <code>mock_fintech_repo/</code>, merumuskan draf patch kepatuhan, serta memproduksi paket artefak handoff (
                <code>proposed_patch.diff</code>, <code>generated_tests.py</code>, <code>impact_report.json</code>).
              </p>
            </div>
            <div className="text-[11px] font-semibold text-[#8C887B] pt-1">
              Status: Menunggu Eksekusi IBM Bob
            </div>
          </div>
        ) : currentArtifact ? (
          <div className="relative">
            <div className="absolute top-3 right-3 z-10 flex items-center space-x-2">
              <button
                onClick={() => downloadArtifact(currentArtifact.name, currentArtifact.content)}
                className="flex items-center space-x-1.5 rounded bg-[#FFFFFF] hover:bg-[#F8F7F4] px-2.5 py-1 text-xs text-[#1A1917] border border-[#C8C2B5] transition-colors shadow-sm font-semibold cursor-pointer"
                title="Unduh berkas"
              >
                <Download className="h-3.5 w-3.5 text-[#4A4843]" />
                <span>Unduh Berkas</span>
              </button>
              <button
                onClick={() => copyContent(currentArtifact.content)}
                className="flex items-center space-x-1.5 rounded bg-[#FFFFFF] hover:bg-[#F8F7F4] px-2.5 py-1 text-xs text-[#1A1917] border border-[#C8C2B5] transition-colors shadow-sm font-semibold cursor-pointer"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-[#0F5C2B]" /> : <Copy className="h-3.5 w-3.5 text-[#4A4843]" />}
                <span>{copied ? "Tersalin!" : "Salin Isi"}</span>
              </button>
            </div>

            <div className="rounded bg-[#FAF8F5] border border-[#DDD8CD] p-4 max-h-96 overflow-y-auto shadow-inner pt-12">
              {activeArtifactTab === "proposed_patch.diff" ? (
                <div className="font-mono text-xs leading-relaxed space-y-0.5">
                  {currentArtifact.content.split("\n").map((line, lIdx) => {
                    let lineBg = "bg-transparent";
                    let lineText = "text-[#1A1917]";
                    if (line.startsWith("+++") || line.startsWith("---")) {
                      lineBg = "bg-[#EFECE6]";
                      lineText = "text-[#4A4843] font-bold";
                    } else if (line.startsWith("+")) {
                      lineBg = "bg-[#E6F4EA]";
                      lineText = "text-[#0F5C2B] font-semibold";
                    } else if (line.startsWith("-")) {
                      lineBg = "bg-[#FCE8E6]";
                      lineText = "text-[#C5221F] font-semibold";
                    } else if (line.startsWith("@@")) {
                      lineBg = "bg-[#EFECE6]";
                      lineText = "text-[#1A1917] font-bold";
                    }
                    return (
                      <div key={lIdx} className={`px-2 py-0.5 rounded ${lineBg} ${lineText} whitespace-pre-wrap`}>
                        {line || " "}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <pre className="font-mono text-xs text-[#1A1917] whitespace-pre-wrap leading-relaxed">
                  {currentArtifact.content}
                </pre>
              )}
            </div>
          </div>
        ) : (
          <div className="rounded bg-[#FAF8F5] border border-[#DDD8CD] p-8 text-center text-xs text-[#8C887B]">
            Artefak belum selesai dimuat. Silakan tunggu beberapa saat atau jalankan ulang agen IBM Bob.
          </div>
        )}
      </div>
    </div>
  );
}
