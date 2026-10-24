"use client";

import React, { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import OjkMonitorTab from "@/components/OjkMonitorTab";
import RegulatoryDiffTab from "@/components/RegulatoryDiffTab";
import BobShellConsoleTab from "@/components/BobShellConsoleTab";
import ImpactReviewTab from "@/components/ImpactReviewTab";
import AuditTrailModal from "@/components/AuditTrailModal";
import RepoManagerModal from "@/components/RepoManagerModal";
import {
  SystemHealth,
  OjkRegulation,
  AnalysisResponse,
  ImpactRecord,
  CompanyProfile,
  DEFAULT_POJK_77,
  DEFAULT_POJK_22,
  fetchSystemHealth,
  fetchOjkRegulations,
  fetchAnalysisFindings,
  runAnalysis,
  analyzeOjkRegulation,
  fetchImpactScan,
  fetchImpactDryRun,
  applyPatch,
  rollbackPatch,
  runRepoTests,
  fetchBobArtifacts,
  fetchLicenseProfiles,
  selectCompanyProfile,
  addCompanyRepo,
} from "@/lib/api";
import { GitCompare, Terminal, ShieldCheck, Globe } from "lucide-react";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"diff" | "bob" | "review" | "ojk">("diff");
  const [activeRole, setActiveRole] = useState<string>("Compliance Officer");
  const [auditOpen, setAuditOpen] = useState<boolean>(false);
  const [repoModalOpen, setRepoModalOpen] = useState<boolean>(false);

  // Company profiles & B2B licensing state
  const [companyProfiles, setCompanyProfiles] = useState<CompanyProfile[]>([]);
  const [activeCompanyId, setActiveCompanyId] = useState<string>("bank_digital");

  // Data states
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [regulations, setRegulations] = useState<OjkRegulation[]>([]);
  const [selectedRegulation, setSelectedRegulation] = useState<OjkRegulation | null>(null);
  const [selectedReference, setSelectedReference] = useState<OjkRegulation | null>(null);
  const [ojkLoading, setOjkLoading] = useState<boolean>(false);

  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState<boolean>(false);
  const [hasRunAnalysis, setHasRunAnalysis] = useState<boolean>(false);
  const [hasRunBob, setHasRunBob] = useState<boolean>(false);

  const [artifacts, setArtifacts] = useState<Array<{ name: string; size: number; content: string }>>([]);
  const [impactRecords, setImpactRecords] = useState<ImpactRecord[]>([]);

  // Initial Load & periodic health sync
  useEffect(() => {
    fetchSystemHealth().then(setHealth).catch(console.error);
    const healthInterval = setInterval(() => {
      fetchSystemHealth().then(setHealth).catch(() => {});
    }, 10000);

    loadLicenseProfiles();
    loadAnalysis();
    loadImpact();
    loadArtifacts();
    loadOjk();

    return () => clearInterval(healthInterval);
  }, []);

  const loadLicenseProfiles = () => {
    fetchLicenseProfiles()
      .then((data) => {
        if (data?.profiles) setCompanyProfiles(data.profiles);
        if (data?.active?.id) setActiveCompanyId(data.active.id);
      })
      .catch(console.error);
  };

  const handleCompanyChange = async (companyId: string) => {
    setActiveCompanyId(companyId);
    try {
      await selectCompanyProfile(companyId);
      const h = await fetchSystemHealth();
      setHealth(h);
      loadLicenseProfiles();
    } catch (err) {
      console.error("Gagal mengubah entitas perusahaan:", err);
    }
  };

  const handleAddRepo = async (name: string, path: string) => {
    await addCompanyRepo(activeCompanyId, name, path);
    const h = await fetchSystemHealth();
    setHealth(h);
    loadLicenseProfiles();
  };

  const loadOjk = () => {
    setOjkLoading(true);
    fetchOjkRegulations()
      .then((data) => {
        setRegulations(data);
      })
      .catch(console.error)
      .finally(() => setOjkLoading(false));
  };

  const loadAnalysis = () => {
    fetchAnalysisFindings()
      .then((data) => {
        setAnalysis(data);
      })
      .catch(console.error);
  };

  const handleRunAnalysis = async () => {
    if (!selectedRegulation || !selectedReference) {
      alert("Silakan tentukan regulasi acuan dan regulasi pembaruan terlebih dahulu.");
      return;
    }
    setAnalysisLoading(true);
    try {
      const res = await runAnalysis("embedded", selectedRegulation, selectedReference);
      setHasRunAnalysis(true);
      setHasRunBob(false);
      if (res?.data) {
        const d = res.data;
        const total = d.findings?.length || 0;
        const valid = d.findings?.filter((f: any) => f.sitasi_valid)?.length || 0;
        setAnalysis({
          source: "live",
          analysis_meta: d.analysis_meta,
          metrics: {
            total_findings: total,
            valid_citations: valid,
            citation_percentage: total > 0 ? Math.round((valid / total) * 100) : 100,
            confidence: "Tinggi",
            abstain: false,
          },
          findings: d.findings || [],
        });
      } else {
        await loadAnalysis();
      }
      await loadImpact();
    } catch (err: any) {
      alert(`Error analisis: ${err.message}`);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const loadImpact = () => {
    fetchImpactScan()
      .then((data) => setImpactRecords(data?.records || []))
      .catch(console.error);
  };

  const loadArtifacts = () => {
    fetchBobArtifacts().then(setArtifacts).catch(console.error);
  };

  const handleSelectOjk = async (reg: OjkRegulation) => {
    setSelectedRegulation(reg);
    const ref = selectedReference || DEFAULT_POJK_77;
    if (!selectedReference) {
      setSelectedReference(DEFAULT_POJK_77);
    }
    setAnalysisLoading(true);
    setActiveTab("diff");
    try {
      const res = await runAnalysis("embedded", reg, ref);
      setHasRunAnalysis(true);
      setHasRunBob(false);
      if (res?.data) {
        const d = res.data;
        const total = d.findings?.length || 0;
        const valid = d.findings?.filter((f: any) => f.sitasi_valid)?.length || 0;
        setAnalysis({
          source: "live",
          analysis_meta: d.analysis_meta,
          metrics: {
            total_findings: total,
            valid_citations: valid,
            citation_percentage: total > 0 ? Math.round((valid / total) * 100) : 100,
            confidence: "Tinggi",
            abstain: false,
          },
          findings: d.findings || [],
        });
      } else {
        await loadAnalysis();
      }
      await loadImpact();
    } catch (err: any) {
      alert(`Gagal memproses POJK ${reg.nomor}/${reg.tahun}: ${err.message}`);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleSelectAsReference = (reg: OjkRegulation) => {
    setSelectedReference(reg);
    setHasRunAnalysis(false);
    setHasRunBob(false);
    setActiveTab("diff");
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] text-[#1A1917] flex flex-col md:flex-row font-sans">
      {/* Left Sidebar (Classic 280px Identical to app.py) */}
      <Sidebar
        health={health}
        activeCompanyId={activeCompanyId}
        companyProfiles={companyProfiles}
        onCompanyChange={handleCompanyChange}
        onOpenAudit={() => setAuditOpen(true)}
        onOpenRepoManager={() => setRepoModalOpen(true)}
      />

      {/* Right Canvas / Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Main Canvas Header */}
        <header className="border-b border-[#DDD8CD] bg-[#FAF8F5] px-8 py-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-[#111110]">SELISIH</h1>
              <p className="text-xs text-[#4A4843] mt-0.5">
                Regulatory Change & Code Impact System — IBM Hackathon IT-Finance
              </p>
            </div>
            <div className="text-left sm:text-right">
              <span className="text-xs font-bold text-[#111110]">Entitas Perusahaan</span>
              <div>
                <span className="inline-block mt-0.5 rounded bg-[#EFECE6] border border-[#C8C2B5] px-2.5 py-0.5 text-[11px] font-bold text-[#111110]">
                  {health?.license?.organization || "PT Bank Digital Nusantara"}
                </span>
              </div>
              <div className="text-[10px] text-[#8C887B] font-mono mt-0.5">
                {health?.license?.plan || "Enterprise Plan"} •{" "}
                <span className={health?.license?.is_valid !== false ? "text-[#0F5C2B] font-bold" : "text-[#C5221F] font-bold"}>
                  {health?.license?.status_label || (health?.license?.is_valid !== false ? "Aktif" : "Dibatasi")}
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 p-8 space-y-6 max-w-6xl w-full">
          {/* Main Navigation Tabs */}
          <div className="flex border-b border-[#DDD8CD] space-x-1">
            {[
              { id: "diff", label: "1. Analisis Regulasi (Diff)", icon: GitCompare },
              { id: "bob", label: "2. Pemetaan Dampak Kode", icon: Terminal },
              { id: "review", label: "3. Tata Kelola & Tinjauan", icon: ShieldCheck },
              { id: "ojk", label: "4. Pemantau Regulasi OJK (Live JDIH)", icon: Globe },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center space-x-2 px-5 py-3 text-xs md:text-sm font-bold border-b-2 transition-all rounded-t-md ${
                    isActive
                      ? "border-[#1A1917] text-[#111110] bg-[#FFFFFF] shadow-sm"
                      : "border-transparent text-[#4A4843] hover:text-[#111110] hover:bg-[#F3EFE8]"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? "text-[#1A1917]" : "text-[#8C887B]"}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Tab Views */}
          {activeTab === "diff" && (
            <RegulatoryDiffTab
              analysis={analysis}
              loading={analysisLoading}
              regulations={regulations}
              selectedReference={selectedReference}
              onSelectReference={(reg) => {
                setSelectedReference(reg);
                setHasRunAnalysis(false);
                setHasRunBob(false);
              }}
              selectedRegulation={selectedRegulation}
              onSelectRegulation={(reg) => {
                setSelectedRegulation(reg);
                setHasRunAnalysis(false);
                setHasRunBob(false);
              }}
              onRunAnalysis={handleRunAnalysis}
              hasRunAnalysis={hasRunAnalysis}
            />
          )}

          {activeTab === "bob" && (
            <BobShellConsoleTab
              artifacts={artifacts}
              onRefreshArtifacts={loadArtifacts}
              analysis={analysis}
              selectedReference={selectedReference}
              selectedRegulation={selectedRegulation}
              hasRunAnalysis={hasRunAnalysis}
              hasRunBob={hasRunBob}
              onBobExecuted={() => setHasRunBob(true)}
              mcpConnected={Boolean(health?.components?.bob?.connected)}
              onNavigateToReview={() => setActiveTab("review")}
            />
          )}

          {activeTab === "review" && (
            <ImpactReviewTab
              records={impactRecords}
              activeRole={health?.license?.organization || "PT Bank Digital Nusantara"}
              hasRunAnalysis={hasRunAnalysis}
              hasRunBob={hasRunBob}
              onNavigateToTab={(tab: "diff" | "bob") => setActiveTab(tab)}
              canRunPatch={health?.license?.is_valid !== false}
              licenseMessage={health?.license?.message}
              onDryRun={fetchImpactDryRun}
              onApplyPatch={async (note) => {
                const res = await applyPatch(health?.license?.organization || "PT Bank Digital Nusantara", note);
                await loadImpact();
                await loadArtifacts();
                return res;
              }}
              onRollback={async () => {
                const res = await rollbackPatch();
                await loadImpact();
                await loadArtifacts();
                return res;
              }}
              onRunTest={runRepoTests}
              onOpenAudit={() => setAuditOpen(true)}
              analysis={analysis}
              selectedReference={selectedReference}
              selectedRegulation={selectedRegulation}
            />
          )}

          {activeTab === "ojk" && (
            <OjkMonitorTab
              regulations={regulations}
              loading={ojkLoading}
              onRefresh={loadOjk}
              onSelectForAnalysis={handleSelectOjk}
              onSelectAsReference={handleSelectAsReference}
            />
          )}
        </main>

        {/* Footer */}
        <footer className="border-t border-[#DDD8CD] bg-[#F3EFE8] py-4 px-8 text-center text-xs text-[#4A4843]">
          <p>SELISIH Enterprise v2.0 — IBM x Hacktiv8 (IT-Finance) • IBM Bob & IBM watsonx • Zero Auto-Deploy Guarantee</p>
        </footer>
      </div>

      {/* Audit Trail Modal */}
      <AuditTrailModal isOpen={auditOpen} onClose={() => setAuditOpen(false)} />

      {/* Repository Manager Modal */}
      <RepoManagerModal
        isOpen={repoModalOpen}
        onClose={() => setRepoModalOpen(false)}
        company={
          companyProfiles.find((c) => c.id === activeCompanyId) ||
          (health?.license
            ? {
                id: activeCompanyId,
                organization: health.license.organization,
                plan: health.license.plan,
                plan_label: health.license.plan,
                status: health.license.status,
                status_label: health.license.status_label,
                repo_limit: health.license.repo_limit,
                active_repos: health.license.active_repos,
                quota_ok: health.license.is_valid,
                can_run: health.license.is_valid,
                message: health.license.message,
                repositories: [
                  {
                    id: "repo-core",
                    name: "mock_fintech_repo (Core Banking)",
                    path: "mock_fintech_repo",
                    is_active: true,
                  },
                ],
              }
            : null)
        }
        onAddRepo={handleAddRepo}
      />
    </div>
  );
}
