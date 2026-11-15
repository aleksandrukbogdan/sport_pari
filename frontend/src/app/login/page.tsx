import Link from "next/link";

import { AuthForm } from "@/modules/forms";
import { isDemo } from "@/shared/labels";
import { PageTitle } from "@/shared/ui";

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const params = await searchParams;
  const nextPath = params.next && params.next.startsWith("/") ? params.next : "/";
  return (
    <div className="stack">
      <PageTitle title="Вход">
        <p className="muted">Пароль проверяет сервис пользователей. Отдельного хранилища в интерфейсе нет.</p>
      </PageTitle>
      <AuthForm mode="login" nextPath={nextPath} demo={isDemo()} />
      <p>Нет учётной записи? <Link href="/register">Регистрация</Link></p>
    </div>
  );
}
