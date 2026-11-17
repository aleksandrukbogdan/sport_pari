import Link from "next/link";

import { AuthForm } from "@/modules/forms";
import { isDemo } from "@/shared/labels";
import { PageTitle } from "@/shared/ui";

export default function RegisterPage() {
  return (
    <div className="stack">
      <PageTitle title="Регистрация">
        <p className="lead">Создайте учётную запись, чтобы отвечать на вопросы и обсуждать разбор. Пароль хранит сервис пользователей.</p>
      </PageTitle>
      <AuthForm mode="register" nextPath="/" demo={isDemo()} />
      <p>Уже есть вход? <Link href="/login">Войти</Link></p>
    </div>
  );
}
