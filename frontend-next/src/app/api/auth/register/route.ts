import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const API_URL = process.env.API_URL || "http://localhost:8000";

export async function POST(request: Request) {
  try {
    const { email, password } = await request.json();

    // Get anonymous session cookie to pass along for migration
    const cookieStore = await cookies();
    const anonSession = cookieStore.get("session_id");

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (anonSession) {
      headers["Cookie"] = `session_id=${anonSession.value}`;
    }

    const res = await fetch(`${API_URL}/api/auth/register`, {
      method: "POST",
      headers,
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const error = await res.json();
      return NextResponse.json(
        { detail: error.detail || "Registration failed" },
        { status: res.status }
      );
    }

    const data = await res.json();

    // Now auto-login after registration
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const loginRes = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });

    if (loginRes.ok) {
      const loginData = await loginRes.json();

      cookieStore.set("access_token", loginData.access_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 30 * 60,
      });

      cookieStore.set("refresh_token", loginData.refresh_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 7 * 24 * 60 * 60,
      });

      const payload = JSON.parse(
        Buffer.from(loginData.access_token.split(".")[1], "base64").toString()
      );

      return NextResponse.json({
        user: {
          id: payload.sub,
          email: payload.email || email,
          role: payload.role || "user",
        },
        migration: data.migration || null,
      });
    }

    return NextResponse.json({
      user: { id: data.id, email, role: "user" },
      migration: data.migration || null,
    });
  } catch (err) {
    return NextResponse.json(
      { detail: err instanceof Error ? err.message : "Internal error" },
      { status: 500 }
    );
  }
}
