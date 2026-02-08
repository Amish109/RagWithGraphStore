import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const API_URL = process.env.API_URL || "http://localhost:8000";

export async function POST() {
  try {
    const cookieStore = await cookies();
    const refreshToken = cookieStore.get("refresh_token");

    if (!refreshToken) {
      return NextResponse.json(
        { detail: "No refresh token" },
        { status: 401 }
      );
    }

    const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken.value }),
    });

    if (!res.ok) {
      cookieStore.delete("access_token");
      cookieStore.delete("refresh_token");
      return NextResponse.json(
        { detail: "Refresh failed" },
        { status: 401 }
      );
    }

    const data = await res.json();

    cookieStore.set("access_token", data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 30 * 60,
    });

    cookieStore.set("refresh_token", data.refresh_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 7 * 24 * 60 * 60,
    });

    // Decode JWT to return user info
    const payload = JSON.parse(
      Buffer.from(data.access_token.split(".")[1], "base64").toString()
    );

    return NextResponse.json({
      success: true,
      user: {
        id: payload.user_id,
        email: payload.sub,
        role: payload.role || "user",
      },
    });
  } catch {
    return NextResponse.json(
      { detail: "Refresh error" },
      { status: 500 }
    );
  }
}
