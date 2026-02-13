import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access_token");

    if (!accessToken) {
      return NextResponse.json({ user: null }, { status: 200 });
    }

    // Decode JWT payload (no signature check — just reading stored cookie)
    const parts = accessToken.value.split(".");
    if (parts.length !== 3) {
      return NextResponse.json({ user: null }, { status: 200 });
    }

    const payload = JSON.parse(
      Buffer.from(parts[1], "base64").toString()
    );

    // Check if token is expired
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      return NextResponse.json({ user: null, expired: true }, { status: 200 });
    }

    return NextResponse.json({
      user: {
        id: payload.user_id,
        email: payload.sub,
        role: payload.role || "user",
      },
    });
  } catch {
    return NextResponse.json({ user: null }, { status: 200 });
  }
}
