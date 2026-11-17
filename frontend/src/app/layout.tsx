import type { Metadata } from "next";

import { AppShell } from "@/shared/shell";
import { isDemo } from "@/shared/labels";
import { loadViewer } from "@/shared/server-api";
import "./globals.css";

export const metadata: Metadata = { title: "sport_pari", description: "Учебная спортивная аналитика" };
export const dynamic = "force-dynamic";

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const viewer = await loadViewer();
  return (
    <html lang="ru">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700&family=Source+Serif+4:opsz,wght@8..60,600&display=swap" />
        <meta name="theme-color" content="#0c1218" />
      </head>
      <body>
        <AppShell viewer={viewer} demo={isDemo()}>{children}</AppShell>
      </body>
    </html>
  );
}
