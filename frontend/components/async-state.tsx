"use client";

import { Card, ErrorBanner } from "@/components/ui";

export function Loading() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {[0, 1, 2].map((item) => (
        <Card key={item} className="min-h-36 animate-pulse bg-white/[.045]" />
      ))}
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return <ErrorBanner>{message}</ErrorBanner>;
}

export function PageHeader({ title, caption }: { title: string; caption?: string }) {
  return (
    <div className="mb-8">
      <div className="mb-3 inline-flex rounded-full border border-gold/20 bg-gold/10 px-3 py-1 text-xs font-black uppercase tracking-[.2em] text-gold">
        Album premium 2026
      </div>
      <h1 className="max-w-5xl text-4xl font-black tracking-tight text-white md:text-6xl">{title}</h1>
      {caption && <p className="mt-4 max-w-3xl text-base font-semibold leading-relaxed text-muted md:text-lg">{caption}</p>}
    </div>
  );
}
