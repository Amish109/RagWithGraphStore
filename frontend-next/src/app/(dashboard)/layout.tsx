"use client";

import { useEffect } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { useAuthStore } from "@/stores/auth-store";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { setUser, setLoading, setAnonymous } = useAuthStore();

  useEffect(() => {
    async function checkAuth() {
      try {
        const res = await fetch("/api/auth/refresh", { method: "POST" });
        if (res.ok) {
          // Refresh succeeded, get user from the access token via a check endpoint
          // For now, decode from cookie via a simple me endpoint
          const meRes = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/auth/me`,
            { credentials: "include" }
          );
          if (meRes.ok) {
            const user = await meRes.json();
            setUser(user);
          } else {
            setAnonymous(true);
            setLoading(false);
          }
        } else {
          setAnonymous(true);
          setLoading(false);
        }
      } catch {
        setAnonymous(true);
        setLoading(false);
      }
    }
    checkAuth();
  }, [setUser, setLoading, setAnonymous]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
