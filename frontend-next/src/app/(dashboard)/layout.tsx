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
        // Use lightweight /me endpoint — does NOT consume the refresh token
        const res = await fetch("/api/auth/me");
        const data = await res.json();

        if (data.user) {
          setUser(data.user);
        } else if (data.expired) {
          // Token expired — try a single refresh
          const refreshRes = await fetch("/api/auth/refresh", { method: "POST" });
          if (refreshRes.ok) {
            const refreshData = await refreshRes.json();
            if (refreshData.user) {
              setUser(refreshData.user);
              return;
            }
          }
          setAnonymous(true);
          setLoading(false);
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
