import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SELISIH — Enterprise Regulatory Change & Code Impact System",
  description: "Menjembatani Dokumen Regulasi OJK dengan Repositori Kode Fintech secara Human-in-the-Loop",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id">
      <body className="min-h-screen bg-[#FAF8F5] text-[#1A1917] antialiased">
        {children}
      </body>
    </html>
  );
}
