import { NextResponse } from "next/server";

import { isDemo } from "@/shared/labels";

export async function POST(request: Request) {
  if (isDemo()) return NextResponse.json({ detail: "Демонстрационный режим не создаёт учётную запись" }, { status: 409 });
  const body = await request.json().catch(() => null);
  const userApi = (process.env.USER_API_URL ?? "http://localhost:8001").replace(/\/$/, "");
  try {
    const response = await fetch(`${userApi}/registration`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json().catch(() => ({}));
    return NextResponse.json(payload, { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Не удалось связаться с сервисом пользователей" }, { status: 502 });
  }
}
