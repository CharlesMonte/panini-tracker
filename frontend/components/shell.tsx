"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { motion } from "framer-motion";
import {
  BookOpen,
  Database,
  History,
  Home,
  PackagePlus,
  Repeat2,
  Search,
  Settings,
  ShoppingCart,
  Sparkles,
} from "lucide-react";

const usage = [
  { href: "/", label: "Accueil", short: "Home", icon: Home },
  { href: "/saisie", label: "Saisie rapide", short: "Saisie", icon: PackagePlus },
  { href: "/echanges", label: "Échanges", short: "Échanges", icon: Repeat2 },
  { href: "/achats-ventes", label: "Achats / Ventes", short: "Ventes", icon: ShoppingCart },
  { href: "/collection", label: "Collection", short: "Album", icon: BookOpen },
  { href: "/catalogue", label: "Catalogue", short: "Catalogue", icon: Search },
];

const admin = [
  { href: "/historique", label: "Historique", short: "Historique", icon: History },
  { href: "/import-export", label: "Import / Export", short: "Import", icon: Settings },
  { href: "/admin", label: "Admin DB", short: "Admin", icon: Database },
];

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-pitch text-white">
      <HostStripes />
      <div className="flex min-h-screen">
        <aside className="sticky top-0 hidden h-screen w-[292px] shrink-0 border-r border-white/10 bg-pitch/72 backdrop-blur-2xl lg:block">
          <div className="flex h-full flex-col overflow-y-auto overscroll-contain p-5 [scrollbar-color:rgba(242,201,93,.45)_transparent] [scrollbar-width:thin]">
            <Brand />
            <QuickAction />
            <NavGroup title="Usage courant" items={usage} />
            <NavGroup title="Administration" items={admin} subtle />
            <div className="min-h-4" />
          </div>
        </aside>
        <main className="w-full pb-24 lg:pb-0">
          <header className="sticky top-0 z-30 border-b border-white/10 bg-pitch/82 px-4 py-3 backdrop-blur-2xl lg:hidden">
            <Brand compact />
          </header>
          <div className="mx-auto max-w-[1500px] px-4 py-6 md:px-6 lg:px-9 lg:py-9">{children}</div>
        </main>
      </div>
      <MobileNav />
    </div>
  );
}

function HostStripes() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute left-0 top-0 h-1 w-full bg-gradient-to-r from-canada via-gold to-usa" />
      <div className="absolute -left-20 top-28 h-72 w-72 rounded-full bg-canada/15 blur-3xl" />
      <div className="absolute -right-16 top-20 h-80 w-80 rounded-full bg-usa/14 blur-3xl" />
      <div className="absolute bottom-0 left-1/3 h-80 w-80 rounded-full bg-mexico/10 blur-3xl" />
    </div>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/" className={clsx("flex items-center gap-3", compact ? "" : "mb-6")}>
      <motion.div
        whileHover={{ rotate: -4, scale: 1.04 }}
        className="relative grid h-12 w-12 place-items-center overflow-hidden rounded-[1.25rem] bg-gradient-to-br from-canada via-gold to-usa font-black text-pitch shadow-foil"
      >
        <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,.38),transparent_42%)]" />
        <span className="relative">26</span>
      </motion.div>
      <div>
        <div className="text-lg font-black leading-tight">Panini Tracker</div>
        <div className="text-xs font-bold uppercase tracking-[.18em] text-muted">World Cup 2026</div>
      </div>
    </Link>
  );
}

function QuickAction() {
  return (
    <Link href="/saisie" className="mb-7 block rounded-sticker border border-gold/25 bg-gold/10 p-4 shadow-glow transition hover:border-gold/60 hover:bg-gold/15">
      <div className="flex items-center gap-2 text-sm font-black text-gold">
        <Sparkles className="h-4 w-4" />
        Action rapide
      </div>
      <div className="mt-2 text-xl font-black text-white">Ajouter une pochette</div>
      <div className="mt-1 text-sm font-semibold text-muted">Colle les codes, preview, applique.</div>
    </Link>
  );
}

function NavGroup({ title, items, subtle = false }: { title: string; items: typeof usage; subtle?: boolean }) {
  return (
    <div className="mb-7">
      <div className="mb-2 px-3 text-xs font-black uppercase tracking-[.2em] text-slate-500">{title}</div>
      <div className="space-y-1.5">
        {items.map((item) => (
          <NavLink key={item.href} item={item} subtle={subtle} />
        ))}
      </div>
    </div>
  );
}

function NavLink({ item, subtle = false }: { item: (typeof usage)[number]; subtle?: boolean }) {
  const pathname = usePathname();
  const active = pathname === item.href;
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      className={clsx(
        "group relative flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-black transition",
        active ? "bg-white/10 text-white ring-1 ring-gold/35" : subtle ? "text-slate-500 hover:bg-white/6 hover:text-slate-200" : "text-slate-300 hover:bg-white/7 hover:text-white",
      )}
    >
      {active && <motion.div layoutId="active-nav" className="absolute inset-y-2 left-0 w-1 rounded-full bg-gold" />}
      <Icon className={clsx("h-4 w-4", active ? "text-gold" : "text-muted group-hover:text-gold")} />
      {item.label}
    </Link>
  );
}

function MobileNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed inset-x-3 bottom-3 z-40 rounded-[1.65rem] border border-white/12 bg-pitch/88 p-2 shadow-foil backdrop-blur-2xl lg:hidden">
      <div className="grid grid-cols-5 gap-1">
        {usage.slice(0, 5).map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex flex-col items-center gap-1 rounded-2xl px-2 py-2 text-[11px] font-black transition",
                active ? "bg-gold text-pitch" : "text-muted hover:bg-white/7 hover:text-white",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.short}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
