import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const API_URL = process.env.API_URL || "http://localhost:8000";

export async function POST(request: Request) {
  try {
    const { email, password } = await request.json();

    // Backend expects OAuth2PasswordRequestForm (form-encoded)
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const res = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });

    if (!res.ok) {
      const error = await res.json();
      return NextResponse.json(
        { detail: error.detail || "Login failed" },
        { status: res.status }
      );
    }

    const data = await res.json();

    const cookieStore = await cookies();

    cookieStore.set("access_token", data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 30 * 60, // 30 minutes
    });

    cookieStore.set("refresh_token", data.refresh_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 7 * 24 * 60 * 60, // 7 days
    });

    // Decode JWT to get user info (without verification — backend validated)
    const payload = JSON.parse(
      Buffer.from(data.access_token.split(".")[1], "base64").toString()
    );

    return NextResponse.json({
      user: {
        id: payload.sub,
        email: payload.email || email,
        role: payload.role || "user",
      },
    });
  } catch (err) {
    return NextResponse.json(
      { detail: err instanceof Error ? err.message : "Internal error" },
      { status: 500 }
    );
  }
}
