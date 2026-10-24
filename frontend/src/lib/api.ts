const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface SystemHealth {
  status: string;
  timestamp: string;
  components?: {
    langflow: {
      name: string;
      connected: boolean;
    };
    chromadb: {
      name: string;
      connected: boolean;
    };
    bob: {
      name: string;
      connected: boolean;
    };
  };
  langflow: {
    mode: string;
    connected: boolean;
    flow_id: string;
  };
  license: {
    organization: string;
    plan: string;
    status: string;
    status_label: string;
    is_valid: boolean;
    active_repos: number;
    repo_limit: number;
    message: string;
  };
  artifacts_exist: boolean;
}

export interface OjkRegulation {
  id: string;
  judul: string;
  nomor: string;
  tahun: string;
  sektor: string;
  sektor_id: string;
  jenis: string;
  tanggal_berlaku: string;
  status: string;
  detail_url?: string;
  download_url?: string;
  fetched_at: string;
}

export const DEFAULT_POJK_77: OjkRegulation = {
  id: "pojk-77-2016",
  nomor: "77/POJK.01/2016",
  tahun: "2016",
  judul: "Peraturan Otoritas Jasa Keuangan Nomor 77/POJK.01/2016 tentang Layanan Pinjam Meminjam Uang Berbasis Teknologi Informasi",
  sektor: "Lembaga Pembiayaan & LPBBTI (P2P Lending)",
  sektor_id: "09",
  jenis: "Peraturan OJK",
  tanggal_berlaku: "28-12-2016",
  status: "Diubah / Terdahulu",
  detail_url: "https://jdih.ojk.go.id/Web/ViewPeraturan/Detail/pojk-77-2016",
  fetched_at: "2026-10-23T12:00:00Z",
};

export const DEFAULT_POJK_22: OjkRegulation = {
  id: "pojk-22-2023",
  nomor: "22",
  tahun: "2023",
  judul: "Pelindungan Konsumen dan Masyarakat di Sektor Jasa Keuangan",
  sektor: "Pelindungan Konsumen & Market Conduct",
  sektor_id: "04",
  jenis: "Peraturan OJK",
  tanggal_berlaku: "20-12-2023",
  status: "Berlaku",
  detail_url: "https://jdih.ojk.go.id/Web/ViewPeraturan/Detail/pojk-22-2023",
  fetched_at: "2026-10-23T12:00:00Z",
};

export interface ReferenceRegulation {
  id: string;
  nomor: string;
  tahun: string;
  doc_id: string;
  judul: string;
  sektor: string;
  keterangan: string;
  pasal_kunci: string;
  ketentuan_kunci: string[];
}

export const REFERENCE_REGULATIONS: ReferenceRegulation[] = [
  {
    id: "pojk-77-2016",
    nomor: "77/POJK.01/2016",
    tahun: "2016",
    doc_id: "POJK-77-2016",
    judul: "Layanan Pinjam Meminjam Uang Berbasis Teknologi Informasi",
    sektor: "Fintech Lending (P2P Lending)",
    keterangan: "Basis acuan statutori fintech lending terdahulu (diindeks di ChromaDB lokal).",
    pasal_kunci: "Pasal 8 ayat (2) & (3)",
    ketentuan_kunci: [
      "Batas maksimum plafon pinjaman dana: Rp 20.000.000",
      "Batas maksimum tingkat suku bunga harian: 0,4% per hari",
      "Penyelenggara wajib terdaftar dan berizin resmi di OJK",
    ],
  },
  {
    id: "pojk-1-2013",
    nomor: "1/POJK.07/2013",
    tahun: "2013",
    doc_id: "POJK-1-2013",
    judul: "Perlindungan Konsumen Sektor Jasa Keuangan",
    sektor: "Pelindungan Konsumen & Edukasi",
    keterangan: "Regulasi acuan awal prinsip transparansi produk finansial dan penanganan pengaduan nasabah.",
    pasal_kunci: "Pasal 4 ayat (1) & (2)",
    ketentuan_kunci: [
      "Kewajiban keterbukaan informasi biaya dan perhitungan bunga",
      "Penyediaan mekanisme penanganan dan penyelesaian pengaduan",
      "Larangan klausula baku yang sepihak memberatkan konsumen",
    ],
  },
  {
    id: "pojk-13-2018",
    nomor: "13/POJK.02/2018",
    tahun: "2018",
    doc_id: "POJK-13-2018",
    judul: "Inovasi Keuangan Digital di Sektor Jasa Keuangan",
    sektor: "Inovasi Keuangan Digital (IKD / Sandbox)",
    keterangan: "Regulasi acuan awal ruang uji coba terbatas (Regulatory Sandbox) dan tata kelola ITSK terdahulu.",
    pasal_kunci: "Pasal 7 ayat (1)",
    ketentuan_kunci: [
      "Kewajiban pencatatan dan masa pengujian di Regulatory Sandbox",
      "Prinsip perlindungan kerahasiaan data nasabah finansial",
      "Penerapan audit independen pada sistem teknologi informasi",
    ],
  },
];

export interface Finding {
  change_id: string;
  jenis_perubahan: string;
  pasal_baru: {
    doc_id: string;
    pasal: string;
    ayat: string;
    kutipan: string;
  };
  pasal_lama: {
    doc_id: string;
    pasal: string;
    ayat: string;
    kutipan: string;
  };
  ringkasan: string;
  sitasi_valid: boolean;
  confidence: string;
  abstain: boolean;
  alasan_abstain?: string | null;
  kandidat_kode: Array<{
    path: string;
    lokasi: string;
    evidence: string;
    alasan: string;
    confidence: string;
    patch_status: string;
    test_status: string;
    old_code: string;
    proposed_code: string;
  }>;
}

export interface AnalysisResponse {
  source: string;
  analysis_meta: any;
  metrics: {
    total_findings: number;
    valid_citations: number;
    citation_percentage: number;
    confidence: string;
    abstain: boolean;
  };
  findings: Finding[];
}

export interface ImpactRecord {
  finding_id?: string;
  change_id?: string;
  ringkasan?: string;
  path: string;
  abs_path?: string;
  line?: number | null;
  lines?: number[];
  status: string;
  old_code: string;
  proposed_code: string;
  diff?: string;
  evidence?: string;
  alasan?: string;
}

export interface DryRunResponse {
  dry_run: boolean;
  results: Array<{
    path: string;
    status: string;
    backup_path: string | null;
    message: string;
  }>;
  records_count: number;
}

export interface ApplyPatchResponse {
  success: boolean;
  applied_count: number;
  results: Array<{
    path: string;
    status: string;
    backup_path: string | null;
    message: string;
  }>;
}

export interface TestResultResponse {
  cmd?: string;
  returncode?: number;
  code?: number;
  stdout: string;
  stderr: string;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  action: string;
  actor: string;
  details: string;
  note?: string;
  backups?: string[];
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  const res = await fetch(`${API_BASE}/api/system/health`, { cache: "no-store" });
  if (!res.ok) throw new Error("Gagal mengambil status sistem");
  return res.json();
}

export async function fetchOjkRegulations(sectors = "10,09,04", limit = 15): Promise<OjkRegulation[]> {
  const res = await fetch(`${API_BASE}/api/ojk/regulations?sectors=${sectors}&limit=${limit}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Gagal mengambil daftar regulasi OJK");
  const data = await res.json();
  return data.regulations || [];
}

export async function fetchAnalysisFindings(): Promise<AnalysisResponse> {
  const res = await fetch(`${API_BASE}/api/analysis/findings`, { cache: "no-store" });
  if (!res.ok) throw new Error("Gagal mengambil hasil temuan regulasi");
  return res.json();
}

export async function runAnalysis(
  engine: "embedded" | "rest" = "embedded",
  ojkInfo?: Partial<OjkRegulation>,
  acuanInfo?: Partial<OjkRegulation>
): Promise<any> {
  const res = await fetch(`${API_BASE}/api/analysis/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ engine, ojk_info: ojkInfo, acuan_info: acuanInfo }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Gagal menjalankan analisis regulasi");
  }
  return res.json();
}

export async function analyzeOjkRegulation(reg: OjkRegulation): Promise<any> {
  const res = await fetch(`${API_BASE}/api/ojk/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      id: reg.id,
      judul: reg.judul,
      nomor: reg.nomor,
      tahun: reg.tahun,
      detail_url: reg.detail_url,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Gagal menganalisis regulasi OJK");
  }
  return res.json();
}

export async function fetchImpactScan(): Promise<{ records: ImpactRecord[]; source: string }> {
  const res = await fetch(`${API_BASE}/api/impact/scan`, { cache: "no-store" });
  if (!res.ok) throw new Error("Gagal memindai dampak kode");
  return res.json();
}

export async function fetchImpactDryRun(): Promise<DryRunResponse> {
  const res = await fetch(`${API_BASE}/api/impact/dry-run`, { cache: "no-store" });
  if (!res.ok) throw new Error("Gagal menjalankan dry-run patch");
  return res.json();
}

export async function applyPatch(reviewerRole: string, reviewerNote: string): Promise<ApplyPatchResponse> {
  const res = await fetch(`${API_BASE}/api/impact/apply`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Role": reviewerRole || "Compliance Officer",
    },
    body: JSON.stringify({
      reviewer_role: reviewerRole,
      reviewer_note: reviewerNote,
      confirm: true,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Gagal menerapkan patch");
  }
  return res.json();
}

export async function rollbackPatch(role: string = "Compliance Officer"): Promise<{
  status: string;
  count: number;
  message: string;
  restored: Array<{ target: string; backup_source: string }>;
}> {
  const res = await fetch(`${API_BASE}/api/impact/rollback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Role": role,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Gagal memulihkan cadangan patch");
  }
  return res.json();
}

export async function runRepoTests(): Promise<TestResultResponse> {
  const res = await fetch(`${API_BASE}/api/impact/test`, { method: "POST" });
  if (!res.ok) throw new Error("Gagal mengeksekusi test suite repositori");
  return res.json();
}

export async function fetchAuditLogs(): Promise<AuditLog[]> {
  const res = await fetch(`${API_BASE}/api/audit/logs`, { cache: "no-store" });
  if (!res.ok) throw new Error("Gagal mengambil log jejak audit");
  const data = await res.json();
  return data.logs || [];
}

export interface CompanyRepo {
  id: string;
  name: string;
  path: string;
  is_active: boolean;
}

export interface CompanyProfile {
  id: string;
  organization: string;
  plan: string;
  plan_label: string;
  status: string;
  status_label: string;
  repo_limit: number;
  active_repos: number;
  quota_ok: boolean;
  can_run: boolean;
  message: string;
  repositories: CompanyRepo[];
}

export async function fetchBobArtifacts(): Promise<Array<{ name: string; size: number; content: string }>> {
  const res = await fetch(`${API_BASE}/api/bob/artifacts`, { cache: "no-store" });
  if (!res.ok) throw new Error("Gagal mengambil artefak Bob");
  const data = await res.json();
  return data.artifacts || [];
}

export async function fetchLicenseProfiles(): Promise<{
  profiles: CompanyProfile[];
  active: CompanyProfile;
}> {
  const res = await fetch(`${API_BASE}/api/license/profiles`, { cache: "no-store" });
  if (!res.ok) throw new Error("Gagal mengambil profil entitas perusahaan");
  return res.json();
}

export async function selectCompanyProfile(companyId: string): Promise<CompanyProfile> {
  const res = await fetch(`${API_BASE}/api/license/select`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company_id: companyId }),
  });
  if (!res.ok) throw new Error("Gagal mengubah entitas perusahaan");
  const data = await res.json();
  return data.company;
}

export async function addCompanyRepo(
  companyId: string,
  name: string,
  path: string,
  role: string = "Administrator"
): Promise<{ success: boolean; repo: CompanyRepo; company: CompanyProfile }> {
  const res = await fetch(`${API_BASE}/api/license/add-repo`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Role": role,
    },
    body: JSON.stringify({ company_id: companyId, name, path }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Gagal mendaftarkan repositori baru");
  }
  return res.json();
}
