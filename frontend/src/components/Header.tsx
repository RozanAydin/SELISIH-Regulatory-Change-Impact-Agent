"use client";

import React from "react";
import { ShieldCheck, Server, KeyRound, Building2, History } from "lucide-react";
import { SystemHealth } from "@/lib/api";

interface HeaderProps {
  health: SystemHealth | null;
  activeRole: string;
  onRoleChange: (role: string) => void;
  onOpenAudit: () => void;
}

export const ROLES = [
  "Compliance Officer",
  "Software Engineer",
  "Administrator",
];

export default function Header({ health, activeRole, onRoleChange, onOpenAudit }: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 border-b border-[#DDD8CD] bg-[#FFFFFF]/95 backdrop-blur px-6 py-3.5 shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Logo & Brand matching app.py */}
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded bg-[#1A1917] text-white font-bold text-lg tracking-wider shadow-sm">
            S
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold tracking-tight text-[#111110]">SELISIH</span>
              <span className="rounded bg-[#EFECE6] px-2 py-0.5 text-xs font-semibold text-[#2D2C28] border border-[#C8C2B5]">
                Enterprise v2.0
              </span>
            </div>
            <p className="text-xs text-[#4A4843]">
              Regulatory Change & Code Impact System (IBM watsonx & IBM Bob)
            </p>
          </div>
        </div>

        {/* Status Indicators & Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* License Gateway Badge */}
          <div className="flex items-center space-x-2 rounded border border-[#DDD8CD] bg-[#F3EFE8] px-3 py-1.5 text-xs">
            <Building2 className="h-3.5 w-3.5 text-[#3C3A35]" />
            <span className="text-[#3C3A35] font-medium">{health?.license.organization || "PT Bank Digital Nusantara"}</span>
            <span className="rounded bg-[#FFFFFF] px-1.5 py-0.2 text-[10px] font-semibold text-[#1A1917] border border-[#DDD8CD]">
              {health?.license.plan || "Enterprise"}
            </span>
            <span className="flex items-center gap-1 text-[11px] font-semibold text-[#0F5C2B]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#0F5C2B] animate-pulse"></span>
              {health?.license.status_label || "Aktif"}
            </span>
          </div>

          {/* Langflow Engine Badge */}
          <div className="flex items-center space-x-1.5 rounded border border-[#DDD8CD] bg-[#F3EFE8] px-3 py-1.5 text-xs">
            <Server className="h-3.5 w-3.5 text-[#3C3A35]" />
            <span className="text-[#4A4843]">Engine:</span>
            <span className="font-semibold text-[#111110]">
              {health?.langflow.mode === "embedded" ? "Embedded (Granite)" : "Langflow REST"}
            </span>
          </div>

          {/* Audit Trail Button */}
          <button
            onClick={onOpenAudit}
            className="flex items-center space-x-1.5 rounded border border-[#C8C2B5] bg-[#FFFFFF] hover:bg-[#F8F7F4] px-3 py-1.5 text-xs font-semibold text-[#1A1917] transition-colors shadow-sm"
          >
            <History className="h-3.5 w-3.5 text-[#8A5B00]" />
            <span>Audit Trail</span>
          </button>

          {/* Role Selector */}
          <div className="flex items-center space-x-2 rounded border border-[#C8C2B5] bg-[#EFECE6] px-3 py-1 text-xs">
            <KeyRound className="h-3.5 w-3.5 text-[#1A1917]" />
            <span className="text-xs text-[#4A4843]">Peran:</span>
            <select
              value={activeRole}
              onChange={(e) => onRoleChange(e.target.value)}
              className="bg-transparent font-semibold text-[#1A1917] focus:outline-none cursor-pointer"
            >
              {ROLES.map((role) => (
                <option key={role} value={role} className="bg-[#FFFFFF] text-[#1A1917]">
                  {role}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </header>
  );
}
