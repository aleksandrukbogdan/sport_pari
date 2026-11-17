"use client";

import type { ReactNode } from "react";

export function PageTitle({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <header className="stack">
      <h2 className="page-title">{title}</h2>
      {children}
    </header>
  );
}

export function Breadcrumbs({ items }: { items: { href?: string; label: string }[] }) {
  return (
    <nav className="crumbs" aria-label="Навигация по разделу">
      {items.map((item, index) => (
        <span key={item.label}>
          {index > 0 ? " / " : null}
          {item.href ? <a href={item.href}>{item.label}</a> : <span>{item.label}</span>}
        </span>
      ))}
    </nav>
  );
}

export function StatusBadge({ status, label }: { status: string; label: string }) {
  return <span className={`status ${status}`}>{label}</span>;
}

export function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="surface">
      <h3 className="card-title">{title}</h3>
      <p className="muted">{text}</p>
    </div>
  );
}

export function ErrorState({ message, href }: { message: string; href?: string }) {
  return (
    <div className="surface" role="alert">
      <h3 className="card-title">Не получилось загрузить данные</h3>
      <p>{message}</p>
      {href ? <a className="button secondary" href={href}>Попробовать ещё раз</a> : null}
    </div>
  );
}

export function SkeletonBlock() {
  return (
    <div className="stack" aria-hidden="true">
      <div className="skeleton" style={{ height: 28, width: "46%" }} />
      <div className="skeleton" style={{ height: 96 }} />
      <div className="skeleton" style={{ height: 96 }} />
    </div>
  );
}

export function DemoBanner() {
  return <p className="banner">Демонстрационные данные. Учебный пример, сервер не является источником этих карточек.</p>;
}

export function WhenText({ value }: { value: string }) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return <span>{value}</span>;
  return <time dateTime={value}>{new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium", timeStyle: "short" }).format(date)}</time>;
}
