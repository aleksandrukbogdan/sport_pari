import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { isDemo } from "@/shared/labels";

const userApi = () => (process.env.USER_API_URL ?? "http://localhost:8001").replace(/\/$/, "");

function cookieOptions(maxAge: number) {
  return { httpOnly: true, sameSite: "lax" as const, path: "/", maxAge, secure: false };
}

export async function POST(request: Request) {
  const jar = await cookies();
  if (isDemo()) {
    jar.set("demo_session", "1", cookieOptions(60 * 60 * 8));
    return NextResponse.json({ ok: true, demo: true });
  }
  const body = await request.json().catch(() => null);
  try {
    const response = await fetch(`${userApi()}/login`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) return NextResponse.json(payload, { status: response.status });
    jar.set("access_token", payload.access_token, cookieOptions(payload.expires_in ?? 3600));
    jar.set("refresh_token", payload.refresh_token, cookieOptions(payload.refresh_expires_in ?? 60 * 60 * 24));
    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json({ detail: "Не удалось связаться с сервисом пользователей" }, { status: 502 });
  }
}
