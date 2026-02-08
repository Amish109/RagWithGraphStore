"use client";

import { useAuthStore } from "@/stores/auth-store";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export function Header() {
  const { isAuthenticated, isAnonymous } = useAuthStore();

  if (isAuthenticated) return null;

  return (
    <div className="flex items-center gap-2 border-b px-4 py-2 bg-muted/50">
      <span className="text-sm text-muted-foreground flex-1">
        {isAnonymous
          ? "You're browsing anonymously. Sign up to save your work."
          : "Sign in to access all features."}
      </span>
      <Button asChild size="sm" variant="outline">
        <Link href="/login">Login</Link>
      </Button>
      <Button asChild size="sm">
        <Link href="/register">Sign Up</Link>
      </Button>
    </div>
  );
}
