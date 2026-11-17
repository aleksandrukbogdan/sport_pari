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
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" />
      </head>
      <body>
        <AppShell viewer={viewer} demo={isDemo()}>{children}</AppShell>
      </body>
    </html>
  );
}
