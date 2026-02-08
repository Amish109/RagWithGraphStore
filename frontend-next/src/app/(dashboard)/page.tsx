"use client";

import { useAuthStore } from "@/stores/auth-store";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FileText, MessageSquare, Brain, GitCompareArrows } from "lucide-react";
import Link from "next/link";

const features = [
  {
    title: "Documents",
    description: "Upload and manage PDF/DOCX documents",
    icon: FileText,
    href: "/documents",
  },
  {
    title: "Chat",
    description: "Ask questions about your documents with AI",
    icon: MessageSquare,
    href: "/chat",
  },
  {
    title: "Compare",
    description: "Compare multiple documents for insights",
    icon: GitCompareArrows,
    href: "/compare",
  },
  {
    title: "Memory",
    description: "Manage your personal knowledge base",
    icon: Brain,
    href: "/memory",
  },
];

export default function DashboardPage() {
  const { user, isAuthenticated, isAnonymous } = useAuthStore();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          {isAuthenticated
            ? `Welcome back, ${user?.email?.split("@")[0]}`
            : "RAG Document Q&A"}
        </h1>
        <p className="text-muted-foreground mt-1">
          {isAnonymous
            ? "You're browsing anonymously. Sign up to save your work permanently."
            : "Upload documents and get intelligent, contextual answers."}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {features.map((feature) => {
          const Icon = feature.icon;
          return (
            <Link key={feature.href} href={feature.href}>
              <Card className="hover:bg-accent/50 transition-colors cursor-pointer h-full">
                <CardHeader className="flex flex-row items-center gap-2 pb-2">
                  <Icon className="h-5 w-5 text-primary" />
                  <CardTitle className="text-lg">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription>{feature.description}</CardDescription>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
