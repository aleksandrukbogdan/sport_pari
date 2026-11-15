"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { DemoBanner } from "@/shared/ui";
import type { Viewer } from "@/shared/types";

const links = [
  { href: "/", label: "Обзор" },
  { href: "/news", label: "Новости" },
  { href: "/matches", label: "Матчи и статистика" },
  { href: "/predictions", label: "Прогнозы" },
  { href: "/profile", label: "Профиль" },
];

function sectionTitle(pathname: string) {
  if (pathname.startsWith("/news")) return "Новости";
  if (pathname.startsWith("/matches")) return "Матчи и статистика";
  if (pathname.startsWith("/predictions")) return "Прогнозы";
  if (pathname.startsWith("/profile")) return "Профиль";
  if (pathname.startsWith("/login")) return "Вход";
  if (pathname.startsWith("/register")) return "Регистрация";
  if (pathname.startsWith("/components")) return "Компоненты";
  return "Обзор";
}

export function AppShell({ viewer, demo, children }: { viewer: Viewer | null; demo: boolean; children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [menu, setMenu] = useState(false);

  return (
    <div className="shell">
      <a className="skip" href="#content">К содержанию</a>
      <aside className={open ? "sidebar open" : "sidebar closed"}>
        <p className="brand">sport_pari</p>
        <nav className="nav" aria-label="Разделы">
          {links.map((link) => (
            <Link key={link.href} href={link.href} aria-current={pathname === link.href ? "page" : undefined} onClick={() => setOpen(false)}>
              {link.label}
            </Link>
          ))}
        </nav>
      </aside>
      <div className="main-column">
        <header className="topbar">
          <button className="menu-button" type="button" aria-expanded={open} aria-controls="app-nav" onClick={() => setOpen((value) => !value)}>
            Меню
          </button>
          <h1>{sectionTitle(pathname)}</h1>
          <button className="user-button" type="button" aria-expanded={menu} onClick={() => setMenu((value) => !value)}>
            {viewer ? viewer.username : "Войти"}
          </button>
          {menu ? (
            <div className="user-menu" role="menu">
              {viewer ? (
                <>
                  <Link href="/profile" onClick={() => setMenu(false)}>Профиль</Link>
                  <form action="/api/auth/logout" method="post">
                    <button type="submit">Выйти</button>
                  </form>
                </>
              ) : (
                <Link href={`/login?next=${encodeURIComponent(pathname)}`} onClick={() => setMenu(false)}>Войти</Link>
              )}
            </div>
          ) : null}
        </header>
        <main id="content" className="content">
          {demo ? <DemoBanner /> : null}
          {children}
        </main>
      </div>
    </div>
  );
}
