import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { isDemo } from "@/shared/labels";
import { subjectFromToken } from "@/shared/server-api";

export const dynamic = "force-dynamic";

const targets: Record<string, string | undefined> = {
  user: process.env.USER_API_URL ?? "http://localhost:8001",
  news: process.env.NEWS_API_URL ?? "http://localhost:8002",
  sports: process.env.SPORTS_API_URL ?? "http://localhost:8003",
  prediction: process.env.PREDICTION_API_URL ?? "http://localhost:8004",
};

type Context = { params: Promise<{ service: string; path: string[] }> };

async function proxy(request: Request, context: Context) {
  if (isDemo()) {
    return NextResponse.json({ detail: "Демонстрационный режим не вызывает сервер" }, { status: 409 });
  }
  const { service, path } = await context.params;
  const base = targets[service];
  if (!base) return NextResponse.json({ detail: "Неизвестный сервис" }, { status: 404 });
  const url = new URL(`${base.replace(/\/$/, "")}/${path.join("/")}`);
  url.search = new URL(request.url).search;
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const jar = await cookies();
  const access = jar.get("access_token")?.value ?? "";
  if (access && (service === "user" || service === "prediction")) headers.set("authorization", `Bearer ${access}`);
  if (access && service === "news") {
    const subject = subjectFromToken(access);
    if (subject) headers.set("x-user-id", subject);
  }
  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  try {
    const response = await fetch(url, { method: request.method, headers, body: hasBody ? await request.text() : undefined, cache: "no-store" });
    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json({ detail: "Не удалось связаться с сервисом" }, { status: 502 });
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
