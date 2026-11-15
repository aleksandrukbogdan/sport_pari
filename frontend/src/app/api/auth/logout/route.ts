import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const jar = await cookies();
  const token = jar.get("access_token")?.value;
  const userApi = (process.env.USER_API_URL ?? "http://localhost:8001").replace(/\/$/, "");
  if (token) {
    await fetch(`${userApi}/logout`, { method: "POST", headers: { authorization: `Bearer ${token}` } }).catch(() => null);
  }
  jar.delete("access_token");
  jar.delete("refresh_token");
  jar.delete("demo_session");
  const origin = new URL(request.url).origin;
  return NextResponse.redirect(new URL("/", origin), 303);
}
